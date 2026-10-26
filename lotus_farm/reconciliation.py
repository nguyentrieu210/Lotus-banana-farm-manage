import json

import frappe
from frappe.utils import flt, now_datetime

from lotus_farm.controls import command, lock, require_role
from lotus_farm.rules import canonical_hash
from lotus_farm.stock_bridge import _forecast_outputs


def _linked_materialized_allocations(stock_reservation):
    return frappe.get_all(
        "Forecast Allocation",
        filters={
            "stock_reservation": stock_reservation,
            "allocation_state": "Materialized",
            "parenttype": "Harvest Forecast",
        },
        fields=["name", "parent", "reserved_qty_kg", "sales_order", "sales_order_item", "item"],
        order_by="parent, name",
    )


def _stock_entry_effect(request):
    if not request.stock_entry or request.stock_reservation:
        frappe.throw("Đảo phiếu kho cần đúng một phiếu kho đích.")
    lock("Stock Entry", request.stock_entry)
    entry = frappe.get_doc("Stock Entry", request.stock_entry)
    entry.check_permission("read")
    if entry.docstatus != 1 or not entry.get("lotus_packout_run"):
        frappe.throw("Chọn một phiếu kho đóng gói lại (Repack) của Lotus đã ghi sổ.")
    run = frappe.get_doc("Packout Run", entry.lotus_packout_run)
    run.check_permission("read")
    if run.farm != request.farm:
        frappe.throw("Vườn của phiếu đối soát phải khớp đợt đóng gói.")

    forecast_totals = _forecast_outputs(run)
    impacts = []
    active_reservations = set()
    for forecast in sorted(forecast_totals):
        lock("Harvest Forecast", forecast)
        supply = frappe.get_doc("Harvest Forecast", forecast)
        item_amounts = forecast_totals[forecast]
        amount = flt(sum(item_amounts.values()), 3)
        if supply.output_plan:
            materialized = {row.item: flt(row.materialized_qty_kg, 3) for row in supply.output_plan}
            for item, item_amount in item_amounts.items():
                if materialized.get(item, 0) + 0.0005 < flt(item_amount, 3):
                    frappe.throw("Số lượng dự thu đã hiện thực theo từng vật tư nhỏ hơn số đề xuất đảo.")
        elif flt(supply.materialized_qty_kg, 3) + 0.0005 < amount:
            frappe.throw("Số lượng dự thu đã hiện thực nhỏ hơn số đề xuất đảo.")
        impacts.append(
            {
                "forecast": forecast,
                "qty_kg": amount,
                "items": [
                    {"item": item, "qty_kg": flt(item_amount, 3)}
                    for item, item_amount in sorted(item_amounts.items())
                ],
            }
        )
        for row in frappe.get_all(
            "Forecast Allocation",
            filters={
                "parent": forecast,
                "parenttype": "Harvest Forecast",
                "allocation_state": "Materialized",
            },
            fields=["stock_reservation"],
        ):
            if row.stock_reservation and frappe.db.get_value(
                "Stock Reservation Entry", row.stock_reservation, "docstatus"
            ) == 1:
                active_reservations.add(row.stock_reservation)
    if active_reservations:
        frappe.throw(
            "Hủy giữ hàng thực tế đã liên kết qua phiếu đối soát trước: "
            + ", ".join(sorted(active_reservations))
        )
    return {
        "type": "Stock Entry Reversal",
        "farm": request.farm,
        "stock_entry": entry.name,
        "packout_run": run.name,
        "forecast_impacts": impacts,
    }


def _stock_reservation_effect(request):
    if not request.stock_reservation or request.stock_entry:
        frappe.throw("Hủy giữ hàng cần đúng một phiếu giữ hàng.")
    lock("Stock Reservation Entry", request.stock_reservation)
    reservation = frappe.get_doc("Stock Reservation Entry", request.stock_reservation)
    reservation.check_permission("read")
    if reservation.docstatus != 1 or reservation.voucher_type != "Sales Order":
        frappe.throw("Chọn một phiếu giữ hàng của đơn bán hàng đã duyệt.")
    if flt(reservation.delivered_qty) or flt(reservation.consumed_qty) or flt(reservation.transferred_qty):
        frappe.throw("Hàng giữ đã giao, đã dùng hoặc đã chuyển phải được đối soát ở khâu sau trước.")

    rows = _linked_materialized_allocations(reservation.name)
    if not rows:
        frappe.throw("Phiếu giữ hàng thực tế này không có phân bổ Lotus đang hiệu lực.")
    effects = []
    farms = set()
    for row in rows:
        lock("Harvest Forecast", row.parent)
        supply = frappe.get_doc("Harvest Forecast", row.parent)
        supply.check_permission("read")
        farms.add(supply.farm)
        if (
            row.sales_order != reservation.voucher_no
            or row.sales_order_item != reservation.voucher_detail_no
            or row.item != reservation.item_code
        ):
            frappe.throw("Phân bổ Lotus đã liên kết không còn khớp với phiếu giữ hàng thực tế.")
        effects.append(
            {
                "forecast": row.parent,
                "allocation": row.name,
                "qty_kg": flt(row.reserved_qty_kg, 3),
            }
        )
    if farms != {request.farm}:
        frappe.throw("Một phiếu đối soát chỉ áp dụng cho hàng giữ thực tế của một vườn.")
    return {
        "type": "Stock Reservation Cancellation",
        "farm": request.farm,
        "stock_reservation": reservation.name,
        "sales_order": reservation.voucher_no,
        "sales_order_item": reservation.voucher_detail_no,
        "reservation_disposition": request.reservation_disposition,
        "allocation_impacts": effects,
    }


def build_effect(request):
    lock('Farm', request.farm)
    if request.reconciliation_type == "Stock Entry Reversal":
        return _stock_entry_effect(request)
    if request.reconciliation_type == "Stock Reservation Cancellation":
        return _stock_reservation_effect(request)
    frappe.throw("Loại đối soát không được hỗ trợ.")


def approve(request):
    require_role("Lotus Auditor")
    effect = build_effect(request)
    request.effect_json = json.dumps(effect, sort_keys=True, separators=(",", ":"), default=str)
    request.effect_hash = canonical_hash(effect)
    request.state = "Approved"
    request.reviewed_by = frappe.session.user
    request.reviewed_at = now_datetime()


@frappe.whitelist(methods=["POST"])
def execute(reconciliation):
    initial = frappe.get_doc('Supply Reconciliation', reconciliation)
    initial.check_permission('read')
    lock('Farm', initial.farm)
    lock("Supply Reconciliation", reconciliation)
    request = frappe.get_doc("Supply Reconciliation", reconciliation, for_update=True)
    request.check_permission("read")
    if request.docstatus != 1 or request.state != "Approved":
        frappe.throw("Chỉ áp dụng được phiếu đối soát đã duyệt.")
    if request.reconciliation_type == "Stock Entry Reversal":
        require_role("Lotus Packing Supervisor", "Lotus Auditor")
    else:
        require_role("Lotus Sales Planner", "Lotus Auditor")

    effect = build_effect(request)
    if canonical_hash(effect) != request.effect_hash:
        frappe.throw("Chứng từ đích đã thay đổi sau khi duyệt; hãy kiểm tra và duyệt phiếu đối soát mới.")

    if request.reconciliation_type == "Stock Entry Reversal":
        target = frappe.get_doc("Stock Entry", request.stock_entry)
        action = "reconciliation_cancel"
    else:
        target = frappe.get_doc("Stock Reservation Entry", request.stock_reservation)
        action = (
            "reconciliation_cancel_restore"
            if request.reservation_disposition == "Restore Future Reservation"
            else "reconciliation_cancel_release"
        )
    target.check_permission("cancel")
    # The approved request is itself a submitted backlink to the target. Temporarily
    # clear only that exact link while core cancel checks every other backlink normally.
    target_field = (
        "stock_entry"
        if request.reconciliation_type == "Stock Entry Reversal"
        else "stock_reservation"
    )
    target_name = request.get(target_field)
    frappe.db.set_value(
        "Supply Reconciliation",
        request.name,
        target_field,
        None,
        update_modified=False,
    )
    packout_name = None
    if request.reconciliation_type == "Stock Entry Reversal":
        packout_name = target.get("lotus_packout_run")
        if packout_name and frappe.db.get_value("Packout Run", packout_name, "stock_entry") == target.name:
            frappe.db.set_value(
                "Packout Run",
                packout_name,
                "stock_entry",
                None,
                update_modified=False,
            )
    try:
        with command(target, action):
            target.cancel()
    finally:
        if packout_name:
            frappe.db.set_value(
                "Packout Run",
                packout_name,
                "stock_entry",
                target.name,
                update_modified=False,
            )
        frappe.db.set_value(
            "Supply Reconciliation",
            request.name,
            target_field,
            target_name,
            update_modified=False,
        )

    applied_at = now_datetime()
    frappe.db.set_value(
        "Supply Reconciliation",
        request.name,
        {
            "state": "Applied",
            "applied_by": frappe.session.user,
            "applied_at": applied_at,
        },
        update_modified=True,
    )
    return {
        "reconciliation": request.name,
        "state": "Applied",
        "target": target.name,
        "target_docstatus": target.docstatus,
    }
