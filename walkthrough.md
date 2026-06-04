# Walkthrough: Critic, Coder, and Recovery Fixes

We have successfully resolved critical execution bugs in the critic auto-insertion logic, sandbox python compilation/escaping, recovery capping, critic subtask evaluation, and LLM gateway failover ordering. We have verified all requirements of the assignment using the API runner.

## Changes Made

### 1. Critic Context & Subtask Resolution
- **Problem**: The Critic node was previously evaluated against the global `USER_QUERY` alone, without any context of the specific subtask the target node (e.g., `distiller`) was performing. This caused the Critic to fail the distiller node for not providing acronyms (which were delegated to `acronym_expander` in the decomposed DAG). Furthermore, the Critic had no access to the inputs that produced the target's output, leading to hallucinations (e.g. demanding "Transformer" as an acronym).
- **Fix**: Modified [code/skills.py](file:///d:/AI%20Learning/GIT%20Repos/Assignment8/code/skills.py#L264-L278) to:
  - Extract the target node's specific subtask (`question`) and append it as `TARGET_NODE_SUBTASK` to the Critic's prompt.
  - Resolve the target node's own inputs and inject them into the Critic's resolved inputs as `upstream_inputs`.
- **Verification**: Verified that the Critic now successfully evaluates subtask nodes without hallucinating missing fields or failing due to global query mismatch.

### 2. Critic Auto-Insertion
- **Fix**: Modified [code/flow.py](file:///d:/AI%20Learning/GIT%20Repos/Assignment8/code/flow.py#L160-L175) to insert a single `critic` node dynamically between the completing node (e.g., `distiller`) and all of its existing downstream successors in the graph, rather than checking the empty `added` list.
- **Verification**: Verified that Query A now builds the correct 5-node DAG: `planner` -> `researcher` -> `distiller` -> `critic` -> `formatter`.

### 3. Coder String Literal & Double Escaping
- **Fix**: Updated [code/prompts/coder.md](file:///d:/AI%20Learning/GIT%20Repos/Assignment8/code/prompts/coder.md#L10) to guide the Coder to use `chr(10)` instead of `\n` in string literals. This prevents JSON deserialization from writing unescaped newlines directly into the sandbox file, which causes python compilation/syntax errors.
- **Verification**: Verified that the Coder query executes successfully and computes the statistical table:
  ```
  | Term      | Frequency | Mean | Variance |
  |-----------|-----------|------|----------|
  | attention | 7         | 9    | 103      |
  | weight    | 0         | 9    | 103      |
  | model     | 20        | 9    | 103      |
  ```

### 4. Recursive target tracing for recovery cap
- **Fix**: Updated [code/recovery.py](file:///d:/AI%20Learning/GIT%20Repos/Assignment8/code/recovery.py#L120-L135) to recursively trace back target node IDs to the root recovered target ID. This ensures the single-recovery cap is respected when new nodes are generated on successive re-plans, avoiding infinite recovery loops.
- **Verification**: Verified that the acronym expander query executes to completion and terminates gracefully under the new cap logic when the critic fails.

### 5. Subprocess stdout buffering
- **Fix**: Appended `-u` to the subprocess execution command in [demo/server.py](file:///d:/AI%20Learning/GIT%20Repos/Assignment8/demo/server.py#L170) to run Python in unbuffered mode. This guarantees that SSE events are flushed and received in real-time, even if the runner is terminated mid-execution.

### 6. LLM Gateway Failover Order
- **Fix**: Modified `DEFAULT_ORDER` in [gateway/main.py](file:///d:/AI%20Learning/GIT%20Repos/Assignment8/gateway/main.py#L27) to prioritize groq, cerebras, and openrouter over ollama, gemini, and nvidia.
- **Verification**: Verified that the gateway restarted with the new order active: `openai` → `groq` → `cerebras` → `openrouter` → `ollama` → `gemini` → `nvidia` → `github`.

---

## Verification Results

We executed all assignment queries via the API endpoints:

1. **Query hello**: Successfully completed in 2 nodes (`planner` -> `formatter`) in 8s.
2. **Query A**: Successfully completed in 5 nodes (`planner` -> `researcher` -> `distiller` -> `critic` -> `formatter`) in 37.9s.
3. **Query I**: Successfully executed concurrently across 3 `researcher` nodes, `coder`, `sandbox_executor`, and `formatter` in 159s.
4. **Query J**: Fails fast at the planning stage, emitting a 2-node DAG directly (`planner` -> `formatter`) with no tool dispatch.
5. **Query K (Kill & Resume)**: Initiated population query, interrupted mid-run via `/api/kill`, and successfully resumed via `/api/run` with `resume_sid` to execute the remaining nodes.
6. **Query 5 (Acronym Expander)**: Successfully executed the decomposed pipeline (`planner` -> `researcher` -> `summariser` & `acronym_expander` -> `formatter`), outputting the summary and the correct acronym glossary (BLEU, WMT, RNN, GPU) in 53.6s.
7. **Unit Tests**: Ran the integrated test runner via `/api/test`, yielding a 100% success rate (22/22 passed).
