"""BRD metric contracts, independent of Frappe and database state."""

import hashlib
import json
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


def canonical_hash(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def reconcile_mass(inputs, outputs, reject, loss, tolerance):
    incoming = sum((quantity(v, "Số kg đầu vào", positive=True) for v in inputs), Decimal(0))
    finished = sum((quantity(v, "Số kg đầu ra", positive=True) for v in outputs), Decimal(0))
    variance = incoming - finished - quantity(reject) - quantity(loss)
    if abs(variance) > quantity(tolerance, "Dung sai"):
        raise RuleError(f"Cân bằng khối lượng lệch {variance} kg; sửa khối lượng trước khi phát hành.")
    return {"input_kg": float(incoming), "output_kg": float(finished), "mass_variance_kg": float(variance)}


def reserve_limit(safe, reserved, requested, remaining_demand):
    requested = quantity(requested, "Số kg giữ hàng", positive=True)
    if requested > quantity(safe) - quantity(reserved):
        raise RuleError("Số giữ hàng vượt lượng dự thu còn có thể cam kết.")
    if requested > quantity(remaining_demand):
        raise RuleError("Số giữ hàng vượt nhu cầu còn lại của dòng đơn bán hàng.")
    return float(requested)


def scale_net(gross, tare):
    gross, tare = quantity(gross), quantity(tare)
    if tare > gross:
        raise RuleError("Khối lượng bì không được vượt khối lượng cân tổng.")
    return float(gross - tare)


def calibration(rows, minimum_samples):
    """Weighted kg/bunch and field release; never average per-row averages."""
    clean = []
    for r in rows:
        bunches = quantity(r["harvested_bunch_qty"], "Số buồng", positive=True)
        gross = quantity(r["gross_weight_kg"], "Khối lượng cân tổng", positive=True)
        released = quantity(r["saleable_weight_kg"], "Số kg phát hành")
        if released > gross:
            raise RuleError("Số kg phát hành không được vượt số kg cân tổng.")
        clean.append((bunches, gross, released))
    if len(clean) < int(minimum_samples) or int(minimum_samples) < 1:
        raise RuleError("Chưa đủ mẫu thực tế đã đối chiếu để hiệu chỉnh.")
    bunches, gross, released = [sum((r[i] for r in clean), Decimal(0)) for i in range(3)]
    return dict(
        sample_count=len(clean),
        covered_bunches=float(bunches),
        covered_kg=float(gross),
        avg_bunch_weight_kg=float(gross / bunches),
        quality_pass_rate_percent=float(released / gross * 100),
    )


def forecast_accuracy(pairs):
    pairs = [(quantity(f), quantity(a)) for f, a in pairs]
    total = sum((a for _, a in pairs), Decimal(0))
    if not total:
        return {"bias": None, "wape": None, "sample_count": len(pairs)}
    return {
        "bias": float(sum((f - a for f, a in pairs), Decimal(0)) / total),
        "wape": float(sum((abs(f - a) for f, a in pairs), Decimal(0)) / total),
        "sample_count": len(pairs),
    }


def integer_quantity(value, label="Số đếm"):
    result = quantity(value, label)
    if result != result.to_integral_value():
        raise RuleError(f"{label} phải là số nguyên.")
    return int(result)
