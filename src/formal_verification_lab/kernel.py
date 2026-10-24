"""Scoped conformance checks on supplied facts, not runtime effect authority."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Iterable

from .bundles import PARTS


class Verdict(str, Enum):
    BOUNDED_PASS = "BOUNDED_PASS"
    COUNTEREXAMPLE = "COUNTEREXAMPLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Finding:
    property_id: str
    status: Verdict
    detail: str


ALLOWED: dict[str, set[tuple[str, str]]] = {
    "ADVANCE": {("PREPARED", "CLAIMED"), ("CLAIMED", "EXECUTING")},
    "PUBLISH": {("CLAIMED", "EXECUTING")},
    "RESUME": {("INTERRUPTED", "CLAIMED")},
    "RETRY": {("FAILED", "CLAIMED"), ("UNKNOWN", "RECONCILING")},
    "TERMINAL": {("RECONCILED", "TERMINAL")},
}
PROPERTIES = (
    "FVL-SCHEMA", "FVL-LEGAL", "FVL-AUTH", "FVL-BIND", "FVL-FRESH",
    "FVL-IDEMPOTENCY", "FVL-CHECKPOINT", "FVL-RETRY", "FVL-POST-BIND",
    "FVL-NO-DUPLICATE", "FVL-EFFECT-RECEIPT", "FVL-TERMINAL", "FVL-NO-FALSE-SUCCESS",
)


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _sequence(value: Any) -> bool:
    return type(value) is int and value >= 0


def _tri(value: bool | None, ident: str, good: str, bad: str, missing: str) -> Finding:
    if value is None:
        return Finding(ident, Verdict.UNKNOWN, missing)
    return Finding(ident, Verdict.BOUNDED_PASS if value else Verdict.COUNTEREXAMPLE,
                   good if value else bad)


def evaluate(record: dict[str, Any], properties: Iterable[str] | None = None) -> dict[str, Any]:
    """Evaluate available normalized facts; missing inputs affect only dependent checks.

    Explicit partial selection does not assert that omitted evidence was absent
    from the original execution. A complete case claiming success is also checked
    for unsupported acceptance. No result grants production or merge permission.
    """
    if not isinstance(record, dict):
        raise ValueError("Evidence record must be an object")
    selected = tuple(properties) if properties is not None else None
    if selected is not None:
        if not selected or any(name not in PROPERTIES for name in selected):
            raise ValueError("Select known FVL properties")
        if len(set(selected)) != len(selected):
            raise ValueError("Duplicate selected property")
    op = record.get("operation")
    op = op if isinstance(op, dict) else {}
    auth = record.get("authority")
    ev = record.get("evidence")
    pre = record.get("preflight")
    post = record.get("provider")
    kind = op.get("kind")
    modeled_kind = isinstance(kind, str) and kind in ALLOWED
    ident, session, action_seq = (op.get(name) for name in ("operation_id", "session_id", "action_seq"))
    identity_available = _text(ident) and _text(session) and _sequence(action_seq)
    findings = [_tri(True if modeled_kind and identity_available else None, "FVL-SCHEMA",
                     "Normalized operation identity and sequence supplied", "Invalid operation",
                     "Operation kind, identity or sequence unavailable; no values invented")]

    transition_ok = None
    if modeled_kind and _text(op.get("from_state")) and _text(op.get("to_state")):
        transition_ok = (op["from_state"], op["to_state"]) in ALLOWED[kind]
    findings.append(_tri(transition_ok, "FVL-LEGAL", "Legal modeled transition", "Illegal transition",
                         "Modeled operation or transition endpoints unavailable"))

    auth_ok = None
    if identity_available and modeled_kind and isinstance(auth, dict):
        if (all(name in auth for name in ("operation_id", "session_id", "authorized", "allowed_kinds", "epoch", "seq"))
                and _sequence(auth["seq"]) and _sequence(auth["epoch"])
                and type(auth["authorized"]) is bool and isinstance(auth["allowed_kinds"], list)):
            auth_ok = (auth["operation_id"] == ident and auth["session_id"] == session
                       and auth["authorized"] and kind in auth["allowed_kinds"] and auth["seq"] <= action_seq)
    findings.append(_tri(auth_ok, "FVL-AUTH", "Supplied grant identity/scope/order match",
                         "Foreign, denied, out-of-scope or future grant", "Grant facts or operation binding unavailable"))

    bound = None
    if identity_available and _text(op.get("head")) and isinstance(ev, dict):
        if (all(name in ev for name in ("operation_id", "session_id", "head", "captured_seq", "digest"))
                and _sequence(ev["captured_seq"]) and isinstance(ev["digest"], str) and len(ev["digest"]) == 64):
            bound = (ev["operation_id"] == ident and ev["session_id"] == session
                     and ev["head"] == op["head"] and ev["captured_seq"] <= action_seq)
    findings.append(_tri(bound, "FVL-BIND", "Evidence identity/head bound", "Evidence identity/head drift",
                         "Evidence binding missing or malformed"))

    fresh = None
    if identity_available and _text(op.get("head")) and all(isinstance(x, dict) for x in (pre, ev, auth)):
        if (all(name in pre for name in ("operation_id", "head", "observed_seq", "authority_epoch"))
                and _sequence(pre["observed_seq"]) and _sequence(pre["authority_epoch"])
                and _sequence(ev.get("captured_seq")) and _sequence(auth.get("epoch")) and _sequence(auth.get("seq"))):
            if bound is False:
                fresh = False
            elif bound is True and _text(auth.get("operation_id")) and _text(auth.get("session_id")):
                auth_subject = auth["operation_id"] == ident and auth["session_id"] == session
                fresh = (auth_subject and pre["operation_id"] == ident
                         and pre["head"] == ev.get("head") == op["head"] and pre["authority_epoch"] == auth["epoch"]
                         and ev["captured_seq"] <= pre["observed_seq"] <= action_seq and auth["seq"] <= pre["observed_seq"])
    findings.append(_tri(fresh, "FVL-FRESH", "Pre-effect head and grant epoch agree",
                         "Stale head/epoch or invalid order", "Qualified pre-effect facts unavailable"))

    post_matches = None
    if _text(ident) and _sequence(action_seq) and isinstance(post, dict):
        if "operation_id" in post and _sequence(post.get("observed_seq")):
            if kind == "RETRY":
                prior = op.get("prior_attempt_seq")
                ordering = prior <= post["observed_seq"] < action_seq if _sequence(prior) else None
            else:
                ordering = post["observed_seq"] >= action_seq
            post_matches = post["operation_id"] == ident and ordering if ordering is not None else None
            if not _text(op.get("idempotency_key")) or "idempotency_key" not in post:
                post_matches = None
            else:
                post_matches = post_matches and post["idempotency_key"] == op["idempotency_key"]
    no_duplicate = None
    if post_matches is True and isinstance(post, dict) and _sequence(post.get("effect_count")):
        if post["effect_count"] > 1:
            no_duplicate = False
        elif post.get("complete") is True:
            no_duplicate = True

    effect = kind == "PUBLISH" or op.get("requests_effect") is True
    if effect:
        idempotent = None
        if "idempotency_key" in op and not _text(op["idempotency_key"]):
            idempotent = False
        elif _text(op.get("idempotency_key")):
            idempotent = False if post_matches is False else no_duplicate
        findings.append(_tri(idempotent, "FVL-IDEMPOTENCY", "Stable bound operation key and at-most-once scope observed",
                             "Operation key or qualified effect scope is inconsistent", "Qualified operation key/effect scope unavailable"))
    if kind == "RESUME":
        checkpoint = None
        if bound is False:
            checkpoint = False
        elif bound is True and isinstance(ev, dict) and "checkpoint_digest" in ev and "checkpoint_digest" in op:
            checkpoint = _text(ev["checkpoint_digest"]) and ev["checkpoint_digest"] == op["checkpoint_digest"]
        findings.append(_tri(checkpoint, "FVL-CHECKPOINT", "Checkpoint digest bound", "Checkpoint differs",
                             "Checkpoint unavailable"))
    if kind == "RETRY":
        reconciliation = None
        if post_matches is False:
            reconciliation = False
        elif post_matches is True and isinstance(post, dict) and _sequence(post.get("effect_count")) and type(post.get("reconciled")) is bool:
            if not post["reconciled"] or post["effect_count"] != 0:
                reconciliation = False
            elif post.get("complete") is True:
                reconciliation = True
        findings.append(_tri(reconciliation, "FVL-RETRY", "Readback reconciled no prior effect",
                             "Retry without no-effect reconciliation", "Prior effect status unknown"))

    if effect or kind in ("TERMINAL", "RETRY"):
        findings.append(_tri(post_matches, "FVL-POST-BIND", "Readback operation/key/time match",
                             "Readback disagrees with operation, key or time", "Readback binding unavailable"))
    if effect or kind in ("TERMINAL", "RETRY") or isinstance(post, dict) and "effect_count" in post:
        findings.append(_tri(no_duplicate, "FVL-NO-DUPLICATE", "Complete readback shows at most one effect",
                             "Readback reports more than one effect", "Complete effect scope not observed"))
    if effect and op.get("reports_success") is True:
        receipt = None
        if (post_matches is not None and isinstance(post, dict)
                and _sequence(post.get("effect_count")) and type(post.get("effect_confirmed")) is bool):
            receipt = post_matches and post["effect_count"] == 1 and post["effect_confirmed"]
        findings.append(_tri(receipt, "FVL-EFFECT-RECEIPT", "Single effect confirmed in bound readback",
                             "Success contradicts effect readback", "Effect confirmation unavailable"))
    if kind == "TERMINAL":
        terminal = None
        if (post_matches is not None and isinstance(post, dict)
                and type(post.get("terminal_receipt")) is bool and _sequence(post.get("effect_count"))):
            if not post["terminal_receipt"] or post["effect_count"] != 1 or not post_matches:
                terminal = False
            elif post.get("complete") is True:
                terminal = True
        findings.append(_tri(terminal, "FVL-TERMINAL", "Bound terminal receipt and single effect observed",
                             "Terminal contradicts effect receipt", "Terminal receipt or complete scope unavailable"))

    if op.get("reports_success") is True:
        incomplete = [f.property_id for f in findings if f.status is not Verdict.BOUNDED_PASS]
        partial = record.get("provenance") == "selected_offline" or any(part not in record for part in PARTS)
        supported = not incomplete
        if partial and incomplete and not any(f.status is Verdict.COUNTEREXAMPLE for f in findings):
            supported = None
        findings.append(_tri(supported, "FVL-NO-FALSE-SUCCESS", "Reported success has scoped support",
                             "Unsupported success claim: " + ",".join(incomplete),
                             "Selected evidence does not establish whether the success claim was supported"))
    return _out(record, op, findings, selected)


def _out(record: dict[str, Any], op: dict[str, Any], findings: list[Finding], selected: tuple[str, ...] | None) -> dict[str, Any]:
    if selected is not None:
        by_name = {finding.property_id: finding for finding in findings}
        findings = [by_name.get(name, Finding(name, Verdict.UNKNOWN,
                    "Property not applicable or its operation context is unavailable")) for name in selected]
    if any(f.status is Verdict.COUNTEREXAMPLE for f in findings):
        verdict = Verdict.COUNTEREXAMPLE
    elif not findings or any(f.status is Verdict.UNKNOWN for f in findings):
        verdict = Verdict.UNKNOWN
    else:
        verdict = Verdict.BOUNDED_PASS
    return {
        "schema": "fvl.finding.v1", "operation_id": op.get("operation_id"), "verdict": verdict.value,
        "claim_level": "SYNTHETIC_CONFORMANCE" if record.get("provenance") == "synthetic" else "UNAUTHENTICATED_OFFLINE_READBACK",
        "scope": "SELECTED_PROPERTIES" if selected is not None else "APPLICABLE_PROPERTIES",
        "requested_properties": list(selected) if selected is not None else None,
        "selected_parts": [part for part in PARTS if part in record],
        "missing_parts": [part for part in PARTS if part not in record],
        "source_refs": record.get("source_refs", {}),
        "requested_parts": record.get("requested_parts"), "selection_errors": record.get("selection_errors", []),
        "observations": {"provider_effect_count": record["provider"].get("effect_count")} if isinstance(record.get("provider"), dict) else {},
        "authorizes_landing": False, "authorizes_production_effect": False, "production_acceptance": "NOT_RUN",
        "findings": [{**asdict(f), "status": f.status.value} for f in findings],
    }
