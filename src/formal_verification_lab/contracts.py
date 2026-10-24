"""Pure mathematical predicates for CrossHair and icontract.

No filesystem/network operations are reachable from these functions.
"""
from __future__ import annotations


def eligible_effect(
    authorized: bool,
    fresh: bool,
    legal: bool,
    identity_bound: bool,
    observed_duplicate: bool,
) -> bool:
    """A necessary-condition predicate; NOT an authorization oracle."""
    return (
        authorized and fresh and legal and identity_bound
        and not observed_duplicate
    )


def receipt_supported(
    effect_count: int,
    provider_confirmed: bool,
    authorization_confirmed: bool,
) -> bool:
    """Necessary predicate; provider truth must come from independent readback."""
    return (effect_count == 1 and provider_confirmed and authorization_confirmed)
