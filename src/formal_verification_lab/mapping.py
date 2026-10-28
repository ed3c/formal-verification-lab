"""Measure a supplied finite source-location relation, never semantic correctness."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .bundles import BundleError, _directory, _part


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise BundleError("mapping: " + message)


def _rows(value: Any, *, observed: bool) -> dict[str, dict[str, Any]]:
    _require(isinstance(value, dict) and isinstance(value.get("rows"), list), "rows must be a list")
    result = {}
    for row in value["rows"]:
        _require(isinstance(row, dict) and isinstance(row.get("id"), str) and bool(row["id"].strip()), "row.id")
        _require(row["id"] not in result, "duplicate id: " + row["id"])
        status = row.get("status", "resolved")
        _require(isinstance(status, str) and status in ("resolved", "unknown"), "row.status")
        _require(observed or status == "resolved", "expected truth cannot be unknown")
        if status == "resolved":
            _require(isinstance(row.get("path"), str) and bool(row["path"].strip())
                     and type(row.get("line")) is int and row["line"] > 0, "resolved path/line")
        result[row["id"]] = {**row, "status": status}
    return result


def measure_mapping(folder: str | Path, study_path: str) -> dict[str, Any]:
    root = _directory(folder)
    study, study_ref = _part(root, study_path)
    _require(isinstance(study, dict) and study.get("schema") == "fvl.mapping.v1", "schema")
    for field in ("scope", "revision", "expected_origin"):
        _require(isinstance(study.get(field), str) and bool(study[field].strip()), field)
    refs = [study_ref]
    sets = {}
    for field in ("expected", "observed"):
        selected = study.get(field)
        selected = selected if isinstance(selected, list) else [selected]
        _require(bool(selected), field + ": empty selected parts")
        rows = []
        for ref in selected:
            _require(isinstance(ref, dict) and set(ref) == {"path", "sha256"}
                     and isinstance(ref["path"], str) and isinstance(ref["sha256"], str), field + ".ref")
            value, actual = _part(root, ref["path"], ref["sha256"])
            # Validate every part, then also reject duplicate identities across parts.
            rows.extend(_rows(value, observed=field == "observed").values())
            refs.append(actual)
        sets[field] = _rows({"rows": rows}, observed=field == "observed")
    expected, observed = sets["expected"], sets["observed"]
    matched, wrong, extra, unknown, missing = [], [], [], [], []
    for name, row in expected.items():
        actual = observed.get(name)
        if actual is None:
            missing.append(name)
        elif actual["status"] == "unknown":
            unknown.append(name)
        elif (row["path"], row["line"]) == (actual["path"], actual["line"]):
            matched.append(name)
        else:
            wrong.append(name)
    extra = [name for name, row in observed.items() if name not in expected and row["status"] == "resolved"]
    tp, fp, fn = len(matched), len(wrong) + len(extra), len(expected) - len(matched)
    resolved_expected = len(matched) + len(wrong)
    return {"schema": "fvl.mapping.result.v1", "status": "FINITE_MAPPING_MEASURED", "scope": study["scope"],
            "revision": study["revision"], "expected_origin": study["expected_origin"], "source_refs": refs,
            "population": len(expected), "tp": tp, "fp": fp, "fn": fn,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / len(expected) if expected else None,
            "coverage": resolved_expected / len(expected) if expected else None,
            "unknown": unknown, "missing": missing, "wrong": wrong, "extra": extra,
            "extra_unknown": [name for name, row in observed.items() if name not in expected and row["status"] == "unknown"],
            "target": "precision and recall both strictly >0.99 on the supplied frozen population",
            "target_met_supplied_population": bool(expected) and 100 * tp > 99 * (tp + fp)
                                              and 100 * tp > 99 * (tp + fn),
            "ground_truth_review": "SESSION_REQUIRED", "selection_sufficiency": "NOT_EVALUATED",
            "retention_value": "NOT_EVALUATED", "native_conformance": "NOT_EVALUATED",
            "authorizes_landing": False, "authorizes_production_effect": False}
