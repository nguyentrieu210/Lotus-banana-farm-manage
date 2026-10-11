"""Pure piece-rate rules. Piecework pay never depends on headcount or workdays."""
from decimal import Decimal, ROUND_HALF_UP
from lotus_farm.rules import RuleError, quantity


def piece_amount(accepted_qty, unit_price):
    """Accepted output x approved price; round only the final VND amount."""
    qty = quantity(accepted_qty, "Accepted quantity")
    price = quantity(unit_price, "Unit price", positive=True)
    return int((qty * price).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def accepted_output(reported_qty, accepted_qty, reason=""):
    """Review cannot approve more than the submitted work result."""
    reported = quantity(reported_qty, "Reported quantity")
    accepted = quantity(accepted_qty, "Accepted quantity")
    if accepted > reported:
        raise RuleError("Accepted quantity cannot exceed reported quantity.")
    if accepted < reported and not (reason or "").strip():
        raise RuleError("A reduced accepted quantity requires a reason.")
    return float(accepted)
