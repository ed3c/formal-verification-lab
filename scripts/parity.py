from __future__ import annotations

import argparse
from collections import deque
from dataclasses import asdict, dataclass, fields
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Callable, Iterable


ROOT = Path(__file__).resolve().parents[1]
MODEL_SOURCE = ROOT / "src/formal_verification_lab/model_explore.py"
SPEC = ROOT / "specs/operation.qnt"
GENERATOR = Path(__file__).resolve()
QUINT_VERSION = "0.32.0"
STATE_CAP = 1_000
PYTHON_TO_QUINT = {"fail": "markFailed"}
NEGATIVE_ERROR_CODE = "QNT508"
NEGATIVE_ERROR_MESSAGE = "Expect condition does not hold true"
STATE_FIELDS = {
    "phase": "phase",
    "authorized": "authorized",
    "bound": "bound",
    "fresh": "fresh",
    "reconciled": "reconciled",
    "effect_count": "effectCount",
    "effect_authorized": "effectAuthorized",
    "receipt_observed": "receiptObserved",
    "reported_success": "reportedSuccess",
}
DETERMINISTIC_NODE_KINDS = {"app", "bool", "int", "name", "str"}
DETERMINISTIC_OPCODES = {
    "Rec",
    "actionAll",
    "and",
    "assign",
    "eq",
    "field",
    "ite",
    "or",
    "with",
}

sys.path.insert(0, str(ROOT / "src"))
from formal_verification_lab.model_explore import State, successors


class ParityError(ValueError):
    pass


@dataclass(frozen=True)
class ReachableGraph:
    states: tuple[State, ...]
    edges: tuple[tuple[int, str, int], ...]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def enumerate_reachable_graph(
    successor_fn: Callable[[State], Iterable[tuple[str, State]]] = successors,
    state_cap: int = STATE_CAP,
) -> ReachableGraph:
    if state_cap < 1:
        raise ParityError("state cap must be positive")
    initial = State()
    states = [initial]
    indexes = {initial: 0}
    queue = deque([initial])
    edges: list[tuple[int, str, int]] = []
    while queue:
        source = queue.popleft()
        source_index = indexes[source]
        for action, target in successor_fn(source):
            if target not in indexes:
                if len(states) >= state_cap:
                    raise ParityError(
                        f"reachable graph exceeded state cap {state_cap}; graph is incomplete"
                    )
                indexes[target] = len(states)
                states.append(target)
                queue.append(target)
            edges.append((source_index, action, indexes[target]))
    return ReachableGraph(tuple(states), tuple(edges))


def _module(ast: dict[str, Any], name: str) -> dict[str, Any]:
    if ast.get("stage") != "parsing":
        raise ParityError(f"unexpected Quint AST stage: {ast.get('stage')!r}")
    if ast.get("errors") != []:
        raise ParityError("Quint parser returned errors")
    modules = ast.get("modules")
    if not isinstance(modules, list):
        raise ParityError("Quint AST modules must be a list")
    matches = [module for module in modules if isinstance(module, dict) and module.get("name") == name]
    if len(matches) != 1:
        raise ParityError(f"expected one Quint module named {name}, found {len(matches)}")
    return matches[0]


def _walk_expression(value: object) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_expression(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_expression(child)


def _validate_deterministic_action(name: str, expr: object) -> None:
    if not isinstance(expr, dict):
        raise ParityError(f"action {name} has no expression object")
    for node in _walk_expression(expr):
        kind = node.get("kind")
        if kind not in DETERMINISTIC_NODE_KINDS:
            raise ParityError(f"action {name} uses unsupported AST node kind {kind!r}")
        if kind == "name" and node.get("name") != "s":
            raise ParityError(f"action {name} uses unsupported name reference {node.get('name')!r}")
        if kind == "app":
            opcode = node.get("opcode")
            if opcode not in DETERMINISTIC_OPCODES:
                raise ParityError(f"action {name} uses unsupported opcode {opcode!r}")


def parse_action_registry(ast: dict[str, Any], module_name: str = "OperationProtocol") -> tuple[str, ...]:
    module = _module(ast, module_name)
    declarations = module.get("declarations")
    if not isinstance(declarations, list):
        raise ParityError("Quint module declarations must be a list")
    allowed_declaration_kinds = {"def", "typedef", "var"}
    for declaration in declarations:
        if not isinstance(declaration, dict) or declaration.get("kind") not in allowed_declaration_kinds:
            kind = declaration.get("kind") if isinstance(declaration, dict) else type(declaration).__name__
            raise ParityError(f"unsupported Quint declaration kind {kind!r}")
        if declaration.get("kind") == "def" and declaration.get("qualifier") not in {"action", "val"}:
            raise ParityError(
                f"unsupported Quint definition qualifier {declaration.get('qualifier')!r}"
            )
    action_declarations = [
        declaration
        for declaration in declarations
        if declaration.get("kind") == "def" and declaration.get("qualifier") == "action"
    ]
    names = [declaration.get("name") for declaration in action_declarations]
    if any(not isinstance(name, str) for name in names) or len(set(names)) != len(names):
        raise ParityError("Quint action declarations must have unique string names")
    steps = [declaration for declaration in action_declarations if declaration["name"] == "step"]
    if len(steps) != 1:
        raise ParityError(f"expected one step action, found {len(steps)}")
    step_expr = steps[0].get("expr")
    if not isinstance(step_expr, dict) or step_expr.get("kind") != "app" or step_expr.get("opcode") != "actionAny":
        raise ParityError("step must be an actionAny union of named actions")
    args = step_expr.get("args")
    if not isinstance(args, list) or not args:
        raise ParityError("step action registry must not be empty")
    registry: list[str] = []
    for arg in args:
        if not isinstance(arg, dict) or arg.get("kind") != "name" or not isinstance(arg.get("name"), str):
            raise ParityError("step contains a non-name action branch")
        registry.append(arg["name"])
    if len(set(registry)) != len(registry):
        raise ParityError("step action registry contains duplicates")
    declared = set(names)
    expected_declared = set(registry) | {"init", "step"}
    if declared != expected_declared:
        raise ParityError(
            f"action declarations differ from init plus step registry: "
            f"extra={sorted(declared - expected_declared)}, missing={sorted(expected_declared - declared)}"
        )
    by_name = {declaration["name"]: declaration for declaration in action_declarations}
    for name in ("init", *registry):
        _validate_deterministic_action(name, by_name[name].get("expr"))
    return tuple(registry)


def validate_registry_against_graph(registry: tuple[str, ...], graph: ReachableGraph) -> None:
    python_actions = {PYTHON_TO_QUINT.get(action, action) for _, action, _ in graph.edges}
    quint_actions = set(registry)
    if python_actions != quint_actions:
        raise ParityError(
            "Python and Quint action registries differ: "
            f"python_only={sorted(python_actions - quint_actions)}, "
            f"quint_only={sorted(quint_actions - python_actions)}"
        )


def _quint_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value)
    raise ParityError(f"unsupported state value {value!r}")


def quint_record(state: State) -> str:
    values = asdict(state)
    body = ", ".join(
        f"{STATE_FIELDS[field.name]}: {_quint_value(values[field.name])}" for field in fields(State)
    )
    return "{" + body + "}"


def _test_name(state_index: int, action: str, enabled: bool) -> str:
    suffix = "EnabledTest" if enabled else "DisabledTest"
    return f"state{state_index:03d}{action[0].upper()}{action[1:]}{suffix}"


def transition_matrix(
    graph: ReachableGraph, registry: tuple[str, ...]
) -> tuple[tuple[int, str, int | None], ...]:
    targets: dict[tuple[int, str], list[int]] = {}
    for source, python_action, target in graph.edges:
        action = PYTHON_TO_QUINT.get(python_action, python_action)
        targets.setdefault((source, action), []).append(target)
    rows: list[tuple[int, str, int | None]] = []
    for state_index in range(len(graph.states)):
        for action in registry:
            matches = targets.get((state_index, action), [])
            if len(matches) > 1:
                raise ParityError(
                    f"Python action {action} has {len(matches)} targets from state {state_index}; "
                    "nondeterministic actions are unsupported"
                )
            rows.append((state_index, action, matches[0] if matches else None))
    return tuple(rows)


def build_positive_harness(
    graph: ReachableGraph, registry: tuple[str, ...], import_path: str
) -> tuple[str, tuple[str, ...]]:
    lines = [
        "module P1Parity {",
        f'  import OperationProtocol.* from {json.dumps(import_path)}',
        "",
    ]
    test_names = ["exactInitialStateTest"]
    lines.append(f"  run exactInitialStateTest = init.expect(s == {quint_record(State())})")
    for state_index, action, target_index in transition_matrix(graph, registry):
        enabled = target_index is not None
        name = _test_name(state_index, action, enabled)
        test_names.append(name)
        source = quint_record(graph.states[state_index])
        if enabled:
            target = quint_record(graph.states[target_index])
            lines.append(f"  run {name} = (s' = {source}).then({action}).expect(s == {target})")
        else:
            lines.append(f"  run {name} = (s' = {source}).then({action}.fail())")
    lines.extend(["}", ""])
    return "\n".join(lines), tuple(test_names)


def build_negative_harness(graph: ReachableGraph, import_path: str) -> tuple[str, str]:
    publish_edge = next(
        (edge for edge in graph.edges if PYTHON_TO_QUINT.get(edge[1], edge[1]) == "publish"),
        None,
    )
    if publish_edge is None:
        raise ParityError("reachable graph has no enabled publish action for the negative control")
    source_index, _, target_index = publish_edge
    wrong = asdict(graph.states[target_index])
    wrong["effect_count"] = 0 if wrong["effect_count"] != 0 else 1
    wrong_state = State(**wrong)
    name = "deliberatePublishMismatchTest"
    content = "\n".join(
        [
            "module P1ParityNegative {",
            f'  import OperationProtocol.* from {json.dumps(import_path)}',
            "",
            f"  run {name} = (s' = {quint_record(graph.states[source_index])})"
            f".then(publish).expect(s == {quint_record(wrong_state)})",
            "}",
            "",
        ]
    )
    return content, name


def graph_record(graph: ReachableGraph) -> dict[str, object]:
    return {
        "schema": "fvl.p1-reachable-graph.v1",
        "saturated": True,
        "state_cap": STATE_CAP,
        "state_count": len(graph.states),
        "edge_count": len(graph.edges),
        "states": [asdict(state) for state in graph.states],
        "edges": [
            {"source": source, "action": action, "target": target}
            for source, action, target in graph.edges
        ],
    }


def _captured_text(value: str | bytes | None) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


def run_command(name: str, argv: list[str], cwd: Path, evidence: Path) -> dict[str, object]:
    run_dir = evidence / "runs" / name
    run_dir.mkdir(parents=True, exist_ok=False)
    command = {
        "argv": argv,
        "cwd": str(cwd),
        "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "timeout_seconds": 180,
    }
    write_json(run_dir / "command.json", command)
    started = time.monotonic()
    try:
        result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, timeout=180, check=False)
        receipt = {
            **command,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "exit_code": result.returncode,
            "timed_out": False,
            "process_error": None,
        }
        (run_dir / "stdout.txt").write_text(result.stdout, encoding="utf-8")
        (run_dir / "stderr.txt").write_text(result.stderr, encoding="utf-8")
    except subprocess.TimeoutExpired as exc:
        receipt = {
            **command,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "exit_code": None,
            "timed_out": True,
            "process_error": f"TimeoutExpired: {exc}",
        }
        (run_dir / "stdout.txt").write_text(_captured_text(exc.stdout), encoding="utf-8")
        (run_dir / "stderr.txt").write_text(_captured_text(exc.stderr), encoding="utf-8")
    except OSError as exc:
        receipt = {
            **command,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "exit_code": None,
            "timed_out": False,
            "process_error": f"{exc.__class__.__name__}: {exc}",
        }
        (run_dir / "stdout.txt").write_text("", encoding="utf-8")
        (run_dir / "stderr.txt").write_text(str(exc), encoding="utf-8")
    write_json(run_dir / "result.json", receipt)
    return receipt


def _read_result(path: Path) -> dict[str, Any]:
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ParityError(f"cannot read Quint result {path}: {exc}") from exc
    if not isinstance(result, dict):
        raise ParityError(f"Quint result {path} is not an object")
    return result


def validate_positive_result(
    receipt: dict[str, object], result: dict[str, Any], expected_names: tuple[str, ...]
) -> None:
    if receipt.get("exit_code") != 0 or receipt.get("timed_out") or receipt.get("process_error"):
        raise ParityError(f"positive Quint test command failed with exit {receipt.get('exit_code')}")
    if result.get("stage") != "testing" or result.get("errors") != []:
        raise ParityError("positive Quint result did not reach a clean testing stage")
    if result.get("failed") != [] or result.get("ignored") != []:
        raise ParityError("positive Quint result contains failed or ignored tests")
    passed = result.get("passed")
    if not isinstance(passed, list) or tuple(passed) != expected_names:
        actual_count = len(passed) if isinstance(passed, list) else "invalid"
        raise ParityError(
            f"positive Quint test count or names mismatch: expected {len(expected_names)}, got {actual_count}"
        )


def validate_negative_result(
    receipt: dict[str, object], stdout: str, stderr: str, expected_name: str
) -> None:
    if receipt.get("exit_code") != 1 or receipt.get("timed_out") or receipt.get("process_error"):
        raise ParityError("negative Quint control did not fail through a completed tool invocation")
    diagnostic = f"Error [{NEGATIVE_ERROR_CODE}]: {NEGATIVE_ERROR_MESSAGE}"
    output = f"{stdout}\n{stderr}"
    required = (
        f"{expected_name} failed after 1 test(s)",
        f"1) {expected_name}:",
        diagnostic,
    )
    if any(fragment not in output for fragment in required):
        raise ParityError(
            "negative Quint control did not produce the expected false-expect diagnostic"
        )


def _input_paths(toolchain: Path) -> dict[str, Path]:
    return {
        "python_model": MODEL_SOURCE,
        "quint_spec": SPEC,
        "parity_generator": GENERATOR,
        "quint_package": toolchain / "node_modules/@informalsystems/quint/package.json",
    }


def input_digests(paths: dict[str, Path]) -> dict[str, str]:
    return {role: digest(path) for role, path in paths.items()}


def finalize_input_manifest(evidence: Path, inputs: dict[str, Path]) -> bool:
    manifest_path = evidence / "input-manifest.json"
    manifest = _read_result(manifest_path)
    before = manifest.get("before")
    after = input_digests(inputs)
    unchanged = before == after
    write_json(
        manifest_path,
        {
            "schema": "fvl.p1-input-manifest.v1",
            "before": before,
            "after": after,
            "unchanged": unchanged,
        },
    )
    return unchanged


def _relative_quint_import(harness: Path) -> str:
    without_suffix = SPEC.with_suffix("")
    return Path(os.path.relpath(without_suffix, harness.parent)).as_posix()


def execute(toolchain: Path, evidence: Path) -> dict[str, object]:
    inputs = _input_paths(toolchain)
    before = input_digests(inputs)
    write_json(
        evidence / "input-manifest.json",
        {"schema": "fvl.p1-input-manifest.v1", "before": before},
    )
    package_path = toolchain / "node_modules/@informalsystems/quint/package.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    if not isinstance(package, dict):
        raise ParityError("Quint package metadata must be an object")
    if package.get("version") != QUINT_VERSION:
        raise ParityError(f"expected Quint {QUINT_VERSION}, found {package.get('version')!r}")
    quint = toolchain / "node_modules/.bin/quint"
    if not quint.is_file():
        raise ParityError(f"Quint executable is missing: {quint}")

    graph = enumerate_reachable_graph()
    write_json(evidence / "reachable-graph.json", graph_record(graph))

    ast_path = evidence / "parsed-operation-ast.json"
    parse_receipt = run_command(
        "parse",
        [str(quint), "parse", str(SPEC), "--out", str(ast_path)],
        evidence,
        evidence,
    )
    if parse_receipt.get("exit_code") != 0 or parse_receipt.get("timed_out") or parse_receipt.get("process_error"):
        raise ParityError(f"Quint parser failed with exit {parse_receipt.get('exit_code')}")
    ast = _read_result(ast_path)
    registry = parse_action_registry(ast)
    validate_registry_against_graph(registry, graph)
    write_json(
        evidence / "action-registry.json",
        {
            "schema": "fvl.p1-action-registry.v1",
            "module": "OperationProtocol",
            "step_opcode": "actionAny",
            "actions": list(registry),
            "python_aliases": PYTHON_TO_QUINT,
        },
    )

    positive_path = evidence / "generated-parity.qnt"
    import_path = _relative_quint_import(positive_path)
    positive, test_names = build_positive_harness(graph, registry, import_path)
    positive_path.write_text(positive, encoding="utf-8")
    positive_result_path = evidence / "positive-quint-result.json"
    flags = ["--backend=typescript", "--max-samples=1", "--seed=20261024"]
    positive_receipt = run_command(
        "positive",
        [
            str(quint),
            "test",
            str(positive_path),
            "--main=P1Parity",
            *flags,
            f"--out={positive_result_path}",
        ],
        evidence,
        evidence,
    )
    validate_positive_result(positive_receipt, _read_result(positive_result_path), test_names)

    negative_path = evidence / "generated-negative-control.qnt"
    negative, negative_name = build_negative_harness(graph, _relative_quint_import(negative_path))
    negative_path.write_text(negative, encoding="utf-8")
    negative_receipt = run_command(
        "negative",
        [
            str(quint),
            "test",
            str(negative_path),
            "--main=P1ParityNegative",
            *flags,
        ],
        evidence,
        evidence,
    )
    negative_run = evidence / "runs/negative"
    negative_stdout = (negative_run / "stdout.txt").read_text(encoding="utf-8")
    negative_stderr = (negative_run / "stderr.txt").read_text(encoding="utf-8")
    validate_negative_result(negative_receipt, negative_stdout, negative_stderr, negative_name)
    write_json(
        evidence / "negative-diagnostic.json",
        {
            "schema": "fvl.p1-negative-diagnostic.v1",
            "test": negative_name,
            "exit_code": negative_receipt["exit_code"],
            "error_code": NEGATIVE_ERROR_CODE,
            "message": NEGATIVE_ERROR_MESSAGE,
            "raw_output": ["runs/negative/stdout.txt", "runs/negative/stderr.txt"],
        },
    )

    if not finalize_input_manifest(evidence, inputs):
        raise ParityError("input drift detected across parity invocation")
    return {
        "schema": "fvl.p1-parity-result.v1",
        "status": "BOUNDED_PASS",
        "claim": "FINITE_REACHABLE_NAMED_ACTION_PARITY",
        "quint_version": QUINT_VERSION,
        "backend": "typescript",
        "seed": "20261024",
        "max_samples": 1,
        "state_cap": STATE_CAP,
        "graph_saturated": True,
        "reachable_states": len(graph.states),
        "python_edges": len(graph.edges),
        "actions": list(registry),
        "action_checks": len(graph.states) * len(registry),
        "initial_state_checks": 1,
        "passed_tests": len(test_names),
        "negative_control": "COUNTEREXAMPLE",
        "negative_diagnostic": f"{NEGATIVE_ERROR_CODE}_{NEGATIVE_ERROR_MESSAGE}",
        "input_digests_unchanged": True,
        "all_state_equivalence": "NOT_ESTABLISHED",
        "liveness": "NOT_ESTABLISHED",
        "native_refinement": "NOT_RUN",
        "production_acceptance": "NOT_CLAIMED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--toolchain", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    toolchain = args.toolchain.resolve()
    evidence = args.evidence_dir.resolve()
    if evidence == ROOT or ROOT in evidence.parents:
        raise SystemExit("evidence directory must be outside the repository")
    if evidence.exists():
        raise SystemExit(f"evidence directory already exists: {evidence}")
    evidence.mkdir(parents=True)
    try:
        result = execute(toolchain, evidence)
    except (OSError, KeyError, json.JSONDecodeError, ParityError) as exc:
        error = f"{exc.__class__.__name__}: {exc}"
        manifest_path = evidence / "input-manifest.json"
        if manifest_path.is_file():
            try:
                if not finalize_input_manifest(evidence, _input_paths(toolchain)):
                    error = f"ParityError: input drift detected across parity invocation; prior error: {error}"
            except (OSError, json.JSONDecodeError, ParityError) as manifest_exc:
                error = f"{error}; input digest finalization failed: {manifest_exc}"
        result = {
            "schema": "fvl.p1-parity-result.v1",
            "status": "NOT_VERIFIED",
            "error": error,
        }
        write_json(evidence / "summary.json", result)
        print(json.dumps({**result, "evidence": str(evidence)}, indent=2, sort_keys=True))
        return 1
    write_json(evidence / "summary.json", result)
    print(json.dumps({**result, "evidence": str(evidence)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
