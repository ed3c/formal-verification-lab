from __future__ import annotations

from pathlib import Path
import sys

import pytest


sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import parity


def _ast(action_names: tuple[str, ...]) -> dict[str, object]:
    deterministic = {
        "kind": "app",
        "opcode": "assign",
        "args": [{"kind": "name", "name": "s"}, {"kind": "name", "name": "s"}],
    }
    declarations = [
        {"kind": "def", "qualifier": "action", "name": "init", "expr": deterministic},
        *[
            {"kind": "def", "qualifier": "action", "name": name, "expr": deterministic}
            for name in action_names
        ],
        {
            "kind": "def",
            "qualifier": "action",
            "name": "step",
            "expr": {
                "kind": "app",
                "opcode": "actionAny",
                "args": [{"kind": "name", "name": name} for name in action_names],
            },
        },
    ]
    return {
        "stage": "parsing",
        "errors": [],
        "modules": [{"name": "OperationProtocol", "declarations": declarations}],
    }


def test_reachable_graph_saturates_and_retains_self_loops() -> None:
    graph = parity.enumerate_reachable_graph()

    assert len(graph.states) == 14
    assert len(graph.edges) == 31
    assert any(source == target for source, _, target in graph.edges)


def test_reachable_graph_cap_fails_instead_of_reporting_an_incomplete_graph() -> None:
    with pytest.raises(parity.ParityError, match="graph is incomplete"):
        parity.enumerate_reachable_graph(state_cap=1)


def test_action_registry_requires_named_step_members() -> None:
    ast = _ast(("authorize",))
    step = ast["modules"][0]["declarations"][-1]
    step["expr"]["args"] = [{"kind": "app", "opcode": "actionAll", "args": []}]

    with pytest.raises(parity.ParityError, match="non-name"):
        parity.parse_action_registry(ast)


def test_action_registry_rejects_unlisted_action_declarations() -> None:
    ast = _ast(("authorize",))
    ast["modules"][0]["declarations"].insert(
        -1,
        {
            "kind": "def",
            "qualifier": "action",
            "name": "hiddenAction",
            "expr": {"kind": "app", "opcode": "assign", "args": []},
        },
    )

    with pytest.raises(parity.ParityError, match="action declarations differ"):
        parity.parse_action_registry(ast)


def test_action_registry_rejects_unknown_definition_qualifier() -> None:
    ast = _ast(("authorize",))
    ast["modules"][0]["declarations"].insert(
        -1,
        {"kind": "def", "qualifier": "mystery", "name": "unknown", "expr": {"kind": "bool"}},
    )

    with pytest.raises(parity.ParityError, match="unsupported Quint definition qualifier"):
        parity.parse_action_registry(ast)


def test_action_registry_rejects_nondeterministic_action_body() -> None:
    ast = _ast(("authorize",))
    action = ast["modules"][0]["declarations"][1]
    action["expr"] = {"kind": "app", "opcode": "actionAny", "args": []}

    with pytest.raises(parity.ParityError, match="unsupported opcode 'actionAny'"):
        parity.parse_action_registry(ast)


def test_action_registry_rejects_action_aliases_that_hide_their_syntax() -> None:
    ast = _ast(("authorize",))
    action = ast["modules"][0]["declarations"][1]
    action["expr"] = {"kind": "name", "name": "hiddenAction"}

    with pytest.raises(parity.ParityError, match="unsupported name reference 'hiddenAction'"):
        parity.parse_action_registry(ast)


def test_registry_comparison_applies_only_the_named_fail_alias() -> None:
    graph = parity.enumerate_reachable_graph()
    actions = tuple(
        dict.fromkeys(parity.PYTHON_TO_QUINT.get(action, action) for _, action, _ in graph.edges)
    )
    parity.validate_registry_against_graph(actions, graph)

    with pytest.raises(parity.ParityError, match=r"quint_only=\['invented'\]"):
        parity.validate_registry_against_graph((*actions, "invented"), graph)


def test_harness_checks_initial_state_and_every_state_action_pair() -> None:
    graph = parity.enumerate_reachable_graph()
    actions = tuple(
        dict.fromkeys(parity.PYTHON_TO_QUINT.get(action, action) for _, action, _ in graph.edges)
    )

    harness, names = parity.build_positive_harness(graph, actions, "../specs/operation")

    assert len(names) == 1 + len(graph.states) * len(actions)
    assert harness.count("  run ") == len(names)
    assert "run exactInitialStateTest = init.expect" in harness
    assert ".then(publish).expect" in harness
    assert ".then(publish.fail())" in harness
    assert "effectCount:" in harness
    assert "effect_count:" not in harness


def test_transition_matrix_rejects_multiple_targets_for_one_named_action() -> None:
    graph = parity.enumerate_reachable_graph()
    duplicated = parity.ReachableGraph(graph.states, (*graph.edges, graph.edges[0]))
    action = parity.PYTHON_TO_QUINT.get(graph.edges[0][1], graph.edges[0][1])

    with pytest.raises(parity.ParityError, match="nondeterministic actions are unsupported"):
        parity.transition_matrix(duplicated, (action,))


def test_quint_result_validation_requires_exact_positive_count() -> None:
    positive = {"stage": "testing", "errors": [], "passed": ["aTest"], "failed": [], "ignored": []}
    parity.validate_positive_result(
        {"exit_code": 0, "timed_out": False, "process_error": None}, positive, ("aTest",)
    )
    with pytest.raises(parity.ParityError, match="count or names mismatch"):
        parity.validate_positive_result(
            {"exit_code": 0, "timed_out": False, "process_error": None}, positive, ("aTest", "bTest")
        )



def test_negative_control_requires_the_false_expect_diagnostic() -> None:
    name = "deliberatePublishMismatchTest"
    output = "\n".join(
        [
            f"1) {name} failed after 1 test(s)",
            f"1) {name}:",
            "Error [QNT508]: Expect condition does not hold true",
        ]
    )
    parity.validate_negative_result(
        {"exit_code": 1, "timed_out": False, "process_error": None},
        output,
        "",
        name,
    )
    with pytest.raises(parity.ParityError, match="did not fail"):
        parity.validate_negative_result(
            {"exit_code": 0, "timed_out": False, "process_error": None},
            output,
            "",
            name,
        )


def test_runtime_or_action_failure_cannot_satisfy_the_negative_control() -> None:
    name = "deliberatePublishMismatchTest"
    runtime_failure = "\n".join(
        [
            f"1) {name} failed after 1 test(s)",
            f"1) {name}:",
            "Error [QNT500]: action evaluated to false",
        ]
    )

    with pytest.raises(parity.ParityError, match="false-expect diagnostic"):
        parity.validate_negative_result(
            {"exit_code": 1, "timed_out": False, "process_error": None},
            runtime_failure,
            "",
            name,
        )


def test_timed_out_tool_writes_partial_output_and_a_nonpassing_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def time_out(*args: object, **kwargs: object) -> None:
        raise parity.subprocess.TimeoutExpired(
            cmd=["quint"], timeout=180, output=b"partial output", stderr=b"partial error"
        )

    monkeypatch.setattr(parity.subprocess, "run", time_out)

    receipt = parity.run_command("timeout", ["quint"], tmp_path, tmp_path)

    assert receipt["exit_code"] is None
    assert receipt["timed_out"] is True
    assert (tmp_path / "runs/timeout/stdout.txt").read_text() == "partial output"
    assert (tmp_path / "runs/timeout/stderr.txt").read_text() == "partial error"


def test_generated_harnesses_are_deterministic() -> None:
    graph = parity.enumerate_reachable_graph()
    actions = tuple(
        dict.fromkeys(parity.PYTHON_TO_QUINT.get(action, action) for _, action, _ in graph.edges)
    )

    assert parity.build_positive_harness(graph, actions, "operation") == parity.build_positive_harness(
        graph, actions, "operation"
    )
    assert parity.build_negative_harness(graph, "operation") == parity.build_negative_harness(
        graph, "operation"
    )
