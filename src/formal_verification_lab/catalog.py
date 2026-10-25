"""Describe supplied controls without selecting tests or deciding their value."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .bundles import BundleError, _directory, _part


GRANULARITIES = ("unit_method", "physical_family", "property", "proof_obligation", "query", "agent_case")
METHODS = ("unit", "contract", "integration", "e2e", "property", "model_check", "induction",
           "trace_conformance", "agent_eval", "source_check")
ENVIRONMENTS = ("local", "ci", "native")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise BundleError("catalog: " + message)


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _rows(value: Any, field: str) -> dict[str, dict[str, Any]]:
    _require(isinstance(value, list), field + " must be a list")
    result = {}
    for row in value:
        _require(isinstance(row, dict) and _text(row.get("id")), field + ".id")
        _require(row["id"] not in result, field + ": duplicate id " + row["id"])
        result[row["id"]] = row
    return result


def _labels(value: Any, allowed: Any, field: str) -> None:
    _require(isinstance(value, list) and all(isinstance(v, str) and v in allowed for v in value), field)
    _require(len(value) == len(set(value)), field + ": duplicate label")


def query_catalog(folder: str | Path, catalog_path: str, *, filters: dict[str, list[str]] | None = None,
                  include_controls: bool = False) -> dict[str, Any]:
    root = _directory(folder)
    packet, source_ref = _part(root, catalog_path)
    _require(isinstance(packet, dict) and packet.get("schema") == "fvl.test-catalog.v1", "schema")
    for field in ("scope", "revision", "method_notes"):
        _require(_text(packet.get(field)), field)
    modules = _rows(packet.get("modules"), "modules")
    for module in modules.values():
        _require(_text(module.get("statement")) and _text(module.get("basis")), "module statement/basis")
    source_refs = [source_ref]
    rows = packet.get("controls")
    _require(isinstance(rows, list), "controls must be a list")
    rows = list(rows)
    parts = packet.get("control_parts", [])
    _require(isinstance(parts, list), "control_parts must be a list")
    for ref in parts:
        _require(isinstance(ref, dict) and set(ref) == {"path", "sha256"}
                 and _text(ref.get("path")) and _text(ref.get("sha256")), "control_parts ref")
        part, actual = _part(root, ref["path"], ref["sha256"])
        _require(isinstance(part, dict) and isinstance(part.get("controls"), list), "control part.controls")
        rows.extend(part["controls"])
        source_refs.append(actual)
    controls = _rows(rows, "controls")
    gaps = []
    for name, row in controls.items():
        _require(isinstance(row.get("granularity"), str) and row["granularity"] in GRANULARITIES,
                 "granularity:" + name)
        for field, allowed in (("methods", METHODS), ("environments", ENVIRONMENTS), ("modules", modules)):
            _labels(row.get(field), allowed, field + ":" + name)
        _require(_text(row.get("source")), "source:" + name)
        retention, demand, protection = (row.get(field) for field in ("retention", "demand", "protection"))
        _require(isinstance(retention, dict) and isinstance(retention.get("decision"), str)
                 and retention["decision"] in ("keep", "rewrite") and _text(retention.get("ref")), "retention:" + name)
        _require(isinstance(demand, dict) and demand.get("mode") == "on_demand", "demand.mode:" + name)
        _require(isinstance(protection, dict), "protection:" + name)
        missing = [field for field in ("methods", "environments", "modules") if not row[field]]
        missing += ["demand." + field for field in ("condition", "ref") if not _text(demand.get(field))]
        missing += ["protection." + field for field in ("behavior", "oracle_ref", "discriminator_ref")
                    if not _text(protection.get(field))]
        if missing:
            gaps.append({"id": name, "missing": missing})
    ci = _rows(packet.get("ci_bindings"), "ci_bindings")
    ci_summary = []
    for name, row in ci.items():
        _require(_text(row.get("event")) and _text(row.get("source")), "ci event/source:" + name)
        _require(isinstance(row.get("selection"), str) and row["selection"] in ("dynamic", "explicit"), "ci selection:" + name)
        _labels(row.get("controls"), controls, "ci controls:" + name)
        if row["selection"] == "dynamic":
            _require(not row["controls"] and _text(row.get("condition")), "dynamic CI condition/empty list:" + name)
        _require(all("ci" in controls[key]["environments"] for key in row["controls"]), "CI member environment:" + name)
        ci_summary.append({**row, "control_count": len(row["controls"]) if row["selection"] == "explicit" else None})
    allowed_filters = {"modules": modules, "methods": METHODS, "environments": ENVIRONMENTS,
                       "granularity": GRANULARITIES}
    filters = filters or {}
    for field, values in filters.items():
        _require(field in allowed_filters, "unknown filter dimension:" + field)
        _labels(values, allowed_filters[field], "filter:" + field)
    selected = [row for row in controls.values() if all(
        not values or bool(set(values) & set([row[field]] if field == "granularity" else row[field]))
        for field, values in filters.items())]

    def counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
        return {"unique_records": len(rows),
                "by_granularity": dict(sorted(Counter(row["granularity"] for row in rows).items())),
                **{field: dict(sorted(Counter(value for row in rows for value in row[field]).items()))
                   for field in ("methods", "environments", "modules")},
                "retention": dict(sorted(Counter(row["retention"]["decision"] for row in rows).items())),
                "on_demand_by_granularity": dict(sorted(Counter(row["granularity"] for row in rows).items()))}

    result = {"schema": "fvl.test-catalog.result.v1", "status": "CATALOG_ONLY", "scope": packet["scope"],
              "revision": packet["revision"], "method_notes": packet["method_notes"], "source_refs": source_refs,
              "denominator": counts(list(controls.values())), "filtered": counts(selected), "filters": filters,
              "modules": list(modules.values()), "ci_bindings": ci_summary, "classification_gaps": gaps,
              "necessary_for_change": {"count": None, "reason": "No request-specific necessity relation is evaluated."},
              "counting_rule": "Unique IDs within each granularity; method, environment and module counts overlap.",
              "oracle_review": "SESSION_REQUIRED", "retention_decision": "NOT_EVALUATED",
              "tests_executed": 0, "model_checker": "NOT_RUN", "ci_dispatched": 0,
              "authorizes_landing": False, "authorizes_production_effect": False}
    if include_controls:
        result["controls"] = selected
    return result
