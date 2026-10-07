"""BRD metric contracts, independent of Frappe and database state."""

import hashlib
import json
from decimal import Decimal, InvalidOperation


class RuleError(ValueError):
    pass


def quantity(value, label="Quantity", *, positive=False):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise RuleError(f"{label} must be numeric.") from None
    if not result.is_finite() or result < 0 or (positive and result == 0):
        raise RuleError(f"{label} must be finite and {'positive' if positive else 'non-negative'}.")
    return result


def canonical_hash(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def reconcile_mass(inputs, outputs, reject, loss, tolerance):
    incoming = sum((quantity(v, "Input kg", positive=True) for v in inputs), Decimal(0))
    finished = sum((quantity(v, "Output kg", positive=True) for v in outputs), Decimal(0))
    variance = incoming - finished - quantity(reject) - quantity(loss)
    if abs(variance) > quantity(tolerance, "Tolerance"):
        raise RuleError(f"Mass balance differs by {variance} kg; correct weights before release.")
    return {"input_kg": float(incoming), "output_kg": float(finished), "mass_variance_kg": float(variance)}


def reserve_limit(safe, reserved, requested, remaining_demand):
    requested = quantity(requested, "Reserved kg", positive=True)
    if requested > quantity(safe) - quantity(reserved):
        raise RuleError("Reservation exceeds forecast ATP.")
    if requested > quantity(remaining_demand):
        raise RuleError("Reservation exceeds remaining Sales Order Item demand.")
    return float(requested)


def scale_net(gross, tare):
    gross, tare = quantity(gross), quantity(tare)
    if tare > gross:
        raise RuleError("Tare cannot exceed gross weight.")
    return float(gross - tare)


def calibration(rows, minimum_samples):
    """Weighted kg/bunch and field release; never average per-row averages."""
    clean = []
    for r in rows:
        bunches = quantity(r["harvested_bunch_qty"], "Bunches", positive=True)
        gross = quantity(r["gross_weight_kg"], "Gross", positive=True)
        released = quantity(r["saleable_weight_kg"], "Released")
        if released > gross:
            raise RuleError("Released kg cannot exceed gross kg.")
        clean.append((bunches, gross, released))
    if len(clean) < int(minimum_samples) or int(minimum_samples) < 1:
        raise RuleError("Not enough matched actual samples for calibration.")
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


def integer_quantity(value, label="Count"):
    result = quantity(value, label)
    if result != result.to_integral_value():
        raise RuleError(f"{label} must be a whole number.")
    return int(result)
