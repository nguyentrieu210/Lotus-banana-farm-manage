"""Spec 002 (US3): Work Schedule Rule becomes the vòng chăm sóc: one việc every N days, for the farm or one khu, due
from the day the lô was last reported done. The old rules counted from a crop anchor (planting, selection, shooting,
cut bud) with offsets and material norms, which cannot be read as a cycle. They are written to a JSON file in the
site's private files, then deleted. Only rows with an old anchor are touched, so running it again changes nothing."""
import json
import os

import frappe
from frappe.utils import now_datetime

OLD_COLUMNS = ("anchor", "offset_days", "offset_months", "repeat_months", "quantity_basis", "norm_profile")


def execute():
    if not frappe.db.table_exists("Work Schedule Rule"):
        return
    columns = set(frappe.db.get_table_columns("Work Schedule Rule"))
    if "anchor" not in columns:
        return
    rows = frappe.db.sql("select * from `tabWork Schedule Rule` where ifnull(anchor, '') != ''", as_dict=True)
    if not rows:
        return
    folder = frappe.get_site_path("private", "files")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "work_schedule_rule_legacy_" + now_datetime().strftime("%Y%m%d%H%M%S") + ".json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=1, default=str)
    names = [r.name for r in rows]
    frappe.db.delete("Work Schedule Rule", {"name": ["in", names]})
    frappe.db.delete("Version", {"ref_doctype": "Work Schedule Rule", "docname": ["in", names]})
    print(f"Work Schedule Rule: {len(names)} luật lịch cũ đã lưu ở {path} rồi xóa.")
