"""Resolve biological supply by scope and harvest period, never by guessed Item."""
import frappe


def match_forecast(actual):
    from lotus_farm.controls import lock
    lock('Crop Cycle', actual.crop_cycle)
    rows = frappe.get_all('Harvest Forecast', filters={
        'farm': actual.farm, 'farm_block': actual.farm_block,
        'crop_cycle': actual.crop_cycle, 'sucker_selection_batch': actual.sucker_selection_batch or '',
        'supply_state': 'Released', 'period_start_date': ['<=', actual.harvest_date],
        'period_end_date': ['>=', actual.harvest_date]}, fields=['name'])
    if len(rows) > 1:
        frappe.throw('More than one released forecast matches this harvest; reconcile overlapping supply first.')
    if rows:
        frappe.get_doc('Harvest Forecast', rows[0].name).check_permission('read')
        return rows[0].name
    return None


def check_unlinked_stock(actual):
    if not actual.forecast and match_forecast(actual):
        frappe.throw('This harvest has unresolved released supply. Cancel/amend the harvest to link its forecast before posting stock.')


def refresh_supply(doc, method=None):
    if not doc.forecast:return
    from lotus_farm.controls import lock, command
    lock('Harvest Forecast', doc.forecast)
    supply=frappe.get_doc('Harvest Forecast',doc.forecast)
    supply.check_permission('read')
    with command(supply,'supply'):supply.save(ignore_permissions=True)
