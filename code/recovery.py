"""Failure classification and recovery decisions for the orchestrator.

Two surfaces:

  - `classify_failure(error_text)` buckets a failure into one of
    {transient, validation_error, upstream_failure} so the orchestrator
    can tell apart a gateway 503 from a malformed plan from a genuine
    upstream miss (NOTES_RUNS round-2 review P0 #3).

  - `plan_recovery(...)` is the predicate the Executor consults to
    decide WHAT to do with a failure: "skip", "replan", or "critic_fail".
    Concentrating the if/elif tree here keeps `flow.Executor.run`
    focused on graph mechanics and lets the recovery policy be unit-
    tested in isolation.

The orchestrator imports `plan_recovery` and acts on the returned
`RecoveryDecision` — it does not branch on classifier output itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RecoveryReason = Literal["transient", "validation_error", "upstream_failure"]
RecoveryAction = Literal["skip", "replan", "critic_fail"]


def classify_failure(error_text: str) -> RecoveryReason:
    e = (error_text or "").lower()
    if not e:
        return "upstream_failure"
    if "malformed" in e or "validationerror" in e or "validation error" in e:
        return "validation_error"
    transient_markers = (
        "503", "502", "504",
        "timeout", "timed out",
        "connection", "connectionerror", "httpstatuserror",
        "service unavailable", "bad gateway", "gateway timeout",
    )
    if any(m in e for m in transient_markers):
        return "transient"
    return "upstream_failure"


@dataclass(frozen=True)
class RecoveryDecision:
    action: RecoveryAction
    reason: RecoveryReason
    note: str
    failure_report: str | None = None  # populated when action == "replan"


def plan_recovery(
    *,
    failed_skill: str,
    error_text: str,
    failed_node_id: str,
) -> RecoveryDecision:
    """Decide what to do with a node failure that is NOT a critic-verdict
    failure. The critic-fail path is handled separately in the Executor
    because it needs access to the critic node's metadata (target, child)
    and a per-target cap that is run-scoped state — this function is the
    purely-local predicate.

    Decision table (all coverage):
      reason=transient                          → skip (gateway already retried)
      reason=validation_error                   → skip (prompt bug, not runtime)
      reason=upstream_failure, failed=planner   → skip (would loop on Planner errors)
      reason=upstream_failure, failed=other     → replan
    """
    reason = classify_failure(error_text)
    if reason == "transient":
        return RecoveryDecision(
            action="skip", reason=reason,
            note="transient gateway error; gateway retry exhausted, not re-planning",
        )
    if reason == "validation_error":
        return RecoveryDecision(
            action="skip", reason=reason,
            note="validation error (malformed NodeSpec); fix the prompt, not the run",
        )
    if failed_skill == "planner":
        return RecoveryDecision(
            action="skip", reason=reason,
            note="planner-itself failure; not re-planning a planner",
        )
    fr = (f"node={failed_node_id} skill={failed_skill} reason={reason} "
          f"error={error_text}")
    return RecoveryDecision(
        action="replan", reason=reason,
        note="upstream failure; queueing planner recovery",
        failure_report=fr,
    )


def handle_critic_verdict(nid: str, result, graph, recovered_branches: dict,
                          cap_hit: list) -> bool:
    """Critic-fail policy (P1 #5). Returns True when the caller should skip
    the normal `extend_from` (because the Critic emitted `fail` and we
    handled it by splicing a recovery Planner). False on `pass`.

    Two shapes of Critic appear in S8: auto-inserted Critics (Graph.extend_from
    inserts one whenever a `critic:true` skill has outgoing edges) which
    carry `target` + `child` in metadata, and Planner-emitted Critics
    which do not — for the latter we derive both from graph structure.
    """
    if (result.output or {}).get("verdict", "pass") != "fail":
        return False
    md = graph.g.nodes[nid].get("metadata") or {}
    target_nid = md.get("target")
    if not target_nid:
        for inp in graph.g.nodes[nid]["inputs"]:
            if inp.startswith("n:") and inp in graph.g.nodes:
                target_nid = inp; break
    successors = list(graph.g.successors(nid))
    for child in successors:
        graph.mark(child, "skipped")
    child_nid = successors[0] if successors else None
    if target_nid:
        # Resolve the root target node ID by tracing back recovers metadata
        root_nid = target_nid
        while True:
            ancestor = graph.g.nodes[root_nid].get("metadata", {}).get("recovers")
            if ancestor and ancestor in graph.g.nodes:
                root_nid = ancestor
            else:
                break
    else:
        root_nid = None

    if root_nid and not recovered_branches.get(root_nid):
        recovered_branches[root_nid] = True
        rationale = (result.output or {}).get("rationale", "(no rationale)")
        fr = f"critic failed target={target_nid} child={child_nid} rationale={rationale}"
        rec_nid = graph.add_node("planner", inputs=["USER_QUERY"],
                                 metadata={"failure_report": fr,
                                           "recovers": target_nid,
                                           "recovery_reason": "critic_fail"})
        print(f"  ↪ critic-fail recovery: planner node {rec_nid} for {target_nid}")
    elif root_nid:
        cap_hit.append(root_nid)
        print(f"  ↪ critic-fail on {root_nid} already recovered once; "
              f"CAP HIT — branch skipped, final will reflect missing data")
    return True
