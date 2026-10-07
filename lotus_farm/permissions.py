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


def daily_work_plan(user=None):
    return query_condition("Daily Work Plan", user)


def daily_work_result(user=None):
    return query_condition("Daily Work Result", user)


def labor_allocation(user=None):
    return query_condition("Labor Allocation", user)


def daily_labor_summary(user=None):
    return query_condition("Daily Labor Summary", user)


def material_requirement(user=None):
    return query_condition("Material Requirement", user)


def material_consumption(user=None):
    return query_condition("Material Consumption", user)


def material_recovery(user=None):
    return query_condition("Material Recovery", user)


def bunch_cancellation(user=None):
    return query_condition("Bunch Cancellation", user)


def planting_event(user=None):
    return query_condition("Planting Event", user)


def disease_observation(user=None):
    return query_condition("Disease Observation", user)


def fruit_measurement(user=None):
    return query_condition("Fruit Measurement", user)


def incoming_quality_inspection(user=None):
    return query_condition("Incoming Quality Inspection", user)


def daily_production_close(user=None):
    return query_condition("Daily Production Close", user)


def source_import_batch(user=None):
    return query_condition("Source Import Batch", user)


def legacy_organization_map(user=None):
    return query_condition("Legacy Organization Map", user)


def farm_plot(user=None):
    return query_condition("Farm Plot", user)


def work_team(user=None):
    return query_condition("Work Team", user)


def material_norm_profile(user=None):
    return query_condition("Material Norm Profile", user)


def secondary_product_movement(user=None):
    return query_condition("Secondary Product Movement", user)


def cycle_closing_report(user=None):
    return query_condition("Cycle Closing Report", user)


def legacy_cycle_plot_mapping(user=None):
    return query_condition("Legacy Cycle Plot Mapping",user)


def plot_geometry(user=None):
    return query_condition("Plot Geometry", user)


def scale_device(user=None):
    return query_condition("Scale Device", user)


def work_schedule_rule(user=None):
    return query_condition("Work Schedule Rule", user)


def field_capture(user=None):
    return query_condition("Field Capture", user)


def integration_task(user=None):
    return query_condition("Integration Task", user)


def warehouse_mapping(user=None):
    return query_condition("Warehouse Mapping", user)


def onedrive_feed(user=None):
    return query_condition('OneDrive Feed',user)


def source_inventory_item(user=None):
    return query_condition('Source Inventory Item',user)
