from lotus_farm.controls import query_condition


def farm(user=None):
    return query_condition("Farm", user)


def farm_block(user=None):
    return query_condition("Farm Block", user)


def crop_cycle(user=None):
    return query_condition("Crop Cycle", user)


def sucker_selection_batch(user=None):
    return query_condition("Sucker Selection Batch", user)


def bunch_operation(user=None):
    return query_condition("Bunch Operation", user)


def defect_inspection(user=None):
    return query_condition("Defect Inspection", user)


def harvest_forecast(user=None):
    return query_condition("Harvest Forecast", user)


def harvest_actual(user=None):
    return query_condition("Harvest Actual", user)


def harvest_lot(user=None):
    return query_condition("Harvest Lot", user)


def packout_run(user=None):
    return query_condition("Packout Run", user)


def scale_reading(user=None):
    return query_condition("Scale Reading", user)


def integration_event(user=None):
    return query_condition("Integration Event", user)


def supply_reconciliation(user=None):
    return query_condition("Supply Reconciliation", user)
