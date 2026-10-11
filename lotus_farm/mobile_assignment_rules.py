"""Farm task quantity split; independent of Frappe for deterministic tests."""
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from lotus_farm.rules import RuleError, quantity


def split_quantity(total, weights, whole=False):
    """Allocate a BLOCK total once among plots; conserve the exact stated total.

    Whole-unit work (buồng/cây) uses largest remainders. Other quantities use
    three decimal places, with the remainder on the final plot.
    The caller should display the split BEFORE submitting the plan.
    """
    total = quantity(total, "Khối lượng giao", positive=True)
    clean = [quantity(w, "Diện tích thửa", positive=True) for w in weights]
    if not clean:
        raise RuleError("Lô chưa có thửa đang hoạt động.")
    weight_sum = sum(clean)
    shares = [total * w / weight_sum for w in clean]
    if whole:
        if total != total.to_integral_value():
            raise RuleError("Công việc tính bằng buồng/cây phải giao số nguyên.")
        floors = [int(v.to_integral_value(rounding=ROUND_FLOOR)) for v in shares]
        missing = int(total) - sum(floors)
        indices = sorted(range(len(shares)), key=lambda i: (-(shares[i] - floors[i]), i))
        for i in indices[:missing]:
            floors[i] += 1
        return [float(v) for v in floors]
    quantum = Decimal("0.001")
    if total != total.quantize(quantum):
        raise RuleError("Khối lượng không được vượt quá 3 chữ số thập phân.")
    result = [v.quantize(quantum, rounding=ROUND_HALF_UP) for v in shares[:-1]]
    result.append(total - sum(result, Decimal("0")))
    return [float(v) for v in result]
