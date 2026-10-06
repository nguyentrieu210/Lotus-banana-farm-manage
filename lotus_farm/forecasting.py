class ForecastInputError(ValueError):
    pass


def calculate_availability(
    source_bunch_qty,
    avg_bunch_weight_kg,
    expected_defect_rate_percent=0,
    safety_buffer_percent=0,
    committed_qty_kg=0,
):
    source_bunch_qty = float(source_bunch_qty or 0)
    avg_bunch_weight_kg = float(avg_bunch_weight_kg or 0)
    defect_rate = float(expected_defect_rate_percent or 0)
    safety_buffer = float(safety_buffer_percent or 0)
    committed_qty_kg = float(committed_qty_kg or 0)

    if source_bunch_qty < 0 or avg_bunch_weight_kg < 0 or committed_qty_kg < 0:
        raise ForecastInputError("Forecast quantities cannot be negative.")
    if not 0 <= defect_rate <= 100:
        raise ForecastInputError("Expected Defect Rate must be between 0 and 100.")
    if not 0 <= safety_buffer <= 100:
        raise ForecastInputError("Safety Buffer must be between 0 and 100.")

    gross = source_bunch_qty * avg_bunch_weight_kg
    saleable = gross * (1 - defect_rate / 100)
    safe_saleable = saleable * (1 - safety_buffer / 100)
    atp = safe_saleable - committed_qty_kg
    shortage = max(-atp, 0)

    if shortage > 0:
        status = "Overcommitted"
    elif safe_saleable and atp / safe_saleable <= 0.1:
        status = "Tight"
    else:
        status = "Available"

    return {
        "gross_forecast_kg": round(gross, 3),
        "saleable_forecast_kg": round(saleable, 3),
        "safe_saleable_kg": round(safe_saleable, 3),
        "committed_qty_kg": round(committed_qty_kg, 3),
        "available_to_promise_kg": round(atp, 3),
        "shortage_kg": round(shortage, 3),
        "availability_status": status,
    }
