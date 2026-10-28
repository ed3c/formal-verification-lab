from __future__ import annotations
import json
from pathlib import Path
import pytest
from formal_verification_lab.bundles import load_bundle, BundleError
from formal_verification_lab.kernel import evaluate
from formal_verification_lab.cli import main

FIXTURES = Path(__file__).parents[1] / "fixtures" / "cases"

@pytest.mark.parametrize("folder", sorted(p for p in FIXTURES.iterdir() if p.is_dir()), ids=lambda x: x.name)
def test_planted_control(folder: Path) -> None:
    expected = json.loads((folder / "expected.json").read_text())["verdict"]
    result = evaluate(load_bundle(folder))
    assert result["verdict"] == expected
    assert result["authorizes_landing"] is False
    assert result["production_acceptance"] == "NOT_RUN"
    assert result["claim_level"] == "SYNTHETIC_CONFORMANCE"

def test_manifest_digest_detects_changed_bytes(tmp_path: Path) -> None:
    import shutil
    shutil.copytree(FIXTURES / "publish_valid", tmp_path / "case")
    with (tmp_path / "case" / "operation.json").open("a") as f:
        f.write(" ")
    with pytest.raises(BundleError, match="hash mismatch"):
        load_bundle(tmp_path / "case")

def test_manifest_rejects_parent_path(tmp_path: Path) -> None:
    import shutil
    shutil.copytree(FIXTURES / "publish_valid", tmp_path / "case")
    manifest = json.loads((tmp_path / "case" / "manifest.json").read_text())
    manifest["files"]["operation"]["path"] = "../secrets.json"
    (tmp_path / "case" / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(BundleError, match="canonical"):
        load_bundle(tmp_path / "case")

def test_symlink_file_refused(tmp_path: Path) -> None:
    import shutil
    shutil.copytree(FIXTURES / "publish_valid", tmp_path / "case")
    source = tmp_path / "case" / "authority.json"
    other = tmp_path / "outside.json"
    other.write_bytes(source.read_bytes())
    source.unlink()
    source.symlink_to(other)
    with pytest.raises(BundleError, match="symlink"):
        load_bundle(tmp_path / "case")

def test_cli_controls(capsys) -> None:
    assert main(["controls", str(FIXTURES)]) == 0
    assert '"native_evals": "NOT_RUN"' in capsys.readouterr().out

def test_cli_fail_on_counterexample(capsys) -> None:
    assert main(["evaluate", str(FIXTURES / "duplicate_publish"), "--fail-on-counterexample"]) == 2
    assert '"verdict": "COUNTEREXAMPLE"' in capsys.readouterr().out

def test_missing_bundle_returns_unknown(capsys) -> None:
    assert main(["evaluate", "/does/not/exist"]) == 3
    assert '"status": "UNKNOWN"' in capsys.readouterr().out
