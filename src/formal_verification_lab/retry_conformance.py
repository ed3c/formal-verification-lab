"""Inspect selected retry evidence; local model membership is not Native refinement."""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, fields
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from typing import Any

from .model_explore import State, successors


class InputError(ValueError):
    pass


@dataclass(frozen=True)
class LifecycleEvent:
    seq: int
    kind: str
    order: str | None
    stage: int | None
    session: str | None
    line: int
    sha256: str


MAPPING = {
    "stage.failed": {"candidate_action": "markFailed", "domain": "worker", "status": "UNKNOWN"},
    "order.failed": {"candidate_action": None, "domain": "order", "status": "UNKNOWN"},
    "order.requeued": {"candidate_action": "retry", "domain": "worker", "status": "UNKNOWN"},
}
STATE_FIELDS = tuple(field.name for field in fields(State))
PHASES = frozenset({"PREPARED", "CLAIMED", "EXECUTING", "FAILED", "UNKNOWN", "INTERRUPTED",
                    "RECONCILING", "RECONCILED", "TERMINAL"})
ACTIONS = frozenset({"authorize", "bindEvidence", "advance", "advanceToExecute", "publish", "interrupt",
                     "resume", "markFailed", "fail", "markUnknown", "reconcileNoEffect", "retry", "observeEffect", "terminal"})
EFFECT_GAPS = ["operation pre-phase", "ordered no-effect reconciliation", "matching complete effect scope"]


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json(raw: bytes) -> Any:
    if type(raw) is not bytes:
        raise InputError("JSON input must be bytes")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise InputError("duplicate JSON key")
            result[key] = value
        return result

    def constant(value):
        raise InputError("nonfinite JSON number")

    def floating(value):
        number = float(value)
        if not math.isfinite(number):
            raise InputError("nonfinite JSON number")
        return number

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=constant, parse_float=floating)
        json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
        return value
    except InputError:
        raise
    except (UnicodeError, ValueError, RecursionError) as error:
        raise InputError("invalid UTF-8 JSON") from error


def _lines(raw: bytes) -> list[tuple[int, bytes, dict]]:
    if type(raw) is not bytes:
        raise InputError("JSONL input must be bytes")
    result = []
    for number, line in enumerate(raw.splitlines(keepends=True), 1):
        if not line.strip():
            raise InputError("blank JSONL record at line " + str(number))
        value = _json(line)
        if type(value) is not dict:
            raise InputError("JSONL record must be an object at line " + str(number))
        result.append((number, line, value))
    return result


def _text(value: Any) -> bool:
    return type(value) is str and bool(value)


def parse_lifecycle(raw: bytes, max_events: int = 200) -> tuple[LifecycleEvent, ...]:
    if type(max_events) is not int or max_events < 1:
        raise InputError("max_events must be a positive integer")
    lines = _lines(raw)
    if len(lines) > max_events:
        raise InputError("lifecycle event read bound exceeded; no truncation performed")
    result = []
    previous = 0
    for number, line, value in lines:
        if not {"seq", "type", "at"} <= value.keys() or set(value) - {"seq", "type", "at", "payload"}:
            raise InputError("lifecycle fields must be seq/type/at/payload")
        seq, kind, at = value["seq"], value["type"], value["at"]
        if type(seq) is not int or seq <= previous:
            raise InputError("lifecycle seq must be positive, unique and strictly increasing")
        if not _text(kind) or not _text(at):
            raise InputError("lifecycle type and at must be nonempty strings")
        payload = value.get("payload", {})
        if type(payload) is not dict:
            raise InputError("lifecycle payload must be an object")
        order, stage, session = (payload.get(name) for name in ("order_id", "stage_index", "session_id"))
        if kind in MAPPING and not _text(order):
            raise InputError("mapped lifecycle event requires order_id")
        if order is not None and not _text(order):
            raise InputError("order_id must be a nonempty string")
        if stage is not None and (type(stage) is not int or stage < 0):
            raise InputError("lifecycle stage_index must be a nonnegative integer")
        if session is not None and not _text(session):
            raise InputError("session_id must be a nonempty string")
        result.append(LifecycleEvent(seq, kind, order, stage, session, number, _sha(line)))
        previous = seq
    return tuple(result)


def analyze_lifecycle(raw: bytes, max_events: int = 200) -> dict:
    events = parse_lifecycle(raw, max_events)
    records = []
    orders: dict[str, list[LifecycleEvent]] = {}
    gaps = []
    for index, event in enumerate(events):
        if index and event.seq > events[index - 1].seq + 1:
            gaps.append({"from": events[index - 1].seq + 1, "to": event.seq - 1})
        record = asdict(event)
        record["mapping"] = MAPPING.get(event.kind, {"candidate_action": None, "domain": "unmapped", "status": "UNKNOWN"}).copy()
        records.append(record)
        if event.order is not None:
            orders.setdefault(event.order, []).append(event)
    requeues = []
    for order, selected in orders.items():
        for requeue in [event for event in selected if event.kind == "order.requeued"]:
            failures = [event for event in selected if event.kind == "order.failed" and event.seq < requeue.seq]
            order_failure = failures[-1] if failures else None
            stage_failures = [event for event in selected if event.kind == "stage.failed"
                              and order_failure is not None and event.seq < order_failure.seq]
            stage_failure = stage_failures[-1] if stage_failures else None
            requeues.append({"order_id": order, "requeue_seq": requeue.seq,
                             "observed_prefix": "OBSERVED_ORDERED_PREFIX" if stage_failure else "UNKNOWN",
                             "stage_failed_seq": stage_failure.seq if stage_failure else None,
                             "order_failed_seq": order_failure.seq if order_failure else None,
                             "candidate_action": "retry", "model_conformance": "UNKNOWN",
                             "missing": list(EFFECT_GAPS), "new_attempt_started": None})
    return {"schema": "fvl.retry.lifecycle.v1", "source_sha256": _sha(raw), "source_bytes": len(raw),
            "event_count": len(events), "events": records, "sequence_gaps": gaps,
            "first_seq": events[0].seq if events else None, "last_seq": events[-1].seq if events else None,
            "coverage": "BEST_EFFORT_NOT_COMPLETE_PROOF", "read_bound": max_events,
            "requeues": requeues, "full_native_refinement": "NOT_ESTABLISHED"}


def _state(value: Any, name: str) -> tuple[State | None, list[str]]:
    if value is None:
        return None, [name + "." + field for field in STATE_FIELDS]
    if type(value) is not dict or set(value) - set(STATE_FIELDS):
        raise InputError(name + " must contain only operation State fields")
    for field, actual in value.items():
        valid = type(actual) is str if field == "phase" else type(actual) is int if field == "effect_count" else type(actual) is bool
        if not valid:
            raise InputError(name + "." + field + " has the wrong type")
    missing = [name + "." + field for field in STATE_FIELDS if field not in value]
    if "phase" in value and value["phase"] not in PHASES:
        missing.append(name + ".operation_domain_phase")
    if missing:
        return None, missing
    return State(**value), []


def check_model_step(action, before, after) -> dict:
    """Check explicit operation states against one named local model edge, not reachability."""
    prior, missing_before = _state(before, "before")
    following, missing_after = _state(after, "after")
    missing = missing_before + missing_after
    if type(action) is not str or action not in ACTIONS:
        missing.append("supported operation action")
    result = {"action": action, "before": before, "after": after, "scope": "EXPLICIT_OPERATION_LOCAL_STEP",
              "caller_supplied_operation_states": True, "global_reachability": "NOT_ESTABLISHED",
              "full_native_refinement": "NOT_ESTABLISHED", "missing": missing}
    if missing:
        return {**result, "status": "UNKNOWN", "diagnostic": "operation observation incomplete or outside mapped domain"}
    python_action = "fail" if action == "markFailed" else action
    enabled = [(label, state) for label, state in successors(prior) if label == python_action]
    matches = any(state == following for _, state in enabled)
    return {**result, "python_action": python_action, "status": "BOUNDED_PASS" if matches else "COUNTEREXAMPLE",
            "diagnostic": "named local transition matched" if matches else
                          "action disabled in observed before state" if not enabled else "after state differs from named successor",
            "named_successors": [asdict(state) for _, state in enabled]}


def _stage(value: Any) -> int | None:
    if value is None:
        return None
    if type(value) is int and value >= 0:
        return value
    if type(value) is str and re.fullmatch(r"0|[1-9][0-9]*", value):
        try:
            return int(value)
        except ValueError as error:
            raise InputError("spawn stage_index decimal exceeds the integer decoder limit") from error
    raise InputError("spawn stage_index must be integer or canonical nonnegative decimal string")


def _native(raw: bytes | None) -> dict:
    if raw is None:
        return {"sha256": None, "threads": [], "terminals": []}
    threads, terminals = [], []
    for number, _, value in _lines(raw):
        if value.get("type") == "thread.started" and _text(value.get("thread_id")):
            threads.append({"line": number, "thread_id": value["thread_id"]})
        if value.get("type") in ("turn.completed", "turn.failed"):
            terminals.append({"line": number, "type": value["type"]})
    return {"sha256": _sha(raw), "bytes": len(raw), "threads": threads, "terminals": terminals}


def _equal(left, right):
    return left == right if left is not None and right is not None else None


def _selected_snapshot(snapshot, order, stage, previous_session, resumed_session) -> dict:
    result = {"status": "UNKNOWN", "attempts": [], "dispatch_effects": [], "distinct_attempt_ids": None,
              "ambiguities": [], "dispatch_ambiguities": []}
    if snapshot is None or order is None or stage is None:
        return result
    if type(snapshot) is not dict:
        raise InputError("snapshot must be an object")
    state = snapshot.get("state", {})
    if type(state) is not dict or type(state.get("orders", {})) is not dict:
        raise InputError("snapshot state/orders must be objects")
    selected_order = state.get("orders", {}).get(order)
    if selected_order is None:
        return result
    if type(selected_order) is not dict or type(selected_order.get("stages", [])) is not list:
        raise InputError("snapshot order/stages have wrong types")
    stages = selected_order.get("stages", [])
    if stage >= len(stages):
        return result
    selected_stage = stages[stage]
    if type(selected_stage) is not dict or type(selected_stage.get("attempts", [])) is not list:
        raise InputError("snapshot stage/attempts have wrong types")
    attempts = selected_stage.get("attempts", [])
    for role, session in (("previous", previous_session), ("resumed", resumed_session)):
        matches = [item for item in attempts if type(item) is dict and session is not None and item.get("session_id") == session]
        if len(matches) != 1:
            result["ambiguities"].append({"role": role, "matches": len(matches)})
        else:
            item = matches[0]
            result["attempts"].append({"role": role, **{key: item.get(key) for key in
                                    ("attempt_id", "session_id", "status", "exit_code")}})
    if not result["ambiguities"] and len(result["attempts"]) == 2:
        ids = [item["attempt_id"] for item in result["attempts"]]
        result["distinct_attempt_ids"] = len(set(ids)) == 2 if all(_text(item) for item in ids) else None
        result["status"] = "OBSERVED_ATTEMPT_BINDING" if result["distinct_attempt_ids"] is True else "UNKNOWN"
    ledger = snapshot.get("effect_ledger", [])
    if type(ledger) is not list:
        raise InputError("snapshot effect_ledger must be an array")
    for entry in ledger:
        if type(entry) is not dict:
            raise InputError("snapshot effect ledger entry must be an object")
        effect = entry.get("effect", {})
        if type(effect) is not dict:
            raise InputError("snapshot effect must be an object")
        payload = effect.get("payload", {})
        if type(payload) is not dict:
            raise InputError("snapshot effect payload must be an object")
        if effect.get("type") == "dispatch" and payload.get("order_id") == order:
            dispatch_stage = payload.get("stage_index")
            if dispatch_stage is None:
                result["dispatch_ambiguities"].append({"effect_id": entry.get("effect_id"),
                                                      "stage_index": None, "reason": "stage_index unavailable"})
                continue
            if type(dispatch_stage) is not int or dispatch_stage < 0:
                raise InputError("snapshot dispatch stage_index must be a nonnegative integer")
            if dispatch_stage == stage:
                result["dispatch_effects"].append({"effect_id": entry.get("effect_id"), "status": entry.get("status"),
                                                   "attempts": entry.get("attempts"), "payload": payload})
    result["order_status"] = selected_order.get("status")
    result["stage_status"] = selected_stage.get("status")
    return result


def inspect_resume(previous_spawn, resumed_spawn, previous_raw, resumed_raw, snapshot=None) -> dict:
    """Inspect explicit resume bindings; terminal messages do not establish process or task success."""
    for name, spawn in (("previous_spawn", previous_spawn), ("resumed_spawn", resumed_spawn)):
        if spawn is not None and type(spawn) is not dict:
            raise InputError(name + " must be an object")
    previous, resumed = previous_spawn or {}, resumed_spawn or {}
    for spawn in (previous, resumed):
        for key in ("session_id", "order_id", "resume_session_id", "resume_thread_id", "resume_source_sha256"):
            if key in spawn and spawn[key] is not None and not _text(spawn[key]):
                raise InputError("spawn " + key + " must be a nonempty string")
    prior_native, current_native = _native(previous_raw), _native(resumed_raw)
    previous_stage, resumed_stage = _stage(previous.get("stage_index")), _stage(resumed.get("stage_index"))
    prior_threads = prior_native["threads"]
    current_threads = current_native["threads"]
    prior_thread = prior_threads[0]["thread_id"] if len(prior_threads) == 1 else None
    current_thread = current_threads[0]["thread_id"] if len(current_threads) == 1 else None
    retry_count = resumed.get("retry_count")
    if retry_count is not None and (type(retry_count) is not int or retry_count < 0):
        raise InputError("retry_count must be a nonnegative integer")
    checks = {"predecessor_session": _equal(resumed.get("resume_session_id"), previous.get("session_id")),
              "order": _equal(resumed.get("order_id"), previous.get("order_id")),
              "stage": _equal(previous_stage, resumed_stage),
              "source_sha256": _equal(resumed.get("resume_source_sha256"), prior_native["sha256"]),
              "prior_thread": _equal(resumed.get("resume_thread_id"), prior_thread),
              "current_thread": _equal(resumed.get("resume_thread_id"), current_thread),
              "retry_count": retry_count > 0 if retry_count is not None else None}
    selected = _selected_snapshot(snapshot, previous.get("order_id"), previous_stage,
                                  previous.get("session_id"), resumed.get("session_id"))
    status = "COUNTEREXAMPLE" if False in checks.values() else "UNKNOWN" if None in checks.values() else "BOUNDED_PASS"
    return {"schema": "fvl.retry.resume.v1", "status": status, "scope": "SELECTED_RESUME_BINDINGS_ONLY",
            "checks": checks, "previous_native": prior_native, "resumed_native": current_native,
            "stage_encoding": {"previous_raw": previous.get("stage_index"), "resumed_raw": resumed.get("stage_index"),
                               "previous_normalized": previous_stage, "resumed_normalized": resumed_stage,
                               "conversion": "explicit_spawn_decimal_to_integer"},
            "snapshot": selected, "operation_retry_conformance": "UNKNOWN", "missing": list(EFFECT_GAPS),
            "process_exit": "UNKNOWN", "full_native_refinement": "NOT_ESTABLISHED"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", required=True)
    for name in ("previous-spawn", "resumed-spawn", "previous-raw", "resumed-raw", "snapshot", "model-steps"):
        parser.add_argument("--" + name)
    parser.add_argument("--max-events", type=int, default=200)
    args = parser.parse_args(argv)
    try:
        sources = []

        def selected(name, structured=False):
            path = getattr(args, name)
            if path is None:
                return None
            raw = Path(path).read_bytes()
            sources.append({"role": name, "path": path, "sha256": _sha(raw), "bytes": len(raw)})
            return _json(raw) if structured else raw

        lifecycle = analyze_lifecycle(selected("events"), args.max_events)
        resume = inspect_resume(selected("previous_spawn", True), selected("resumed_spawn", True),
                                selected("previous_raw"), selected("resumed_raw"), selected("snapshot", True))
        observations = selected("model_steps", True)
        steps = []
        if observations is not None:
            if type(observations) is not dict or set(observations) != {"schema", "steps"} or type(observations["schema"]) is not int or observations["schema"] != 1 or type(observations["steps"]) is not list:
                raise InputError("model-steps requires schema=1 and steps array")
            for item in observations["steps"]:
                if type(item) is not dict or set(item) != {"action", "before", "after"}:
                    raise InputError("model step requires only action/before/after")
                steps.append(check_model_step(**item))
        result = {"schema": "fvl.retry.conformance.v1", "lifecycle": lifecycle, "resume": resume,
                  "local_model_steps": steps, "sources": sources, "native_model_conformance": "UNKNOWN",
                  "full_native_refinement": "NOT_ESTABLISHED"}
        sys.stdout.write(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2) + "\n")
        return 0
    except (InputError, OSError) as error:
        print(type(error).__name__ + ": " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
