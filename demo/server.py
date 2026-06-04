"""Demo UI backend — wraps flow.py's Executor and exposes it over HTTP + SSE.

Runs on :8501. The gateway must already be running on :8108.
Streams node-by-node progress to the frontend via Server-Sent Events.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

# Add the code/ directory to sys.path so we can import the orchestrator
CODE_DIR = Path(__file__).resolve().parent.parent / "code"
sys.path.insert(0, str(CODE_DIR))
os.chdir(CODE_DIR)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Orchestrator imports
# pyrefly: ignore [missing-import]
from persistence import SessionStore, list_sessions
from schemas import AgentResult, NodeState


# ── Helpers ──────────────────────────────────────────────────────────────────

def _load_env():
    """Load .env from project root."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())


def _session_summary(sid: str) -> dict:
    """Build a summary dict for one session."""
    store = SessionStore(sid)
    query = store.read_query() or "(no query)"
    nodes = store.read_all_nodes()

    node_list = []
    total_elapsed = 0.0
    for ns in nodes:
        r = ns.result
        node_info = {
            "id": ns.node_id,
            "skill": ns.skill,
            "status": ns.status,
            "elapsed_s": round(r.elapsed_s, 1) if r else 0,
            "provider": r.provider if r else "",
            "error": (r.error[:200] if r and r.error else None),
            "output_preview": "",
        }
        if r and r.output:
            try:
                preview = json.dumps(r.output, ensure_ascii=False)
                node_info["output_preview"] = preview[:500]
            except (TypeError, ValueError):
                node_info["output_preview"] = str(r.output)[:500]
        if r and r.elapsed_s:
            total_elapsed += r.elapsed_s
        node_list.append(node_info)

    # Detect DAG edges from the graph.json
    edges = []
    graph = store.read_graph()
    if graph:
        for u, v in graph.edges():
            edges.append({"from": u, "to": v})

    # Final answer
    final_answer = ""
    for ns in reversed(nodes):
        if ns.skill == "formatter" and ns.result and ns.result.output:
            fa = ns.result.output.get("final_answer", "")
            if isinstance(fa, str) and fa.strip():
                final_answer = fa
                break
    if not final_answer:
        for ns in reversed(nodes):
            if ns.result and ns.result.output:
                final_answer = json.dumps(ns.result.output)[:1000]
                break

    return {
        "session_id": sid,
        "query": query,
        "node_count": len(nodes),
        "total_elapsed_s": round(total_elapsed, 1),
        "nodes": node_list,
        "edges": edges,
        "final_answer": final_answer,
    }


# ── App ──────────────────────────────────────────────────────────────────────

_load_env()

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(title="Assignment 8 Demo UI", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DEMO_DIR = Path(__file__).resolve().parent

# ── Process tracking for kill / resume ───────────────────────────────────────
_process_state = {"process": None, "session_id": None}


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    return (DEMO_DIR / "index.html").read_text(encoding="utf-8")

@app.get("/style.css")
async def css():
    return HTMLResponse(
        (DEMO_DIR / "style.css").read_text(encoding="utf-8"),
        media_type="text/css"
    )

@app.get("/api/sessions")
async def get_sessions():
    sessions = list_sessions()
    return {"sessions": sessions}

@app.get("/api/session/{sid}")
async def get_session(sid: str):
    try:
        return _session_summary(sid)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=404)

@app.get("/api/session/{sid}/node/{node_id}")
async def get_node(sid: str, node_id: str):
    store = SessionStore(sid)
    ns = store.read_node(node_id)
    if not ns:
        return JSONResponse({"error": "node not found"}, status_code=404)
    data = ns.model_dump(mode="json")
    return data


@app.post("/api/run")
async def run_query(request: Request):
    """Run a query through flow.py as a subprocess and stream output via SSE."""
    body = await request.json()
    query = body.get("query", "")
    resume_sid = body.get("resume_sid")

    if not query and not resume_sid:
        return JSONResponse({"error": "query is required"}, status_code=400)

    async def event_stream():
        cmd = [sys.executable, "-u", str(CODE_DIR / "flow.py")]
        if resume_sid:
            cmd += ["--resume", resume_sid]
        if query:
            cmd.append(query)

        yield f"data: {json.dumps({'type': 'start', 'query': query, 'resume': resume_sid})}\n\n"

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(CODE_DIR),
        )
        _process_state["process"] = process

        session_id = None
        buffer = ""
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="replace").rstrip()

            # Detect session ID from first banner line
            if "session " in text and " ─ " in text and not session_id:
                parts = text.split("session ", 1)
                if len(parts) > 1:
                    session_id = parts[1].split()[0].strip()
                    _process_state["session_id"] = session_id
                    yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"

            # Detect node execution lines [n:X]
            if text.startswith("[n:"):
                yield f"data: {json.dumps({'type': 'node', 'text': text})}\n\n"
            elif text.startswith("FINAL:"):
                final = text[6:].strip()
                yield f"data: {json.dumps({'type': 'final', 'answer': final})}\n\n"
            elif "═" in text:
                # Banner lines
                if "FINAL:" in text:
                    pass  # handled above
                else:
                    yield f"data: {json.dumps({'type': 'banner', 'text': text})}\n\n"
            elif text.startswith("  ↪"):
                yield f"data: {json.dumps({'type': 'recovery', 'text': text})}\n\n"
            elif text.startswith("[memory"):
                yield f"data: {json.dumps({'type': 'memory', 'text': text})}\n\n"
            elif text.startswith("[flow]"):
                yield f"data: {json.dumps({'type': 'flow', 'text': text})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'log', 'text': text})}\n\n"

        await process.wait()
        _process_state["process"] = None

        # Report if process was killed
        if process.returncode and process.returncode < 0:
            yield f"data: {json.dumps({'type': 'killed', 'session_id': _process_state.get('session_id'), 'signal': abs(process.returncode)})}\n\n"

        # After completion, load the full session data
        if session_id:
            try:
                summary = _session_summary(session_id)
                yield f"data: {json.dumps({'type': 'complete', 'session': summary})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'text': str(e)})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")



@app.post("/api/kill")
async def kill_running():
    """Kill the currently running flow.py process for resume demo."""
    proc = _process_state.get("process")
    if proc and proc.returncode is None:
        proc.kill()
        sid = _process_state.get("session_id")
        return {"killed": True, "session_id": sid}
    return {"killed": False, "session_id": None}


@app.post("/api/test")
async def run_tests():
    """Run pytest and stream output."""
    async def event_stream():
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "pytest", str(CODE_DIR.parent / "tests" / "test_recovery.py"), "-v",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(CODE_DIR),
        )
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="replace").rstrip()
            yield f"data: {json.dumps({'type': 'test', 'text': text})}\n\n"
        await process.wait()
        yield f"data: {json.dumps({'type': 'test_done', 'exit_code': process.returncode})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8501)
