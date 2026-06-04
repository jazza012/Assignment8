# Assignment 8 — DAG-Based Multi-Agent Orchestrator

**Course:** EAGV3 — Session 8  
**Student:** Jasmeet  
**Repository:** [Assignment8](https://github.com/jazza012/AI-Learning)

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Assignment Parts & Results](#assignment-parts--results)
  - [Part 1 — Base Queries (hello, A, I, J, K)](#part-1--base-queries-hello-a-i-j-k)
  - [Part 2 — Parallel Fan-Out Query](#part-2--parallel-fan-out-query)
  - [Part 3 — Critic Verdict Query](#part-3--critic-verdict-query)
  - [Part 4 — Coder Skill](#part-4--coder-skill)
  - [Part 5 — New Skill (Acronym Expander)](#part-5--new-skill-acronym-expander)
- [Testing](#testing)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

---

## Overview

This project implements a **DAG-based (Directed Acyclic Graph) multi-agent orchestrator** that decomposes user queries into typed skill nodes, executes them in topological order with parallel fan-out where possible, and routes all LLM calls through a local FastAPI gateway with provider failover.

The key architectural insight: **the graph itself is the agent loop**. Each node is a typed skill (Planner, Researcher, Distiller, Critic, Formatter, Coder, etc.), edges carry the predecessor's `AgentResult`, and the runtime executes ready nodes concurrently via `asyncio.gather`.

---

## Architecture

```
User Query
    │
    ▼
┌──────────┐
│  Planner │  Decomposes query into a DAG of skill nodes
└────┬─────┘
     │  emits NodeSpec[]
     ▼
┌──────────────────────────────────────────────────┐
│                   Executor                        │
│  Topological traversal with asyncio.gather        │
│  for concurrent siblings                          │
│                                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  │
│  │ Researcher │  │ Researcher │  │ Researcher │  │  ← parallel fan-out
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  │
│        └───────────┬───┘───────────────┘          │
│                    ▼                               │
│              ┌──────────┐                          │
│              │  Coder   │                          │
│              └────┬─────┘                          │
│                   │  internal_successors           │
│                   ▼                                │
│         ┌──────────────────┐                       │
│         │ SandboxExecutor  │                       │
│         └────────┬─────────┘                       │
│                  ▼                                 │
│            ┌───────────┐                           │
│            │ Formatter │  → Final Answer           │
│            └───────────┘                           │
└──────────────────────────────────────────────────┘

         ┌──────────┐
         │  Critic  │  Auto-inserted on edges from skills
         └──────────┘  tagged critic: true (e.g. Distiller)
               │
          fail → splice recovery Planner
          pass → continue to successor
```

### Core Components

| Component | File | Role |
|---|---|---|
| **Orchestrator** | `code/flow.py` | Builds and executes the DAG; handles resume |
| **Skills Registry** | `code/skills.py` | Loads skill definitions, renders prompts, calls the gateway |
| **Skill Catalogue** | `code/agent_config.yaml` | YAML-only skill declarations with prompt paths and metadata |
| **Recovery** | `code/recovery.py` | Failure classification + Critic-fail splice logic |
| **Sandbox** | `code/sandbox.py` | Subprocess Python runner for Coder output |
| **Persistence** | `code/persistence.py` | Session state writes (graph.json + per-node JSON) |
| **LLM Gateway** | `gateway/main.py` | FastAPI server on `:8108` with provider failover |
| **Provider Router** | `gateway/router.py` | Rate-state management and provider rotation |
| **Agent Routing** | `gateway/agent_routing.yaml` | Skill → provider pinning |

### Skill Catalogue

| Skill | Prompt | Description |
|---|---|---|
| `planner` | `prompts/planner.md` | Decomposes queries into DAG node specifications |
| `researcher` | `prompts/researcher.md` | Multi-step web research with `web_search` and `fetch_url` tools |
| `retriever` | `prompts/retriever.md` | Searches Memory and FAISS index for relevant material |
| `distiller` | `prompts/distiller.md` | Extracts structured fields from raw text (Critic-enabled) |
| `summariser` | `prompts/summariser.md` | Condenses long content into short form |
| `critic` | `prompts/critic.md` | Evaluates upstream output; emits pass/fail with rationale |
| `formatter` | `prompts/formatter.md` | Renders the final user-facing answer |
| `coder` | `prompts/coder.md` | Emits Python code for computational tasks |
| `sandbox_executor` | `prompts/sandbox_executor.md` | Runs Coder output in subprocess sandbox |
| `acronym_expander` | `prompts/acronym_expander.md` | Extracts and expands acronyms from text |

---

## Project Structure

```
Assignment8/
├── Assignment.md              ← Assignment specification
├── Assignment8ReadMe.md       ← This file
├── README.md                  ← Original scaffolding README
├── walkthrough.md             ← Implementation walkthrough
├── .env.example               ← Environment template
├── .env                       ← API keys (git-ignored)
├── .gitignore
│
├── code/                      ← Agent orchestrator
│   ├── flow.py                ← Main orchestrator: Graph + Executor + CLI
│   ├── skills.py              ← Skill registry, prompt rendering, run_skill
│   ├── recovery.py            ← Failure classification + critic-fail splice
│   ├── persistence.py         ← Session state persistence
│   ├── sandbox.py             ← Subprocess Python runner
│   ├── schemas.py             ← AgentResult, NodeSpec, NodeState, MemoryItem
│   ├── mcp_runner.py          ← Multi-turn tool-use loop wrapper
│   ├── mcp_server.py          ← MCP tools: web_search, fetch_url, etc.
│   ├── gateway.py             ← Gateway client import
│   ├── replay.py              ← Stdin-driven trace viewer
│   ├── agent_config.yaml      ← Skills catalogue
│   ├── prompts/               ← One .md prompt file per skill
│   │   ├── planner.md
│   │   ├── researcher.md
│   │   ├── retriever.md
│   │   ├── distiller.md
│   │   ├── summariser.md
│   │   ├── critic.md
│   │   ├── formatter.md
│   │   ├── coder.md
│   │   ├── sandbox_executor.md
│   │   └── acronym_expander.md
│   └── sandbox/papers/        ← Five arXiv abstracts for corpus queries
│       ├── attention.md
│       ├── cot.md
│       ├── dpo.md
│       ├── lora.md
│       └── react.md
│
├── gateway/                   ← LLM Gateway V8 (FastAPI on :8108)
│   ├── main.py                ← Gateway server
│   ├── client.py              ← SDK client
│   ├── providers.py           ← Provider implementations
│   ├── router.py              ← Rate-state and failover routing
│   ├── agent_routing.yaml     ← Agent → provider pinning
│   ├── embedders.py           ← Embedding providers
│   ├── cache.py               ← Response caching
│   ├── db.py                  ← SQLite persistence
│   └── schemas.py             ← Gateway data models
│
├── tests/                     ← Unit tests
│   └── test_recovery.py       ← 22 tests for failure recovery + critic splice
│
├── scratch/                   ← Temporary working files
└── state/                     ← Session state storage
```

---

## Setup & Installation

### Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** — Fast Python package manager
- **Ollama** — Local embeddings (`ollama pull nomic-embed-text`)
- At least one LLM provider API key (OpenAI recommended as default)

### Steps

```powershell
# 1. Clone the repository
git clone https://github.com/jazza012/AI-Learning.git
cd Assignment8

# 2. Configure environment
cp .env.example .env
# Edit .env and add your API keys (at minimum: OPENAI_API_KEY)

# 3. Install dependencies
cd gateway; uv sync; cd ..
cd code; uv sync; cd ..

# 4. Start the LLM Gateway (Terminal 1)
cd gateway
uv run main.py
# Boots on http://localhost:8108

# 5. Run the agent (Terminal 2)
cd code
uv run python flow.py "Say hello."
```

A successful first run prints two node lines (`planner`, `formatter`) and a greeting. Sessions are saved to `code/state/sessions/<session-id>/`.

### Replay a session

```powershell
cd code
uv run python replay.py <session-id>
```

---

## Assignment Parts & Results

### Part 1 — Base Queries (hello, A, I, J, K)

All five base queries from the assignment specification pass within their iteration and wall-clock bounds.

#### Query: hello — "Say hello."

- **Nodes:** 2 (Planner → Formatter)
- **Behaviour:** The Planner emits a Formatter as the only successor. The Formatter produces a greeting. Wall-clock under 3 seconds.
- **DAG shape:** Minimal — demonstrates the smallest possible DAG the architecture can produce.

#### Query A — Shannon Wikipedia

> *"Fetch https://en.wikipedia.org/wiki/Claude_Shannon and tell me his birth date, death date, and three key contributions to information theory."*

- **Nodes:** 4 (Planner → Researcher → Distiller → Critic → Formatter)
- **Behaviour:** The Researcher fetches the Wikipedia page via `fetch_url`. The Distiller extracts structured fields (dates + contributions). A Critic is auto-inserted between Distiller and Formatter (Distiller has `critic: true`), and returns `pass` on this content.
- **Result:** Birth date (April 30, 1916), death date (February 24, 2001), and three contributions correctly extracted.

#### Query I — Three City Populations (Parallel Fan-Out)

> *"For Lagos, Cairo, and Kinshasa, find current populations and growth rates and tell me which is growing fastest."*

- **Nodes:** 7 (Planner → 3× Researcher ∥ → Coder → SandboxExecutor → Formatter)
- **Behaviour:** Three Researcher nodes execute concurrently. Wall-clock is the *maximum* of the three branches, not the sum.
- **Wall-clock:** ~62 seconds vs 125 seconds sequential (Session 7)
- **Token bill:** ~17K input vs 54K for Session 7

#### Query J — Graceful Failure

> *"Read /nonexistent/path.txt and tell me what's in it."*

- **Nodes:** 2 (Planner → Formatter)
- **Behaviour:** The Planner recognises the request is unanswerable (nonexistent path) and emits a Formatter directly with a failure note. No tool is dispatched. The Formatter produces an answer explaining the path could not be accessed.

#### Query K — Resumable Execution

> *"For Lagos, Cairo, and Kinshasa, find current populations and growth rates and tell me which is growing fastest."*

- **Process 1:** Runs the query, is killed (SIGKILL) at iteration 4 of the parallel Researcher layer. Graph state on disk: Planner complete, 2 Researchers complete, 1 Researcher running.
- **Process 2:** `flow.py --resume s8_K_resumed_v2` reads the graph from disk, resets the running Researcher to pending, re-executes only the missing work.
- **Result:** Lagos correctly identified as fastest-growing (~3.78%). Wall-clock across both processes: ~70 seconds vs ~90 seconds for a fresh run.

---

### Part 2 — Parallel Fan-Out Query

**Query:** *"For Lagos, Cairo, and Kinshasa, find current populations and growth rates and tell me which is growing fastest."*

This is the same as Query I above. The key verification:

| Metric | Value |
|---|---|
| Independent sub-tasks | 3 (one Researcher per city) |
| Concurrent execution | ✅ All three fire via `asyncio.gather` |
| Wall-clock | max(branch₁, branch₂, branch₃) ≈ 62s |
| Sequential equivalent | branch₁ + branch₂ + branch₃ ≈ 125s |
| Speedup | ~2× |

The parallel layer's wall-clock is confirmed to be the maximum of the branches, not the sum.

---

### Part 3 — Critic Verdict Query

**Property verified:** The Critic checks whether the Distiller's structured extraction (dates, contributions) is factually present and complete from the source material.

- **Pass run:** Distiller correctly extracts Shannon's birth date, death date, and three contributions. Critic returns `verdict: pass`.
- **Fail run:** Distiller produces incomplete or hallucinated fields. Critic returns `verdict: fail`, which triggers the recovery splice: a recovery Planner is injected into the graph, which re-plans the extraction with corrected instructions. The corrected answer passes on the second attempt.

The recovery mechanism is capped at one re-plan per branch (enforced in `recovery.py`).

---

### Part 4 — Coder Skill

**Prompt file:** `code/prompts/coder.md`

The Coder skill emits Python code wrapped in a JSON structure that the `SandboxExecutor` can execute. Key design decisions in the prompt:

- **Triple-quoted strings** — avoids double-escaping issues with `\n` literals
- **Absolute paths** — the sandbox runs in a temporary OS directory, so all file references use absolute paths to the workspace (`d:/AI Learning/GIT Repos/Assignment8/sandbox/papers/`)
- **File extensions** — `.md` for papers in the sandbox corpus

**Demo query:**

> *"Calculate the frequency of the terms 'attention', 'weight', and 'model' in all five papers in the papers directory. Output a Markdown table showing the frequencies, mean, and variance."*

**DAG:** Planner → Coder → SandboxExecutor → Formatter

**Result:**

| Term | Frequency |
|---|---|
| attention | 7 |
| weight | 0 |
| model | 20 |
| **Mean** | 9.00 |
| **Variance** | 68.67 |

This query requires computation (file I/O, counting, statistics) that the Formatter cannot reliably produce from text alone — it must be executed as code.

---

### Part 5 — New Skill (Acronym Expander)

**Skill:** `acronym_expander`  
**Prompt file:** `prompts/acronym_expander.md`  
**Config entry:** Added to `code/agent_config.yaml` — YAML edit only, no orchestrator modification required.

**Demo query:**

> *"Summarize the Attention paper and list all acronyms used in the abstract with their expansions using the acronym_expander."*

**DAG:** Planner → Researcher → Summariser → Acronym Expander → Formatter

**Result:**

```json
{
  "glossary": {
    "NLP": "Natural Language Processing",
    "RNN": "Recurrent Neural Network",
    "LSTM": "Long Short-Term Memory",
    "Seq2seq": "Sequence-to-Sequence"
  }
}
```

The orchestrator required **zero modification** — adding the skill was a YAML edit (`agent_config.yaml`) plus a prompt file (`prompts/acronym_expander.md`), plus adding the skill name to the Planner's prompt so it knows the skill exists.

---

## Testing

All 22 unit tests pass covering the failure-recovery and critic-splice mechanics:

```powershell
cd code
uv run pytest tests/ -v
```

```
============================= 22 passed in 0.24s ==============================
```

Tests cover:
- Failure classification (transient vs. validation vs. upstream)
- Critic pass/fail verdict handling
- Recovery Planner splice mechanics
- Re-plan cap enforcement (max one re-plan per branch)

---

## Configuration

### LLM Provider Routing

All agents are pinned to **OpenAI** as the default provider via `gateway/agent_routing.yaml`:

```yaml
planner: openai
researcher: openai
distiller: openai
summariser: openai
critic: openai
formatter: openai
retriever: openai
sandbox_executor: openai
coder: openai
browser: openai

default: openai
```

The `default: openai` entry in the gateway's `main.py` provides a fallback for any skill not explicitly listed.

### Environment Variables

Copy `.env.example` to `.env` and fill in at minimum one provider key. See `.env.example` for all supported providers (Gemini, Groq, Cerebras, NVIDIA, GitHub Models, OpenRouter).

---

## Troubleshooting

| Symptom | First Place to Look |
|---|---|
| `[gateway] failed to start within 45s` | Run `cd gateway && uv run main.py` separately and read stderr. Usually a missing API key or port `:8108` already in use. |
| `503 Service Unavailable` | All providers in cooldown or unconfigured. Add another key to `.env` or wait a minute. |
| `no code in upstream coder output` | The Coder prompt isn't emitting the JSON shape the orchestrator expects. Check `prompts/coder.md`. |
| Final answer is short or wrong | Run `replay.py <sid>` and inspect `prompt_sent` for each node to see what the gateway actually received. |
| Sandbox `FileNotFoundError` | Ensure the Coder is using absolute paths. The sandbox runs in a temp directory, not the workspace root. |

---

## Video Demo

📹 YouTube demonstration covering all five parts is available at: *(link to be added)*

---

## References

- [Assignment Specification](Assignment.md)
- [Implementation Walkthrough](walkthrough.md)
- [Original Scaffolding README](README.md)
- [Agent Config](code/agent_config.yaml)
- [Gateway Agent Routing](gateway/agent_routing.yaml)
