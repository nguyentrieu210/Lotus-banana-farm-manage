"""Tài chính – Kế toán: a material issue carries farm / lot / crop cycle / work type on each row, so ERPNext's
own stock posting (Nợ 621 chi phí nguyên liệu, vật liệu trực tiếp / Có kho) lands on the right lot. Planned issues take them from
the Material Requirement; a manual issue names the lot in "Khu vực / lô sử dụng" (its first part is matched to a
lot code of the issuing warehouse's farm). Nothing is posted twice: the warehouse stays the only writer.
"""
import re

import frappe
from frappe.utils import getdate

from lotus_farm.finance import rules, setup


def _has_dims(doc):
    return frappe.get_meta('Stock Entry Detail').has_field('lotus_farm_block')


def _warehouse_farm(warehouse):
    if not warehouse or not frappe.db.exists('DocType', 'Warehouse Mapping'):
        return None
    farms = frappe.get_all('Warehouse Mapping', filters={'warehouse': warehouse}, pluck='farm', distinct=True)
    return farms[0] if len(set(farms)) == 1 else None


def block_from_text(text, farm=None):
    """'A12 / A12-3' -> Farm Block whose code is A12 (in the farm when known); None when unknown or ambiguous."""
    code = re.split(r'[/,;|]', str(text or ''))[0].strip()
    if not code:
        return None
    filters = {'block_code': code}
    if farm:
        filters['farm'] = farm
    found = frappe.get_all('Farm Block', filters=filters, fields=['name', 'farm'], limit_page_length=2)
    return found[0] if len(found) == 1 else None


def _requirement_dims(requirement):
    r = frappe.db.get_value('Material Requirement', requirement, ['farm', 'farm_block', 'crop_cycle', 'work_plan_line'], as_dict=True)
    if not r:
        return {}
    work_type = frappe.db.get_value('Daily Work Plan Line', r.work_plan_line, 'work_type') if r.work_plan_line else None
    return dict(lotus_farm=r.farm, lotus_farm_block=r.farm_block, lotus_crop_cycle=r.crop_cycle, lotus_work_type=work_type)


def issue_dimensions(doc, method=None):
    """Stock Entry validate: fill the dimensions of Material Issue rows; once finance is on (from the cutover date)
    every row must name its farm and the row's expense account is direct material cost (621)."""
    if doc.docstatus == 2 or doc.get('stock_entry_type') != 'Material Issue' or not _has_dims(doc):
        return
    cfg = setup.settings()
    enforce = bool(cfg.finance_enabled and cfg.cutover_date and getdate(doc.posting_date) >= getdate(cfg.cutover_date))
    m = setup.mapping(cfg) if enforce else {}
    for i, row in enumerate(doc.items, start=1):
        dims = _requirement_dims(row.lotus_requirement) if row.get('lotus_requirement') else {}
        if not dims.get('lotus_farm_block') and row.get('lotus_farm_block'):
            dims['lotus_farm_block'] = row.lotus_farm_block
        if not dims.get('lotus_farm_block'):
            found = block_from_text(row.get('lotus_usage_area'), row.get('lotus_farm') or _warehouse_farm(row.s_warehouse))
            if found:
                dims.update(lotus_farm_block=found.name, lotus_farm=found.farm)
        if dims.get('lotus_farm_block') and not dims.get('lotus_farm'):
            dims['lotus_farm'] = frappe.db.get_value('Farm Block', dims['lotus_farm_block'], 'farm')
        for field in rules.DIM_FIELDS:
            if dims.get(field):
                row.set(field, dims[field])
        if enforce:
            if not row.get('lotus_farm'):
                frappe.throw('Dòng %d (%s): chọn lô sử dụng có trong danh sách lô để tính chi phí vào đúng lô.' % (i, row.item_code))
            row.expense_account = m['material_cost']
            row.cost_center = row.cost_center or frappe.get_cached_value('Company', doc.company, 'cost_center')


@frappe.whitelist()
def block_codes(warehouse=None):
    """Lot codes for the issue form's suggestions (the warehouse's farm, else all permitted farms)."""
    if frappe.session.user == 'Guest':
        frappe.throw('Vui lòng đăng nhập.', frappe.AuthenticationError)
    farm = _warehouse_farm(warehouse)
    rows = frappe.get_list('Farm Block', filters={'farm': farm, 'active': 1} if farm else {'active': 1}, fields=['block_code', 'block_name', 'farm'],
                           order_by='farm, block_code', limit_page_length=0)
    return [dict(code=r.block_code, label=(r.block_name or r.block_code) + ('' if farm else ' · ' + r.farm)) for r in rows]
