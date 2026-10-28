from formal_verification_lab.model_explore import State, successors, violation, explore, check_unsafe_canary


def test_initial_has_no_effect_or_authority():
    s = State()
    assert violation(s) is None
    assert all(n != "publish" for n, _ in successors(s))


def test_bounded_protocol_has_terminal_non_vacuity_witness():
    result = explore(12)
    assert result["status"] == "BOUNDED_PASS"
    assert result["terminal_witness"] == [
        "authorize", "bindEvidence", "advance", "publish", "observeEffect", "terminal"
    ]
    assert result["visited_states"] > 1
    assert result["quint_apalache"] == "NOT_RUN"


def test_reconciliation_path_is_observed_without_claiming_retry_progress():
    result = explore(12)
    assert result["reconciliation_witness"] == [
        "authorize", "bindEvidence", "advance", "markUnknown", "reconcileNoEffect", "retry"
    ]
    assert result["liveness_claim"] == "NOT_ESTABLISHED"


def test_short_bound_does_not_claim_non_vacuity():
    result = explore(2)
    assert result["terminal_witness"] is None
    assert result["bound_reached"] is True


def test_canary_is_explicit_counterexample_not_quint_claim():
    c = check_unsafe_canary()
    assert c["status"] == "COUNTEREXAMPLE"
    assert c["quint_apalache"] == "NOT_RUN"
    assert c["trace"][-1] == "publishUnchecked"


def test_injected_unsafe_effect_is_detected():
    assert violation(State(effect_count=1, effect_authorized=False)) == "effectHasPreconditions"


def test_reconciling_has_no_source_supported_phase_changing_continuation():
    from dataclasses import replace
    state = replace(State(), phase="RECONCILING", authorized=True, bound=True, fresh=True)
    assert all(name != "resumeReconciled" for name, _ in successors(state))
    assert all(target.phase == "RECONCILING" for _, target in successors(state))


def test_retry_unknown_without_reconciliation_is_blocked():
    from dataclasses import replace
    s = replace(State(), phase="UNKNOWN", authorized=True, bound=True, fresh=True)
    assert all(name != "retry" for name, _ in successors(s))
