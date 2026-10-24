"""Optional Hypothesis checks. These are sampling, not mathematical proofs."""
import pytest
pytest.importorskip("hypothesis")
from hypothesis import given, strategies as st
from formal_verification_lab.contracts import eligible_effect, receipt_supported

@given(st.booleans(), st.booleans(), st.booleans(), st.booleans(), st.booleans())
def test_gate_never_accepts_missing_predicate(auth, fresh, legal, bound, dup):
    assert not eligible_effect(auth, fresh, legal, bound, dup) or (auth and fresh and legal and bound and not dup)

@given(st.integers(min_value=-10, max_value=10), st.booleans(), st.booleans())
def test_receipt_cannot_pass_without_single_observed_effect(count, confirmed, auth):
    assert not receipt_supported(count, confirmed, auth) or (count == 1 and confirmed and auth)
