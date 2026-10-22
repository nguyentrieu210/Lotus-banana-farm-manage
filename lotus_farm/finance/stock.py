"""Tài chính – Kế toán: a material issue carries farm / lot / crop cycle / work type on each row, so ERPNext's
own stock posting (Nợ 621 chi phí nguyên liệu, vật liệu trực tiếp / Có kho) lands on the right lot. Planned issues take them from
the Material Requirement; a manual issue names the lot in "Khu vực / lô sử dụng" (its first part is matched to a
lot code of the issuing warehouse's farm). Nothing is posted twice: the warehouse stays the only writer.
"""
import re

import frappe
from frappe.utils import flt, getdate

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


RECEIPT_REASONS = {
    # reason -> (label, mapping key of the credited account, needs a lot, needs a supplier)
    'Purchase': ('Mua ngoài chưa qua đơn mua (chờ hóa đơn)', 'received_not_billed', False, True),
    'Recovery': ('Thu hồi vật tư thừa từ lô', 'material_cost', True, False),
    'Surplus': ('Thừa khi kiểm kê / chờ xử lý', 'stock_adjustment', False, False),
}
ISSUE_PURPOSES = {
    # purpose of a Material Issue made outside the Lotus issue form -> (label, mapping key, needs a lot)
    'Production': ('Xuất cho sản xuất (vào lô)', 'material_cost', True),
    'Sale': ('Xuất bán / sản phẩm phụ', 'cost_of_goods_sold', False),
    'Disposal': ('Xuất hủy, hư hỏng', 'other_expense', False),
    'Shortage': ('Thiếu khi kiểm kê / chờ xử lý', 'stock_shortage', False),
}


def _enforced(doc):
    cfg = setup.settings()
    on = bool(cfg.finance_enabled and cfg.cutover_date and getdate(doc.posting_date) >= getdate(cfg.cutover_date))
    return on, (setup.mapping(cfg) if on else {})


def _row_dims(row, warehouse):
    dims = _requirement_dims(row.lotus_requirement) if row.get('lotus_requirement') else {}
    if not dims.get('lotus_farm_block') and row.get('lotus_farm_block'):
        dims['lotus_farm_block'] = row.lotus_farm_block
    if not dims.get('lotus_farm_block'):
        found = block_from_text(row.get('lotus_usage_area'), row.get('lotus_farm') or _warehouse_farm(warehouse))
        if found:
            dims.update(lotus_farm_block=found.name, lotus_farm=found.farm)
    if dims.get('lotus_farm_block') and not dims.get('lotus_farm'):
        dims['lotus_farm'] = frappe.db.get_value('Farm Block', dims['lotus_farm_block'], 'farm')
    for field in rules.DIM_FIELDS:
        if dims.get(field):
            row.set(field, dims[field])


def stock_entry_accounts(doc, method=None):
    """Stock Entry validate: the account each receipt / issue row posts against, once finance is on.
    - Material Issue from the Lotus issue form (lotus_issue_mode): Nợ 621 on the row's lot.
    - Other Material Issue: the purpose decides (production 621 with lot, sale 632, disposal 811, shortage 1381).
    - Material Receipt: the reason decides (purchase without order 3388 with supplier, recovery 621 of the lot, surplus 3381);
      harvest receipts are made by lotus_farm.finance.costing with their own accounts."""
    if doc.docstatus == 2 or not _has_dims(doc):
        return
    kind = doc.get('stock_entry_type')
    if kind not in ('Material Issue', 'Material Receipt'):
        return
    enforce, m = _enforced(doc)
    cost_center = frappe.get_cached_value('Company', doc.company, 'cost_center')
    if kind == 'Material Issue':
        purpose = 'Production' if doc.get('lotus_issue_mode') else doc.get('lotus_issue_purpose')
        for i, row in enumerate(doc.items, start=1):
            _row_dims(row, row.s_warehouse)
            if not enforce:
                continue
            if purpose not in ISSUE_PURPOSES:
                frappe.throw('Chọn mục đích xuất kho (cho sản xuất, xuất bán, hủy hay thiếu kiểm kê) để ghi đúng tài khoản.')
            label, key, needs_lot = ISSUE_PURPOSES[purpose]
            if needs_lot and not row.get('lotus_farm'):
                frappe.throw('Dòng %d (%s): chọn lô sử dụng có trong danh sách lô để tính chi phí vào đúng lô.' % (i, row.item_code))
            row.expense_account = m[key]
            row.cost_center = row.cost_center or cost_center
        return
    if doc.get('lotus_receipt_reason') == 'Harvest':
        return
    reason = doc.get('lotus_receipt_reason')
    for i, row in enumerate(doc.items, start=1):
        if reason == 'Recovery':
            _row_dims(row, row.t_warehouse)
        if not enforce:
            continue
        if reason not in RECEIPT_REASONS:
            frappe.throw('Chọn lý do nhập kho (mua ngoài, thu hồi từ lô hay thừa kiểm kê) để ghi đúng tài khoản.')
        label, key, needs_lot, needs_supplier = RECEIPT_REASONS[reason]
        if needs_supplier and not doc.get('lotus_supplier'):
            frappe.throw('Nhập hàng mua ngoài cần chọn nhà cung cấp để kế toán lập hóa đơn và công nợ.')
        if needs_lot and not row.get('lotus_farm'):
            frappe.throw('Dòng %d (%s): ghi mã lô vật tư được thu hồi về để giảm chi phí của lô đó.' % (i, row.item_code))
        row.expense_account = m[key]
        row.cost_center = row.cost_center or cost_center


# Kept for the hooks of earlier releases.
issue_dimensions = stock_entry_accounts


def reconciliation_accounts(doc, method=None):
    """Stock Reconciliation before submit: a count posts surplus to 3381 and shortage to 1381; opening stock is offset by
    the opening-balance equity account (TT99 has no 'Temporary' account for ERPNext to pick)."""
    enforce, m = _enforced(doc)
    if not enforce:
        return
    if doc.purpose == 'Opening Stock':
        doc.expense_account = m['opening_equity']
        return
    difference = sum(flt(r.amount_difference) for r in doc.items)
    doc.expense_account = m['stock_shortage'] if difference < 0 else m['stock_adjustment']
    if any(flt(r.amount_difference) > 0 for r in doc.items) and any(flt(r.amount_difference) < 0 for r in doc.items):
        frappe.throw('Phiếu kiểm kê có cả thừa và thiếu. Lập riêng một phiếu cho hàng thừa và một phiếu cho hàng thiếu để kế toán ghi đúng 3381 / 1381.')


@frappe.whitelist()
def receipt_options():
    """Reasons and suppliers for the receipt form (warehouse users read suppliers already)."""
    if frappe.session.user == 'Guest':
        frappe.throw('Vui lòng đăng nhập.', frappe.AuthenticationError)
    cfg = setup.settings()
    return dict(enabled=bool(cfg.finance_enabled), reasons=[dict(value=k, label=v[0], lot=v[2], supplier=v[3]) for k, v in RECEIPT_REASONS.items()],
                suppliers=frappe.get_list('Supplier', filters={'disabled': 0}, fields=['name', 'supplier_name'], order_by='supplier_name', limit_page_length=0))


@frappe.whitelist()
def block_codes(warehouse=None):
    """Lot codes for the issue form's suggestions (the warehouse's farm, else all permitted farms)."""
    if frappe.session.user == 'Guest':
        frappe.throw('Vui lòng đăng nhập.', frappe.AuthenticationError)
    farm = _warehouse_farm(warehouse)
    rows = frappe.get_list('Farm Block', filters={'farm': farm, 'active': 1} if farm else {'active': 1}, fields=['block_code', 'block_name', 'farm'],
                           order_by='farm, block_code', limit_page_length=0)
    return [dict(code=r.block_code, label=(r.block_name or r.block_code) + ('' if farm else ' · ' + r.farm)) for r in rows]
