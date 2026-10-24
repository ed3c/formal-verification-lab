"""Finite Python abstraction of the Quint protocol, NOT a Quint interpreter.

Safety is exhaustively checked over *reachable* abstract states when the
finite graph is saturated. Liveness needs environmental/fairness assumptions.
"""
from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, replace
import argparse
import json
from pathlib import Path


@dataclass(frozen=True)
class State:
    phase: str = "PREPARED"
    authorized: bool = False
    bound: bool = False
    fresh: bool = False
    reconciled: bool = False
    effect_count: int = 0
    effect_authorized: bool = False
    receipt_observed: bool = False
    reported_success: bool = False


def successors(s: State) -> tuple[tuple[str, State], ...]:
    """Hand translation of named Quint actions; source parity is unproved."""
    edges: list[tuple[str, State]] = []

    def add(label: str, **updates: object) -> None:
        edges.append((label, replace(s, **updates)))

    if s.phase == "PREPARED":
        add("authorize", authorized=True)
    if s.authorized:
        add("bindEvidence", bound=True, fresh=True)
    if s.phase == "PREPARED" and s.authorized and s.bound and s.fresh:
        add("advance", phase="CLAIMED")
    if s.phase == "CLAIMED":
        add("interrupt", phase="INTERRUPTED")
        add("fail", phase="FAILED")
        if s.effect_count == 0:
            add("markUnknown", phase="UNKNOWN")
        if s.authorized and s.bound and s.fresh:
            add("advanceToExecute", phase="EXECUTING")
            if s.effect_count == 0:
                add("publish", phase="EXECUTING", effect_count=1,
                    effect_authorized=s.authorized and s.bound and s.fresh)
    if s.phase == "INTERRUPTED" and s.authorized and s.bound and s.fresh:
        add("resume", phase="CLAIMED")
    if s.phase in ("FAILED", "UNKNOWN") and s.effect_count == 0:
        add("reconcileNoEffect", reconciled=True)
    if s.phase in ("FAILED", "UNKNOWN") and s.reconciled and s.effect_count == 0:
        add("retry", phase="RECONCILING" if s.phase == "UNKNOWN" else "CLAIMED", reconciled=False)
    if s.phase == "EXECUTING" and s.effect_count == 1:
        add("observeEffect", phase="RECONCILED", receipt_observed=True)
    if s.phase == "RECONCILED" and s.effect_count == 1 and s.receipt_observed:
        add("terminal", phase="TERMINAL", reported_success=True)
    return tuple(edges)


def violation(s: State) -> str | None:
    if not (0 <= s.effect_count <= 1):
        return "noDuplicate"
    if s.effect_count != 0 and not s.effect_authorized:
        return "effectHasPreconditions"
    if s.reported_success and not (s.phase == "TERMINAL" and s.receipt_observed and s.effect_count == 1):
        return "receiptSupported"
    return None


def explore(max_depth: int = 12) -> dict[str, object]:
    if not (0 <= max_depth <= 100):
        raise ValueError("max_depth must be between 0 and 100")
    initial = State()
    queue = deque([(initial, tuple())])
    visited = {initial}
    transition_count = 0
    terminal_witness: tuple[str, ...] | None = None
    reconciliation_witness: tuple[str, ...] | None = None
    bound_reached = False
    while queue:
        state, path = queue.popleft()
        err = violation(state)
        if err is not None:
            return {"schema": "fvl.explicit_state.v2", "engine": "python_translation_not_quint",
                    "max_depth": max_depth, "status": "COUNTEREXAMPLE", "property": err,
                    "trace": list(path), "state": asdict(state), "visited_states": len(visited)}
        if state.phase == "TERMINAL" and terminal_witness is None:
            terminal_witness = path
        if state.phase == "RECONCILING" and reconciliation_witness is None:
            reconciliation_witness = path
        if len(path) == max_depth:
            if any(nxt not in visited for _, nxt in successors(state)):
                bound_reached = True
            continue
        for name, nxt in successors(state):
            transition_count += 1
            if nxt not in visited:
                visited.add(nxt)
                queue.append((nxt, path + (name,)))
    return {"schema": "fvl.explicit_state.v2", "engine": "python_translation_not_quint",
            "status": "BOUNDED_PASS", "claim_level": "FINITE_PYTHON_ABSTRACTION_ONLY",
            "max_depth": max_depth, "visited_states": len(visited),
            "examined_transitions": transition_count, "bound_reached": bound_reached,
            "terminal_witness": list(terminal_witness) if terminal_witness else None,
            "reconciliation_witness": list(reconciliation_witness) if reconciliation_witness else None,
            "liveness_claim": "NOT_ESTABLISHED", "quint_apalache": "NOT_RUN"}


def check_unsafe_canary() -> dict[str, object]:
    before = {"authorized": False, "effected": False}
    after = {"authorized": False, "effected": True}
    invariant = lambda x: (not x["effected"]) or x["authorized"]
    return {"status": "COUNTEREXAMPLE" if invariant(before) and not invariant(after) else "UNKNOWN",
            "engine": "python_translation_not_quint", "property": "unauthorizedEffectIsImpossible",
            "trace": ["init", "publishUnchecked"], "state": after, "quint_apalache": "NOT_RUN"}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--max-depth", type=int, default=12)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    result = {"safe": explore(args.max_depth), "canary": check_unsafe_canary()}
    output = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0 if result["safe"]["status"] == "BOUNDED_PASS" and result["canary"]["status"] == "COUNTEREXAMPLE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
