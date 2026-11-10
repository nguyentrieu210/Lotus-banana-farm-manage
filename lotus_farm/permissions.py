from lotus_farm.controls import query_condition


def farm(user=None):
    return query_condition("Farm", user)


def lotus_block_forecast_profile(user=None):
    return query_condition("Lotus Block Forecast Profile", user)


def farm_block(user=None):
    return query_condition("Farm Block", user)


def work_team(user=None):
    from lotus_farm.mobile_access import allowed_teams, roles, is_manager, LEADER, SUPERVISOR
    import frappe
    user = user or frappe.session.user
    if is_manager(user) or not {LEADER, SUPERVISOR}.intersection(roles(user)):
        return query_condition("Work Team", user)
    farms = frappe.get_all("User Permission", filters={"user": user, "allow": "Farm"}, pluck="for_value")
    permitted = set()
    for farm in farms:
        permitted.update(allowed_teams(farm, user))
    if not permitted:
        return "1=0"
    values = ",".join(frappe.db.escape(value) for value in sorted(permitted))
    return f"`tabWork Team`.`name` in ({values})"


def work_schedule_rule(user=None):
    return query_condition("Work Schedule Rule", user)


def warehouse_mapping(user=None):
    return query_condition("Warehouse Mapping", user)


def packhouse_shift(user=None):
    return query_condition('Packhouse Shift', user)

def lotus_alert(user=None):
    return query_condition('Lotus Alert',user)


def bunch_tag(user=None):
    condition = query_condition('Bunch Tag', user)
    return f"(COALESCE(`tabBunch Tag`.`farm`, '') = '' OR ({condition}))" if condition else ''
