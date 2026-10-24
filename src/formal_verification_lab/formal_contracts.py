"""Optional actual icontract obligations (CrossHair targets this module).

Requires `pip install .[verify]`. Do not import provider adapters here.
"""
import icontract
from .contracts import eligible_effect, receipt_supported


@icontract.ensure(
    lambda authorized, fresh, legal, identity_bound, observed_duplicate, result:
    not result or (authorized and fresh and legal and identity_bound and not observed_duplicate)
)
def verified_effect_necessary(
    authorized: bool,
    fresh: bool,
    legal: bool,
    identity_bound: bool,
    observed_duplicate: bool,
) -> bool:
    return eligible_effect(authorized, fresh, legal, identity_bound, observed_duplicate)


@icontract.ensure(
    lambda effect_count, provider_confirmed, authorization_confirmed, result:
    not result or (effect_count == 1 and provider_confirmed and authorization_confirmed)
)
def verified_receipt_necessary(
    effect_count: int,
    provider_confirmed: bool,
    authorization_confirmed: bool,
) -> bool:
    return receipt_supported(effect_count, provider_confirmed, authorization_confirmed)
