"""Guards of the masters the sổ lô relies on, on a site that has Vườn 222 set up with lines in its sổ lô. Colours and lô are
saved the way the Danh mục editor and Ctrl-K save them (console.save with every editable field, sent back as JSON: dates
as text). A used colour can be renamed or disabled but keeps its code, colour and days; a used lô keeps its code; a lô
nothing uses yet can still be recoded. Everything runs in one transaction and is rolled back.

docker exec -i lotus-vps-test-backend-1 bash -lc 'cd /home/frappe/frappe-bench/sites && ../env/bin/python -' < tests/integration/verify_master_guards.py
"""
import os

import frappe
from frappe.utils import add_days

SITE = os.environ.get("SITE", "frontend")
FARM = "LOTUS-222"
ENTRY = "Lotus Work Entry"

frappe.init(site=SITE)
frappe.connect()

from lotus_farm import console  # noqa: E402

failures = []


def check(label, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + label + (f" -> {detail}" if not ok and detail != "" else ""))
    if not ok:
        failures.append(label)


def refused(label, fn, text):
    """fn must fail with a message that contains text."""
    try:
        fn()
    except frappe.ValidationError as e:
        frappe.clear_messages()
        check(label, text in str(e), str(e))
    except Exception as e:
        check(label, False, repr(e))
    else:
        check(label, False, "no error")


def opened(doctype, name):
    """The record as the Danh mục editor loads it, and every editable field as it posts them back."""
    record = frappe.parse_json(frappe.as_json(console.detail(doctype, name)))
    editable = [f.fieldname for f in frappe.get_meta(doctype).fields
                if not f.read_only and f.fieldtype not in ("Section Break", "Column Break", "Tab Break", "HTML", "Button", "Table")]
    return record, {f: record.get(f) for f in editable}


def save(doctype, name, **changes):
    record, values = opened(doctype, name)
    return console.save(doctype, dict(values, **changes), name=name, base_modified=record["modified"])


try:
    frappe.set_user("Administrator")

    # ------------------------------------------------------------ màu dây
    tag = frappe.db.get_value(ENTRY, {"farm": FARM, "bunch_tag": ["is", "set"]}, "bunch_tag")
    check("the sổ lô has a line with a colour", bool(tag))
    name = frappe.db.get_value("Bunch Tag", tag, "display_name")
    out = save("Bunch Tag", tag, display_name=name + " (đổi tên)", enabled=0)
    check("a used colour saved again from Danh mục can be renamed and disabled",
          out["display_name"] == name + " (đổi tên)" and not out["enabled"], out)
    valid_to = frappe.db.get_value("Bunch Tag", tag, "valid_to")
    refused("a used colour keeps its days", lambda: save("Bunch Tag", tag, valid_to=str(add_days(valid_to, 1))),
            "Màu dây đã có dòng sổ lô")
    unused = frappe.db.sql(f"""select t.name from `tabBunch Tag` t where t.farm = %s and t.source_kind = 'Lotus Weekly'
                               and not exists (select 1 from `tab{ENTRY}` e where e.bunch_tag = t.name)
                               order by t.valid_from desc limit 1""", FARM)
    if unused:
        save("Bunch Tag", unused[0][0], color_label="Màu thử")
        check("a colour no line uses yet can still be corrected", frappe.db.get_value("Bunch Tag", unused[0][0], "color_label") == "Màu thử")

    # ------------------------------------------------------------ lô
    lot = frappe.db.get_value(ENTRY, {"farm": FARM, "state": "Confirmed"}, "farm_block")
    code = frappe.db.get_value("Farm Block", lot, "block_code")
    refused("a lô with lines in the sổ lô keeps its code", lambda: save("Farm Block", lot, block_code=code + "X"),
            "không được đổi vườn hoặc mã lô")
    save("Farm Block", lot, notes="Kiểm tra lưu lại")
    check("the same lô saved again with its own code goes through", frappe.db.get_value("Farm Block", lot, "notes") == "Kiểm tra lưu lại")
    fresh = frappe.get_doc(dict(doctype="Farm Block", farm=FARM, block_code="ZZ-KT", block_name="Lô thử ZZ", area_ha=1, active=1)).insert()
    save("Farm Block", fresh.name, block_code="ZZ-KT2")
    check("a lô nothing uses yet can still be recoded (every link to Farm Block is looked at)",
          frappe.db.get_value("Farm Block", fresh.name, "block_code") == "ZZ-KT2")
finally:
    frappe.set_user("Administrator")
    frappe.db.rollback()

print("\nALL PASSED" if not failures else f"\n{len(failures)} FAILED: " + "; ".join(failures))
