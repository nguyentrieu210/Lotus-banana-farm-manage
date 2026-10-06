"""Pure business rules. All quantities are canonical kilograms."""
from decimal import Decimal, InvalidOperation


class SupplyError(ValueError):
    pass


def quantity(value, label="Quantity", positive=False):
    try:
        number = Decimal(str(value if value not in (None, "") else 0))
    except (InvalidOperation, ValueError):
        raise SupplyError(f"{label} must be a number.") from None
    if not number.is_finite() or number < 0 or (positive and number == 0):
        raise SupplyError(f"{label} must be finite and {'positive' if positive else 'non-negative'}.")
    return number


def mass_balance(input_kg, outputs, loss_kg=0, tolerance_kg=0):
    incoming = quantity(input_kg, "Input kg", positive=True)
    outgoing = sum((quantity(q, "Output kg") for q in outputs), Decimal(0))
    loss = quantity(loss_kg, "Recorded loss kg")
    tolerance = quantity(tolerance_kg, "Tolerance kg")
    variance = incoming - outgoing - loss
    if abs(variance) > tolerance:
        raise SupplyError(f"Packout does not balance: {variance} kg unexplained.")
    return float(variance)


def require_capacity(requested, capacity, already_reserved=0):
    requested = quantity(requested, "Reservation kg", positive=True)
    capacity = quantity(capacity, "Capacity kg")
    reserved = quantity(already_reserved, "Reserved kg")
    if requested + reserved > capacity:
        raise SupplyError("Reservation exceeds remaining supply or Sales Order demand.")


def stock_quantity(net_kg, kg_per_stock_uom):
    return float(quantity(net_kg, "Net kg", positive=True) / quantity(
        kg_per_stock_uom, "kg per stock UOM", positive=True
    ))
