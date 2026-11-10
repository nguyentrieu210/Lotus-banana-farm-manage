"""Number and payload checks shared by the controllers, independent of Frappe and database state."""

from decimal import Decimal, InvalidOperation


class RuleError(ValueError):
    pass


def quantity(value, label="Số lượng", *, positive=False):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise RuleError(f"{label} phải là số.") from None
    if not result.is_finite() or result < 0 or (positive and result == 0):
        raise RuleError(f"{label} phải là số hữu hạn và {'lớn hơn 0' if positive else 'không âm'}.")
    return result


def integer_quantity(value, label="Số đếm"):
    result = quantity(value, label)
    if result != result.to_integral_value():
        raise RuleError(f"{label} phải là số nguyên.")
    return int(result)
