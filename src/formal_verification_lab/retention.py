"""Check a declared finite test-replacement relation, without executing target code."""
from __future__ import annotations

import platform
import time
from pathlib import Path
from typing import Any

from .bundles import BundleError, SelectionPathError, _directory, _part


def _require(condition: bool, field: str) -> None:
    if not condition:
        raise BundleError("retention: " + field)


def _rows(value: Any, field: str) -> dict[str, dict[str, Any]]:
    _require(isinstance(value, list), field + " must be a list")
    result = {}
    for row in value:
        _require(isinstance(row, dict) and isinstance(row.get("id"), str) and bool(row["id"]), field + ".id")
        _require(row["id"] not in result, field + ": duplicate id " + row["id"])
        result[row["id"]] = row
    return result


def evaluate_retention(folder: str | Path, study_path: str) -> dict[str, Any]:
    started = time.monotonic()
    root = _directory(folder)
    study, study_ref = _part(root, study_path)
    _require(isinstance(study, dict) and study.get("schema") == "fvl.retention.v1", "schema")
    _require(isinstance(study.get("scope"), str) and bool(study["scope"]), "scope")
    contracts = _rows(study.get("contracts"), "contracts")
    tests = _rows(study.get("tests"), "tests")
    scenarios = _rows(study.get("scenarios"), "scenarios")
    selected = {}
    for label in ("baseline", "candidate"):
        values = study.get(label)
        _require(isinstance(values, list) and all(isinstance(value, str) and value in tests for value in values), label)
        _require(len(values) == len(set(values)), label + ": duplicate test")
        selected[label] = values
    refs = [study_ref]
    errors = []

    def read(ref: Any, subject: str) -> tuple[dict[str, Any] | None, str | None]:
        _require(isinstance(ref, dict) and set(ref) == {"path", "sha256"}, subject + ".ref")
        _require(isinstance(ref["path"], str) and isinstance(ref["sha256"], str), subject + ".ref values")
        try:
            value, actual = _part(root, ref["path"], ref["sha256"])
            _require(isinstance(value, dict), subject + ": expected object")
        except SelectionPathError:
            raise
        except (OSError, ValueError) as error:
            errors.append({"subject": subject, "path": ref["path"], "reason": str(error)})
            return None, None
        refs.append(actual)
        return value, actual["sha256"]

    oracle = {}
    for name, contract in contracts.items():
        value, _ = read(contract.get("ref"), "contract:" + name)
        oracle[name] = bool(value and value.get("basis") in ("requirement", "compatibility", "bug")
                            and isinstance(value.get("statement"), str) and value["statement"]
                            and isinstance(value.get("source"), str) and value["source"])
    contexts = {}
    sources = {}
    for name, test in tests.items():
        source, sources[name] = read(test.get("source"), "test:" + name)
        context, digest = read(test.get("context"), "context:" + name)
        context_known = (context is not None and all(isinstance(context.get(field), str) and context[field].strip()
                                                    for field in ("entrypoint", "input_recipe")))
        contexts[name] = digest if source is not None and context_known else None
    inputs = {}
    for name, scenario in scenarios.items():
        _require(scenario.get("kind") in ("valid", "fault"), "scenario.kind:" + name)
        if scenario["kind"] == "fault":
            _require(isinstance(scenario.get("contract"), str) and scenario["contract"] in contracts,
                     "scenario.contract:" + name)
        _, inputs[name] = read(scenario.get("input"), "input:" + name)
    observations = study.get("observations")
    _require(isinstance(observations, list), "observations")
    outcomes = {}
    for row in observations:
        _require(isinstance(row, dict) and isinstance(row.get("test"), str) and row["test"] in tests
                 and isinstance(row.get("scenario"), str) and row["scenario"] in scenarios, "observation identity")
        test, case = row["test"], row["scenario"]
        _require((test, case) not in outcomes, "duplicate observation:" + test + ":" + case)
        trace, _ = read(row.get("ref"), "observation:" + test + ":" + case)
        comparable = (trace is not None and inputs[case] is not None and contexts[test] is not None
                      and trace.get("test") == test and trace.get("scenario") == case
                      and trace.get("test_source_sha256") == sources[test]
                      and trace.get("input_sha256") == inputs[case]
                      and trace.get("context_sha256") == contexts[test])
        outcomes[test, case] = trace if comparable else None
    valid = [name for name, case in scenarios.items() if case["kind"] == "valid"]
    faults = [name for name, case in scenarios.items() if case["kind"] == "fault"]
    positives = {}
    findings = []
    used = set(selected["baseline"]) | set(selected["candidate"])
    for test in used:
        values = [outcomes.get((test, case)) for case in valid]
        positives[test] = bool(values) and all(value and value.get("outcome") == "passed"
                                                and value.get("phase") == "complete" for value in values)
        if any(value and value.get("outcome") == "assertion_failed" and value.get("phase") == "body" for value in values):
            findings.append({"property_id": "FVL-RETENTION-POSITIVE", "test": test, "status": "COUNTEREXAMPLE"})
    known_contexts = {contexts[test] for test in used if contexts[test] is not None}
    comparable_context = bool(used) and len(known_contexts) == 1 and all(contexts[test] is not None for test in used)
    for case in faults:
        witnesses = {}
        for label, names in selected.items():
            witnesses[label] = [test for test in names if positives[test]
                                and (value := outcomes.get((test, case)))
                                and value.get("outcome") == "assertion_failed" and value.get("phase") == "body"]
        names = selected["candidate"]
        observed_miss = bool(names) and all(positives[test] and (value := outcomes.get((test, case)))
                                          and value.get("outcome") == "passed"
                                          and value.get("phase") == "complete" for test in names)
        supported = oracle[scenarios[case]["contract"]] and comparable_context
        status = ("BOUNDED_PASS" if supported and witnesses["baseline"] and witnesses["candidate"] else
                  "COUNTEREXAMPLE" if supported and witnesses["baseline"] and (not names or observed_miss) else "UNKNOWN")
        findings.append({"property_id": "FVL-RETENTION-COVERAGE", "scenario": case,
                         "contract": scenarios[case]["contract"], "status": status, "witnesses": witnesses})
    if not valid or not faults or not contracts or any(not any(scenarios[name]["contract"] == contract for name in faults)
                                                     for contract in contracts):
        findings.append({"property_id": "FVL-RETENTION-NONVACUITY", "status": "UNKNOWN"})
    statuses = {finding["status"] for finding in findings}
    verdict = ("COUNTEREXAMPLE" if "COUNTEREXAMPLE" in statuses else
               "BOUNDED_PASS" if statuses == {"BOUNDED_PASS"} else "UNKNOWN")
    return {"schema": "fvl.retention.result.v1", "verdict": verdict, "scope": study["scope"],
            "method": "EXHAUSTIVE_FINITE_RELATION", "model_checker": "NOT_RUN",
            "findings": findings, "source_refs": refs, "selection_errors": errors,
            "oracle_review": "SESSION_REQUIRED", "retention_decision": "SESSION_REQUIRED",
            "assumptions": ["Supplied contract meaning and finite fault domain require Session review.",
                            "Context and trace digests establish consistency, not authenticity or arbitrary program equivalence."],
            "non_claims": ["global test value", "Native conformance", "defect yield", "CPVC", "production acceptance"],
            "cost": {"seconds": round(time.monotonic() - started, 6), "usd": None},
            "tool": {"python": platform.python_version()}, "authorizes_landing": False,
            "authorizes_production_effect": False}
