class ForecastInputError(ValueError):
    pass


def _number(value, default=0):
    if value is None or value == "":
        return float(default)
    return float(value)


def _rate(value, label, default):
    value = _number(value, default)
    if not 0 <= value <= 100:
        raise ForecastInputError(f"{label} must be between 0 and 100.")
    return value


def calculate_availability(
    source_bunch_qty,
    avg_bunch_weight_kg,
    expected_defect_rate_percent=None,
    safety_buffer_percent=0,
    committed_qty_kg=0,
    bunch_survival_rate_percent=100,
    quality_pass_rate_percent=None,
    packout_rate_percent=100,
):
    source_bunch_qty = _number(source_bunch_qty)
    avg_bunch_weight_kg = _number(avg_bunch_weight_kg)
    committed_qty_kg = _number(committed_qty_kg)

    if source_bunch_qty < 0 or avg_bunch_weight_kg < 0 or committed_qty_kg < 0:
        raise ForecastInputError("Forecast quantities cannot be negative.")

    survival_rate = _rate(
        bunch_survival_rate_percent, "Bunch Survival Rate", 100
    )
    safety_buffer = _rate(safety_buffer_percent, "Safety Buffer", 0)
    packout_rate = _rate(packout_rate_percent, "Packout Rate", 100)

    if quality_pass_rate_percent is None or quality_pass_rate_percent == "":
        defect_rate = _rate(
            expected_defect_rate_percent, "Expected Defect Rate", 0
        )
        quality_pass_rate = 100 - defect_rate
    else:
        quality_pass_rate = _rate(
            quality_pass_rate_percent, "Quality Pass Rate", 100
        )

    expected_harvest_bunch_qty = source_bunch_qty * survival_rate / 100
    gross = expected_harvest_bunch_qty * avg_bunch_weight_kg
    saleable = gross * quality_pass_rate / 100
    packed = saleable * packout_rate / 100
    safe_saleable = packed * (1 - safety_buffer / 100)
    atp = safe_saleable - committed_qty_kg
    shortage = max(-atp, 0)

    if shortage > 0:
        status = "Overcommitted"
    elif safe_saleable and atp / safe_saleable <= 0.1:
        status = "Tight"
    else:
        status = "Available"

    return {
        "expected_harvest_bunch_qty": round(expected_harvest_bunch_qty, 3),
        "gross_forecast_kg": round(gross, 3),
        "saleable_forecast_kg": round(saleable, 3),
        "packed_forecast_kg": round(packed, 3),
        "safe_saleable_kg": round(safe_saleable, 3),
        "committed_qty_kg": round(committed_qty_kg, 3),
        "available_to_promise_kg": round(atp, 3),
        "shortage_kg": round(shortage, 3),
        "availability_status": status,
    }
