import icontract


@icontract.ensure(lambda authorized, result: not result or authorized)
def unchecked_effect(authorized: bool) -> bool:
    return True
