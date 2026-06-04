Assignment
Build a DAG-based agent for a problem of your choice and prove the architecture is intact.

Pass the five base queries (hello, A, I, J, K) from this session. Verbatim, within the iteration and wall-clock bounds named alongside each.

Design one query that requires parallel fan-out. The query must have at least three independent sub-tasks that the Planner correctly emits as concurrent nodes. Verify that the parallel layer's wall-clock is the maximum of the branches, not the sum.

Design one query that requires a Critic verdict. Choose a property the Critic can actually verify with the tools available to it. The Critic must produce both a pass and a fail across two runs of the query, and the fail must successfully splice in a Planner recovery that produces a corrected answer.

Fill in the Coder skill. The current prompts/coder.md is a stub; replace it with a prompt that emits Python suitable for the SandboxExecutor. Demonstrate the Coder on one query where the answer requires computation the Formatter cannot reliably produce from text alone.

Add one new skill to agent_config.yaml. Choose a skill that the existing catalogue does not cover. Write its prompt file. Write one query that exercises it. The orchestrator should not need modification; if it does, the modification is reportable.

Submit YouTube Demo clearly showing 1, 2, 3, 4, and 5 parts of the assignment.

Submit README.md link clearly showing results for 1, 2, 3, 4 and 5 parts of the assignment via logs.

Architectural rules carry over. Skills are yaml entries plus prompts. The Planner emits the graph; the Executor runs it; the Critic sits between a flagged producer and its successor. The recovery classifier must continue to pass its unit tests after any change. Adding a new skill is a yaml edit and a prompt file; touching the Executor for anything but a new generic mechanism is a bug.

Query hello. The minimum DAG

Say hello.
Two nodes. The Planner emits a Formatter as the only successor. The Formatter answers. Wall-clock under three seconds. The Planner's prompt allows this shape because the query needs neither research nor structure; the Formatter is the appropriate terminal. Students who run this first see the smallest possible DAG that the architecture can produce.

Query A. Shannon Wikipedia (S7 carryover)

Fetch https://en.wikipedia.org/wiki/Claude_Shannon and tell me his birth
date, death date, and three key contributions to information theory.
Four nodes. Planner emits researcher then distiller then formatter. The Researcher's tool-use loop runs fetch_url once and produces the page content. The Distiller extracts the three structured fields; a Critic auto-inserted between the Distiller and the Formatter returns pass on this content (the dates and contributions are clearly present in the page). The Formatter produces the final answer.

The trace under Session 8 is structurally the same as under Session 7. The wall-clock improvement is marginal because the query is sequential in its dependency structure. The architectural benefit is the trace itself: four named nodes, each with one job, instead of eight iterations of a single loop maintaining its goal list across turns.

Query I. Three city populations (the parallel-fan-out case)

The full discussion of this query lives in the populations section above. Seven nodes. Planner emits three Researchers concurrently, then a Coder, then a Formatter alongside a SandboxExecutor. Wall-clock sixty-two seconds against one hundred twenty-five for Session 7. Token bill seventeen thousand input against fifty-four thousand for Session 7.

Query J. Graceful failure

Read /nonexistent/path.txt and tell me what's in it.
Two nodes. The Planner reads the query, recognises that no part of the agent can plausibly satisfy a request for a file that does not exist, and emits a Formatter directly with a failure note in its inputs. The Formatter produces an answer that explains the path could not be accessed. No tool is dispatched.

The query exercises a path the orchestrator must handle gracefully: the Planner's first pass produces a degenerate DAG (planner to formatter, no work in between) because the query is unanswerable. The brief on this query allowed two outcomes: the agent fails-fast by planning, or the agent attempts the file read and fails-loud at Action. The Planner chose the first. Both are defensible; the first is faster and saves the Action call.

Query K. Resumable execution

For Lagos, Cairo, and Kinshasa, find current populations and growth rates
and tell me which is growing fastest.
The first process runs the query and is killed by SIGKILL at iteration four of the parallel Researcher layer. The graph file on disk contains the Planner as complete, two Researchers as complete, and one Researcher as running. The Executor was mid-gather at the moment of kill.

flow.py --resume s8_K_resumed_v2
The resume reads the graph from disk. The running Researcher is reset to pending. The Executor re-runs the pending Researcher, which re-executes its tool-use loop from the top. The Coder, Formatter, and SandboxExecutor then run. Wall-clock across the two processes is roughly seventy seconds against an estimated ninety seconds for a fresh single-process run; the resume's overhead is the re-execution of the killed Researcher's tool calls. The final answer correctly names Lagos as the fastest-growing city at approximately three point seventy-eight percent.