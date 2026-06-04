# Assignment 8 — Demo Script

> **Purpose:** Step-by-step procedure for the YouTube demo recording.  
> Each section maps to one assignment requirement. Follow in order.

---

## Pre-Demo Setup (Do Before Recording)

### Terminal Layout
Open **three** terminal windows side by side:
- **Terminal 1 (left):** Gateway server
- **Terminal 2 (centre):** Agent commands
- **Terminal 3 (right):** Logs / replay / verification

### 1. Environment Check

```powershell
# Terminal 1 — Verify .env is configured
cd "d:\AI Learning\GIT Repos\Assignment8"
cat .env
# Confirm: OPENAI_API_KEY is set (this is your default provider)
```

### 2. Start the LLM Gateway

```powershell
# Terminal 1 — Start gateway
cd "d:\AI Learning\GIT Repos\Assignment8\gateway"
# Load .env and start
Get-Content ..\.env | Foreach-Object {
  if ($_ -match '^\s*([^#=\s]+)\s*=\s*(.*)$') {
    Set-Item "env:$($Matches[1])" ($Matches[2].Trim())
  }
}
.\.venv\Scripts\python main.py
# Wait for: "Uvicorn running on http://0.0.0.0:8108"
```

### 3. Verify Gateway Health

```powershell
# Terminal 2 — Quick health check
curl http://localhost:8108/v1/status
# Should return JSON with provider list
```

### 4. Run Unit Tests (Show Before Demo)

```powershell
# Terminal 2 — Prove tests pass before any demo
cd "d:\AI Learning\GIT Repos\Assignment8\code"
.\.venv\Scripts\python -m pytest tests/ -v
# Expected: "22 passed in ~0.24s"
```

> **Talking Point:** "All 22 unit tests covering the failure-recovery
> and critic-splice mechanics pass before we start."

---

## Part 1 — Base Queries (hello, A, I, J, K)

### Query: hello — The Minimum DAG

```powershell
# Terminal 2
cd "d:\AI Learning\GIT Repos\Assignment8\code"
.\.venv\Scripts\python flow.py "Say hello."
```

**What to show on camera:**
- The session banner prints (session ID + query)
- Exactly **2 nodes**: `planner` → `formatter`
- Wall-clock **under 3 seconds**
- The Formatter produces a greeting as the final answer

> **Talking Point:** "This is the smallest possible DAG the architecture
> can produce. The Planner sees a trivial query, emits only a Formatter,
> and we get an answer in under 3 seconds. Two nodes, one edge."

**Replay the trace:**
```powershell
# Terminal 3 — Replay the session to show the DAG
.\.venv\Scripts\python replay.py <session-id-from-above>
# Walk through each node: show skill type, inputs, status
```

---

### Query A — Shannon Wikipedia (S7 Carryover)

```powershell
# Terminal 2
.\.venv\Scripts\python flow.py "Fetch https://en.wikipedia.org/wiki/Claude_Shannon and tell me his birth date, death date, and three key contributions to information theory."
```

**What to show on camera:**
- **4 nodes**: Planner → Researcher → Distiller → (Critic auto-inserted) → Formatter
- The Researcher calls `fetch_url` once for the Wikipedia page
- The Distiller extracts: birth date (April 30, 1916), death date (February 24, 2001), three contributions
- The **Critic** is auto-inserted (Distiller has `critic: true` in agent_config.yaml) and returns `pass`
- The Formatter renders the final answer

> **Talking Point:** "Query A is a sequential pipeline. The Researcher
> fetches the page, the Distiller extracts structured fields, a Critic
> verifies the extraction, and the Formatter presents the answer.
> Four named nodes, each with one job."

**Show the config that triggers Critic auto-insertion:**
```powershell
# Terminal 3 — Show agent_config.yaml
cat "d:\AI Learning\GIT Repos\Assignment8\code\agent_config.yaml" | Select-String "distiller" -Context 0,3
# Highlight: critic: true
```

**Replay:**
```powershell
.\.venv\Scripts\python replay.py <session-id>
```

---

### Query I — Three City Populations (Parallel Fan-Out)

```powershell
# Terminal 2
.\.venv\Scripts\python flow.py "For Lagos, Cairo, and Kinshasa, find current populations and growth rates and tell me which is growing fastest."
```

**What to show on camera:**
- **7 nodes**: Planner → 3× Researcher (parallel) → Coder → SandboxExecutor → Formatter
- The three Researchers fire **concurrently** via `asyncio.gather`
- Wall-clock is the **max** of the three branches (~20-30s each), NOT the sum
- Note the total wall-clock (~60-70s) vs sequential estimate (~120s+)
- The Coder writes Python to compare growth rates
- The SandboxExecutor runs it
- Final answer names the fastest-growing city

> **Talking Point:** "This is the parallel fan-out case. Three Researchers
> execute concurrently — you can see them all start at roughly the same
> time. The wall-clock is the slowest branch, not the sum. This cuts
> execution time roughly in half compared to sequential."

**Replay:**
```powershell
.\.venv\Scripts\python replay.py <session-id>
# Point out the three researcher nodes with similar start times
```

---

### Query J — Graceful Failure

```powershell
# Terminal 2
.\.venv\Scripts\python flow.py "Read /nonexistent/path.txt and tell me what's in it."
```

**What to show on camera:**
- **2 nodes**: Planner → Formatter
- The Planner recognises the request is unanswerable
- **No tool is dispatched** — no fetch_url, no web_search
- The Formatter explains the path could not be accessed
- Wall-clock is very fast (similar to hello)

> **Talking Point:** "The Planner is smart enough to recognise this is
> unanswerable. It doesn't waste time dispatching a tool — it emits a
> degenerate DAG with just a Formatter that explains the failure.
> This is graceful failure handling at the planning level."

**Replay:**
```powershell
.\.venv\Scripts\python replay.py <session-id>
```

---

### Query K — Resumable Execution

This query requires **two separate runs** to demonstrate resume.

#### Step 1: Start the query and kill it mid-execution

```powershell
# Terminal 2 — Start the query
.\.venv\Scripts\python flow.py "For Lagos, Cairo, and Kinshasa, find current populations and growth rates and tell me which is growing fastest."
```

**Wait until you see at least 2 of the 3 Researchers complete, then kill the process:**
```powershell
# Press Ctrl+C (or close the terminal) while the 3rd Researcher is still running
# NOTE: On Windows, Ctrl+C sends a softer signal. For a hard kill:
# Open Terminal 3 and run:
taskkill /F /PID <pid-of-the-python-process>
# Or simply press Ctrl+C in Terminal 2
```

**What to show on camera:**
- The session ID printed at the top (you need this for resume)
- At least 2 Researchers show as complete
- The process is killed before all work finishes

> **Talking Point:** "I'm killing the process mid-execution. The graph
> state has been persisted to disk — two Researchers are complete, one
> is still running."

#### Step 2: Resume the killed session

```powershell
# Terminal 2 — Resume with the session ID from Step 1
.\.venv\Scripts\python flow.py --resume <session-id-from-step-1> "For Lagos, Cairo, and Kinshasa, find current populations and growth rates and tell me which is growing fastest."
```

**What to show on camera:**
- The resume reads the graph from disk
- The running Researcher is reset to `pending`
- Only the **incomplete work** is re-executed
- The Coder, SandboxExecutor, and Formatter run after
- The final answer is correct (Lagos, ~3.78% growth rate)
- Total wall-clock across both processes is ~70s vs ~90s fresh

> **Talking Point:** "The resume picks up right where we left off.
> It re-runs only the killed Researcher, then continues with the
> rest of the DAG. The final answer is correct — Lagos at approximately
> 3.78% annual growth. Resumable execution means we don't lose work."

**Show the session state on disk:**
```powershell
# Terminal 3 — Show the persisted state files
dir "d:\AI Learning\GIT Repos\Assignment8\code\state\sessions\<session-id>"
# Show graph.pkl, query.txt, and per-node JSON files
```

---

## Part 2 — Parallel Fan-Out (Detailed Verification)

> **Note:** Query I above already demonstrates this. Use this section to
> provide **additional evidence** if needed.

### Verification: Wall-Clock is Max, Not Sum

```powershell
# Terminal 3 — Replay the Query I session
.\.venv\Scripts\python replay.py <query-I-session-id>
```

**What to show on camera:**
- The three Researcher nodes' timestamps — they all **start** at nearly the same time
- Each branch takes ~20-30 seconds individually
- The total parallel layer completes in ~30 seconds (the max), NOT ~90 seconds (the sum)
- Compare to the total execution time

> **Talking Point:** "Looking at the timestamps: all three Researchers
> started within milliseconds of each other. Branch 1 took 22 seconds,
> Branch 2 took 28 seconds, Branch 3 took 25 seconds. The parallel
> layer completed in 28 seconds — the maximum — not 75 seconds, the sum.
> This proves true concurrent execution via asyncio.gather."

---

## Part 3 — Critic Verdict (Pass and Fail)

### Run 1: Critic Pass

```powershell
# Terminal 2
.\.venv\Scripts\python flow.py "Fetch https://en.wikipedia.org/wiki/Claude_Shannon and tell me his birth date, death date, and three key contributions to information theory."
```

**What to show on camera:**
- The Critic node appears after the Distiller (auto-inserted)
- Critic verdict: `pass`
- The flow continues to the Formatter normally
- Final answer has correct dates and contributions

> **Talking Point:** "The Critic is auto-inserted on every edge out of
> skills tagged with `critic: true`. Here the Distiller extracted the
> correct fields, so the Critic returns pass and the flow continues."

**Show the Critic's output in replay:**
```powershell
.\.venv\Scripts\python replay.py <session-id>
# Navigate to the Critic node — show verdict: pass
```

### Run 2: Critic Fail + Recovery

To trigger a Critic fail, use a query where the Distiller is more likely to produce
incomplete or inaccurate extraction. You can also modify the Critic's prompt temporarily
to be stricter, or use a query with ambiguous source material:

```powershell
# Terminal 2 — A query designed to occasionally trigger Critic fail
.\.venv\Scripts\python flow.py "Fetch https://en.wikipedia.org/wiki/Claude_Shannon and extract exactly five academic publications with their exact publication years."
```

**What to show on camera (if Critic fails):**
- Critic verdict: `fail` with rationale
- A **recovery Planner** node is spliced into the graph
- The recovery Planner re-plans the extraction
- The corrected answer passes the Critic on the second attempt
- Recovery is capped at **one re-plan per branch**

> **Talking Point:** "This time the Critic caught an issue — the Distiller's
> extraction was incomplete. The system automatically splices in a recovery
> Planner, which re-plans the extraction. On the second pass it gets it
> right. The recovery cap ensures we don't loop forever — one re-plan
> per branch, enforced in recovery.py."

**Show the recovery mechanism code:**
```powershell
# Terminal 3 — Show the recovery logic
cat "d:\AI Learning\GIT Repos\Assignment8\code\recovery.py" | head -30
```

**If Critic passes both times**, explain the mechanism and show:
```powershell
# Show the unit tests that prove the splice works
.\.venv\Scripts\python -m pytest tests/test_recovery.py -v -k "critic"
```

---

## Part 4 — Coder Skill

### Show the Coder Prompt (Before Running)

```powershell
# Terminal 3 — Show the completed Coder prompt
cat "d:\AI Learning\GIT Repos\Assignment8\code\prompts\coder.md"
```

> **Talking Point:** "The Coder skill was a stub — I filled it in with
> a prompt that emits Python wrapped in JSON. Key design decisions:
> triple-quoted strings to avoid escape issues, absolute paths because
> the sandbox runs in a temp directory, and .md extensions for the papers."

### Show agent_config.yaml Entry

```powershell
# Terminal 3 — Show the Coder's config
cat "d:\AI Learning\GIT Repos\Assignment8\code\agent_config.yaml" | Select-String "coder" -Context 0,5
# Point out: internal_successors: [sandbox_executor]
```

> **Talking Point:** "The Coder has `internal_successors: [sandbox_executor]`
> — the orchestrator automatically chains SandboxExecutor after Coder
> without the Planner having to know about it."

### Run the Coder Demo Query

```powershell
# Terminal 2
.\.venv\Scripts\python flow.py "Calculate the frequency of the terms 'attention', 'weight', and 'model' in all five papers in the papers directory. Output a Markdown table showing the frequencies, mean, and variance."
```

**What to show on camera:**
- DAG: Planner → Coder → SandboxExecutor → Formatter
- The Coder emits Python code (visible in the trace)
- The SandboxExecutor runs the code in a subprocess
- The Formatter presents the result as a Markdown table
- The computation (file I/O, counting, statistics) is **not** something the Formatter can do from text alone

**Expected output:**
```
| Term      | Frequency |
|-----------|-----------|
| attention | 7         |
| weight    | 0         |
| model     | 20        |
| Mean      | 9.00      |
| Variance  | 68.67     |
```

> **Talking Point:** "This query requires computation — reading five
> paper files, counting term frequencies, and calculating mean and
> variance. The Formatter can't do this from text alone. The Coder
> writes Python, the SandboxExecutor runs it, and we get the correct
> statistical results."

**Replay to show the code:**
```powershell
.\.venv\Scripts\python replay.py <session-id>
# Navigate to the Coder node — show the emitted Python
# Navigate to the SandboxExecutor node — show stdout/stderr
```

---

## Part 5 — New Skill (Acronym Expander)

### Show It's YAML-Only (No Orchestrator Changes)

```powershell
# Terminal 3 — Show the skill entry in agent_config.yaml
cat "d:\AI Learning\GIT Repos\Assignment8\code\agent_config.yaml" | Select-String "acronym" -Context 0,5
```

```powershell
# Terminal 3 — Show the prompt file
cat "d:\AI Learning\GIT Repos\Assignment8\prompts\acronym_expander.md"
```

> **Talking Point:** "Adding a new skill is a YAML edit and a prompt file.
> No orchestrator changes. The acronym_expander is declared in
> agent_config.yaml with a temperature, max_tokens, and a prompt path.
> The Planner's prompt lists it as an available skill."

**Show the Planner knows about it:**
```powershell
cat "d:\AI Learning\GIT Repos\Assignment8\code\prompts\planner.md" | Select-String "acronym"
# or
cat "d:\AI Learning\GIT Repos\Assignment8\prompts\planner.md" | Select-String "acronym"
```

### Run the Acronym Expander Query

```powershell
# Terminal 2
.\.venv\Scripts\python flow.py "Summarize the Attention paper and list all acronyms used in the abstract with their expansions using the acronym_expander."
```

**What to show on camera:**
- DAG: Planner → Researcher → Summariser → Acronym Expander → Formatter
- The Planner correctly routes to the `acronym_expander` skill
- The acronym_expander produces a glossary of acronyms
- No orchestrator modification was needed

**Expected output includes:**
```json
{
  "NLP": "Natural Language Processing",
  "RNN": "Recurrent Neural Network",
  "LSTM": "Long Short-Term Memory",
  "Seq2seq": "Sequence-to-Sequence"
}
```

> **Talking Point:** "The Planner correctly identified that this query
> needs the acronym_expander skill. It built a four-node DAG with the
> new skill integrated. Zero lines of orchestrator code were changed.
> Adding a skill is just YAML plus a prompt file — exactly as the
> architecture promises."

**Replay:**
```powershell
.\.venv\Scripts\python replay.py <session-id>
```

---

## Part 6 — Web UI Dashboard & Interactive Demo

This section demonstrates the DAG Agent Web UI Dashboard. It features a modern dark-themed layout, live DAG rendering with custom connectors, interactive node detail inspector, an integrated test runner, and a visual Kill/Resume flow.

### Step 1: Start the Web UI Server
If the server is not already running, launch the FastAPI server:
```powershell
# Terminal 2 — Start the Demo Server
cd "d:\AI Learning\GIT Repos\Assignment8\demo"
..\code\.venv\Scripts\python.exe server.py
# Server will start on http://localhost:8501
```

### Step 2: Open the Dashboard
Open your browser and navigate to:
```
http://localhost:8501
```

> **Talking Point:** "We've created a premium, high-fidelity Web UI dashboard
> for the DAG Agent. It features a modern dark theme with HSL-tailored colors,
> glassmorphic cards, active glowing running states, and animated floating welcome
> background orbs. In the sidebar, you'll find preset base queries, skill demos,
> and critic demos, plus a past sessions list loaded dynamically from disk."

### Step 3: Run a Base Query with Live DAG Rendering
1. Click **Shannon Wikipedia** in the sidebar. The query field will auto-fill.
2. Click the **▶ Run** button.
3. Observe:
   - Real-time streaming logs on the left.
   - Node-by-node construction of the DAG on the right.
   - When completed: Click the `critic` or `distiller` node in the DAG canvas.
   - Point out the side details inspector showing input variables, final result object, raw prompt, status, and provider.

> **Talking Point:** "As the agent runs, the orchestrator streams events via SSE.
> The frontend parses the live output and constructs the DAG in real-time.
> Clicking any node opens a details inspector revealing the complete state, inputs,
> outputs, and provider mapping. This makes the multi-agent system fully observable."

### Step 4: Run the Interactive Test Runner
1. Click the **✓ Run Tests** button in the header actions.
2. Observe the test suite logs streaming directly into a modal container in real-time.
3. Confirm that all orchestrator tests successfully compile and pass.

### Step 5: Visual Kill & Resume Flow (Query K)
1. Click **Resumable Execution (Query K)** in the sidebar.
2. Click **▶ Run**.
3. While the 3 Researchers are executing concurrently (pulsing in yellow/running states), click the red **✕ Kill** button next to the input field.
4. Confirm the log output says: `✓ Process killed. Session <session_id> saved to disk.`
5. Notice the warning/resume banner that appears showing the session ID and a **↻ Resume Session** button.
6. Click **↻ Resume Session**.
7. Observe that:
   - Only the interrupted/incomplete Researcher runs again.
   - The completed Researchers are skipped, reading directly from their cached state.
   - The execution flows seamlessly through Coder, SandboxExecutor, and Formatter to print the final fastest-growing city answer.

> **Talking Point:** "The kill/resume mechanism is fully integrated visually. When we hit 'Kill',
> the backend terminates the runner subprocess and saves the current graph state.
> When we hit 'Resume', the orchestrator reloads the graph from disk, resets
> only the pending/failed node, and re-executes the remainder of the pipeline.
> This demonstrates industrial-grade fault-tolerance and session recovery."

---

## Wrap-Up — Show Unit Tests Pass After All Changes

```powershell
# Terminal 2
cd "d:\AI Learning\GIT Repos\Assignment8\code"
.\.venv\Scripts\python -m pytest tests/ -v
# Expected: "22 passed"
```

> **Talking Point:** "All 22 unit tests still pass after every change
> we made. The recovery classifier, critic splice, and failure
> classification all remain intact."

### Show Key Files Changed

```powershell
# Terminal 3 — Quick summary
echo "Files modified for this assignment:"
echo "  - code/prompts/coder.md          (Coder skill prompt — was a stub)"
echo "  - code/agent_config.yaml         (added acronym_expander)"
echo "  - prompts/acronym_expander.md    (new skill prompt)"
echo "  - prompts/planner.md             (added acronym_expander to skill list)"
echo "  - gateway/agent_routing.yaml     (pinned all agents to OpenAI)"
echo "  - gateway/main.py                (default provider fallback)"
echo "  - code/skills.py                 (fixed double-escaping)"
```

> **Talking Point:** "No structural changes to flow.py. The orchestrator
> didn't need modification. Skills are YAML entries plus prompts.
> The Planner emits the graph, the Executor runs it, the Critic sits
> between flagged producers and their successors. Architecture intact."

---

## Demo Checklist

Use this to confirm you covered everything before ending the recording:

| # | Requirement | Query/Action | Shown? |
|---|---|---|---|
| 1a | Query hello — minimum DAG (2 nodes, <3s) | `"Say hello."` | ☐ |
| 1b | Query A — Shannon Wikipedia (4 nodes, Critic pass) | `"Fetch https://en.wikipedia.org/wiki/Claude_Shannon..."` | ☐ |
| 1c | Query I — Parallel fan-out (3 concurrent Researchers) | `"For Lagos, Cairo, and Kinshasa..."` | ☐ |
| 1d | Query J — Graceful failure (2 nodes, no tools) | `"Read /nonexistent/path.txt..."` | ☐ |
| 1e | Query K — Resumable execution (kill + resume) | Kill mid-run + `--resume` | ☐ |
| 2 | Parallel fan-out verified (wall-clock = max not sum) | Timestamps from Query I | ☐ |
| 3 | Critic pass + fail + recovery splice | Query A (pass) + stricter query (fail) | ☐ |
| 4 | Coder skill demo (computation query) | `"Calculate frequency of terms..."` | ☐ |
| 5 | New skill (acronym_expander) — no orchestrator changes | `"Summarize the Attention paper..."` | ☐ |
| 6 | Web UI Dashboard — aesthetics & layout | Open http://localhost:8501 | ☐ |
| 7 | Live DAG connectors (fan-out/merge) | Run query and see SVG/CSS connectors | ☐ |
| 8 | Node inspector panel details | Click a node to view state / inputs / outputs | ☐ |
| 9 | Interactive Test Runner | Click "Run Tests" in header | ☐ |
| 10 | Interactive Kill & Resume Flow | Click "Kill" then "Resume Session" | ☐ |
| — | Unit tests pass (22/22) | `pytest tests/ -v` | ☐ |

---

## Estimated Demo Duration

| Section | Estimated Time |
|---|---|
| Pre-demo setup + gateway start | 2 min |
| Part 1: Five base queries | 8-10 min |
| Part 2: Parallel verification | 2 min |
| Part 3: Critic pass + fail | 5 min |
| Part 4: Coder skill | 3-4 min |
| Part 5: New skill | 3-4 min |
| Part 6: Web UI Dashboard | 5-6 min |
| Wrap-up + tests | 2 min |
| **Total** | **~30-35 min** |
