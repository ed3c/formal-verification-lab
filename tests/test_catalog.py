from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from formal_verification_lab.cli import main
from formal_verification_lab.catalog import query_catalog


def packet() -> dict:
    def control(name: str, modules: list[str], environments: list[str]) -> dict:
        return {"id": name, "granularity": "unit_method", "methods": ["unit", "contract"],
                "environments": environments, "modules": modules, "source": "tests/parser.py:7",
                "retention": {"decision": "keep", "ref": "review.md:4"},
                "demand": {"mode": "on_demand", "condition": "Parser contract changes", "ref": "spec.md:1"},
                "protection": {"behavior": "No write on truncated input", "oracle_ref": "spec.md:1",
                               "discriminator_ref": "review.md:4"}}
    return {"schema": "fvl.test-catalog.v1", "scope": "Synthetic parser controls only", "revision": "synthetic-v1",
            "method_notes": "unit identifies the caller's code-test family, not purity",
            "modules": [{"id": "integrity", "statement": "Preserve data", "basis": "spec.md:1"},
                        {"id": "input", "statement": "Reject invalid input", "basis": "spec.md:2"}],
            "controls": [control("reject", ["input", "integrity"], ["local", "ci"]),
                         control("accept", ["input"], ["local"])],
            "ci_bindings": [{"id": "manual", "event": "workflow_dispatch", "source": "workflow.yml:1",
                             "selection": "explicit", "controls": ["reject"]},
                            {"id": "runtime", "event": "pull_request", "source": "runtime.yml:1",
                             "selection": "dynamic", "controls": [], "condition": "original diff selection"}]}


def save(root: Path, value: dict) -> None:
    (root / "catalog.json").write_text(json.dumps(value))


def test_public_query_keeps_overlap_separate_from_necessity_and_execution(tmp_path: Path, capsys) -> None:
    save(tmp_path, packet())
    assert main(["catalog", str(tmp_path), "--catalog", "catalog.json", "--module", "integrity",
                 "--environment", "ci", "--list"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "CATALOG_ONLY"
    assert result["denominator"]["by_granularity"] == {"unit_method": 2}
    assert result["denominator"]["methods"] == {"contract": 2, "unit": 2}
    assert result["denominator"]["modules"] == {"input": 2, "integrity": 1}
    assert [row["id"] for row in result["controls"]] == ["reject"]
    assert result["filtered"]["by_granularity"] == {"unit_method": 1}
    assert [row["control_count"] for row in result["ci_bindings"]] == [1, None]
    assert result["necessary_for_change"]["count"] is None
    assert result["tests_executed"] == result["ci_dispatched"] == 0
    assert result["retention_decision"] == "NOT_EVALUATED"


def test_union_filters_deduplicate_cross_module_control_and_keep_other_grains_separate(tmp_path: Path) -> None:
    value = packet()
    physical = copy.deepcopy(value["controls"][0])
    physical.update(id="crash-recovery", granularity="physical_family", methods=["integration"])
    value["controls"].append(physical)
    save(tmp_path, value)
    result = query_catalog(tmp_path, "catalog.json", filters={"modules": ["input", "integrity"]})
    assert result["filtered"]["by_granularity"] == {"unit_method": 2, "physical_family": 1}
    assert result["filtered"]["unique_records"] == 3
    assert query_catalog(tmp_path, "catalog.json", filters={"granularity": ["physical_family"]})["filtered"]["unique_records"] == 1


def test_missing_classification_is_a_named_gap_not_zero_necessity_or_permission_to_delete(tmp_path: Path) -> None:
    value = packet()
    value["controls"][0].update(modules=[], protection={})
    value["controls"][0]["demand"]["condition"] = ""
    save(tmp_path, value)
    result = query_catalog(tmp_path, "catalog.json")
    assert result["classification_gaps"] == [{"id": "reject", "missing": ["modules", "demand.condition",
        "protection.behavior", "protection.oracle_ref", "protection.discriminator_ref"]}]
    assert result["denominator"]["unique_records"] == 2
    assert result["oracle_review"] == "SESSION_REQUIRED"


@pytest.mark.parametrize("fault", ["duplicate", "ci_as_method", "dangling_module", "dangling_ci",
                                  "dynamic_members", "bad_type", "bad_retention", "unknown_filter"])
def test_invalid_or_ambiguous_classification_is_diagnostic(tmp_path: Path, capsys, fault: str) -> None:
    value = packet()
    if fault == "duplicate":
        value["controls"].append(value["controls"][0])
    elif fault == "ci_as_method":
        value["controls"][0]["methods"] = ["ci"]
    elif fault == "dangling_module":
        value["controls"][0]["modules"] = ["unknown"]
    elif fault == "dangling_ci":
        value["ci_bindings"][0]["controls"] = ["unknown"]
    elif fault == "dynamic_members":
        value["ci_bindings"][1]["controls"] = ["reject"]
    elif fault == "bad_type":
        value["controls"][0]["granularity"] = []
    elif fault == "bad_retention":
        value["controls"][0]["retention"]["decision"] = {}
    save(tmp_path, value)
    args = ["catalog", str(tmp_path), "--catalog", "catalog.json"]
    if fault == "unknown_filter":
        args += ["--module", "typo"]
    assert main(args) == 3
    assert json.loads(capsys.readouterr().out)["status"] == "UNKNOWN"


@pytest.mark.parametrize("path", ["../catalog.json", "linked.json"])
def test_catalog_reuses_original_selected_path_boundary(tmp_path: Path, capsys, path: str) -> None:
    save(tmp_path, packet())
    (tmp_path / "linked.json").symlink_to(tmp_path / "catalog.json")
    assert main(["catalog", str(tmp_path), "--catalog", path]) == 3
    assert json.loads(capsys.readouterr().out)["status"] == "UNKNOWN"


@pytest.mark.parametrize("fault", ["duplicate", "drift"])
def test_catalog_parts_keep_digest_and_unique_population(tmp_path: Path, capsys, fault: str) -> None:
    import hashlib
    value = packet()
    raw = json.dumps({"controls": value["controls"]}).encode()
    (tmp_path / "part.json").write_bytes(raw)
    value["controls"] = []
    value["control_parts"] = [{"path": "part.json", "sha256": hashlib.sha256(raw).hexdigest()}]
    if fault == "duplicate":
        value["control_parts"] *= 2
    else:
        (tmp_path / "part.json").write_text("{}")
    save(tmp_path, value)
    assert main(["catalog", str(tmp_path), "--catalog", "catalog.json"]) == 3
    assert json.loads(capsys.readouterr().out)["status"] == "UNKNOWN"
