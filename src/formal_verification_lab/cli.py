"""Read-only local evidence CLI; never connects to production or launches agents."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .bundles import BundleError, discover, load_bundle, load_selection
from .kernel import PROPERTIES, evaluate
from .retention import evaluate_retention
from .catalog import query_catalog
from .mapping import measure_mapping


def _selection(value: str) -> tuple[str, str]:
    role, separator, path = value.partition("=")
    if not separator or not path:
        raise ValueError("Selected evidence must be ROLE=relative/path.json")
    return role, path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fvl", description="Read-only Agent Harness formal verification lab")
    sub = parser.add_subparsers(dest="command", required=True)
    evaluation = sub.add_parser("evaluate", help="Evaluate a frozen bundle or explicitly selected local evidence")
    evaluation.add_argument("bundle", help="Bundle directory or evidence selection root")
    evaluation.add_argument("--select", action="append", metavar="ROLE=PATH", help="Select one local JSON part; may be repeated")
    evaluation.add_argument("--property", action="append", choices=PROPERTIES, dest="properties")
    evaluation.add_argument("--fail-on-counterexample", action="store_true")
    discovery = sub.add_parser("discover", help="Find bounded local evidence candidates without evaluating them")
    discovery.add_argument("directory")
    discovery.add_argument("--pattern", default="*.json")
    discovery.add_argument("--max-depth", type=int, default=4)
    discovery.add_argument("--max-files", type=int, default=200)
    discovery.add_argument("--max-entries", type=int, default=10_000)
    controls = sub.add_parser("controls", help="Check named synthetic controls")
    controls.add_argument("directory")
    retention = sub.add_parser("retention", help="Check selected finite replacement coverage; never decide test value or run tests")
    retention.add_argument("directory")
    retention.add_argument("--study", required=True, help="Relative JSON study path inside the selected evidence root")
    retention.add_argument("--fail-on-counterexample", action="store_true")
    catalog = sub.add_parser("catalog", help="Describe supplied test classifications; never select or execute tests")
    catalog.add_argument("directory")
    catalog.add_argument("--catalog", required=True, help="Relative catalog JSON path inside the selected root")
    for dimension in ("module", "method", "environment", "granularity"):
        catalog.add_argument("--" + dimension, action="append")
    catalog.add_argument("--list", action="store_true", dest="list_controls")
    mapping = sub.add_parser("mapping", help="Measure a supplied finite source-location relation; never infer test value")
    mapping.add_argument("directory")
    mapping.add_argument("--study", required=True)
    args = parser.parse_args(argv)
    if args.command in ("evaluate", "discover", "retention", "catalog", "mapping"):
        try:
            if args.command == "mapping":
                result = measure_mapping(args.directory, args.study)
            elif args.command == "catalog":
                filters = {field: getattr(args, option) or [] for field, option in (
                    ("modules", "module"), ("methods", "method"), ("environments", "environment"),
                    ("granularity", "granularity"))}
                result = query_catalog(args.directory, args.catalog, filters=filters, include_controls=args.list_controls)
            elif args.command == "discover":
                result = discover(args.directory, args.pattern, args.max_depth, args.max_files, args.max_entries)
            elif args.command == "retention":
                result = evaluate_retention(args.directory, args.study)
            else:
                record = (load_selection(args.bundle, (_selection(value) for value in args.select))
                          if args.select else load_bundle(args.bundle))
                result = evaluate(record, properties=args.properties)
        except (BundleError, ValueError, OSError, json.JSONDecodeError) as exc:
            print(json.dumps({"status": "UNKNOWN", "error": str(exc), "authorizes_landing": False}))
            return 3
        print(json.dumps(result, sort_keys=True, indent=2))
        if args.command in ("evaluate", "retention") and args.fail_on_counterexample and result["verdict"] == "COUNTEREXAMPLE":
            return 2
        return 0
    reports = []
    for folder in sorted(Path(args.directory).iterdir()):
        if not folder.is_dir():
            continue
        try:
            expected = json.loads((folder / "expected.json").read_text())["verdict"]
            record = load_bundle(folder)
            if record["provenance"] != "synthetic":
                raise BundleError("Controls require explicitly synthetic fixtures")
            actual = evaluate(record)["verdict"]
            reports.append({"case": folder.name, "expected": expected, "actual": actual, "matches": expected == actual})
        except (BundleError, ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
            reports.append({"case": folder.name, "matches": False, "error": str(exc)})
    ok = bool(reports) and all(report["matches"] for report in reports)
    print(json.dumps({"kind": "SYNTHETIC_CONTROLS_ONLY", "baseline_treatment": "NOT_RUN",
                      "native_evals": "NOT_RUN", "status": "PASS" if ok else "FAIL", "cases": reports}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
