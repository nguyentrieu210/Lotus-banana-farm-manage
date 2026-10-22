"""Stage a vetted OneDrive banana-work catalog in Work Type without activating it.

Only adds inactive records; never touches active Lotus types, plans, payroll, or rates.
Run with bench Python from bench/sites. Without --commit the transaction rolls back.
"""
import argparse
import collections
import hashlib
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

import frappe

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
SOURCE_SHEET = "3. DM- HMCV"
PREFIX = "OD-"


def parse_master(path):
    with zipfile.ZipFile(path) as archive:
        strings = ["".join(t.text or "" for t in node.iter(NS + "t"))
                   for node in ET.fromstring(archive.read("xl/sharedStrings.xml")).findall(NS + "si")]
        root = ET.fromstring(archive.read("xl/worksheets/sheet8.xml"))
        stage_code = stage = section_code = section = ""
        records = []
        for row in root.findall(".//" + NS + "sheetData/" + NS + "row"):
            cells = {}
            for cell in row.findall(NS + "c"):
                col = re.match(r"[A-Z]+", cell.get("r")).group()
                val, inline = cell.find(NS + "v"), cell.find(NS + "is")
                if val is not None:
                    value = strings[int(val.text)] if cell.get("t") == "s" else val.text
                elif inline is not None:
                    value = "".join(t.text or "" for t in inline.iter(NS + "t"))
                else:
                    value = ""
                if value:
                    cells[col] = str(value).strip()
            if re.fullmatch(r"\d{4}", cells.get("C", "")) and cells.get("D"):
                stage_code, stage = cells["C"], cells["D"]
                section_code = section = ""
            if re.fullmatch(r"\d{2}", cells.get("E", "")) and cells.get("F"):
                section_code, section = stage_code + cells["E"], cells["F"]
            if re.fullmatch(r"\d{9}", cells.get("I", "")) and cells.get("H"):
                if not all((stage_code, section_code, stage, section)):
                    raise ValueError("Missing stage/section at row " + str(row.get("r")))
                records.append(dict(source_code=cells["I"], work_name=cells["H"],
                                    stage_code=stage_code, stage=stage,
                                    section_code=section_code, section=section,
                                    source_row=int(row.get("r"))))
        return records


def fold(value):
    return "".join(c for c in unicodedata.normalize("NFD", value.lower())
                   if not unicodedata.combining(c)).replace("đ", "d").strip()


def run(args):
    raw = open(args.source, "rb").read()
    tasks = parse_master(args.source)
    if len(tasks) != 136 or len({t["section_code"] for t in tasks}) != 33:
        raise ValueError("Unexpected OneDrive source counts")
    source_freq = collections.Counter(t["source_code"] for t in tasks)
    conflicts = [t for t in tasks if source_freq[t["source_code"]] > 1]
    if len(conflicts) != 2 or {t["work_name"] for t in conflicts} != {"Chống đổ ngã", "Phun búp"}:
        raise ValueError("Source code conflicts changed; review mapping")
    if not frappe.db.exists("UOM", {"uom_name": "Việc"}):
        frappe.get_doc({"doctype": "UOM", "uom_name": "Việc"}).insert()
    uom = frappe.db.get_value("UOM", {"uom_name": "Việc"}, "name")
    all_works = frappe.get_all("Work Type", fields=["name", "work_code", "work_name",
                "category", "uom", "active"], limit_page_length=0)
    old_names = collections.defaultdict(list)
    for row in all_works:
        if not str(row.work_code).startswith(PREFIX):
            old_names[fold(row.work_name)].append(row)
    created = {"categories": [], "works": []}
    aliases, codes, records = [], set(), []
    for task in tasks:
        category_code = PREFIX + task["section_code"]
        category_name = task["stage"] + " / " + task["section"]
        found = frappe.get_all("Work Category", filters={"category_code": category_code},
                               fields=["name", "category_name", "active"], limit_page_length=2)
        if len(found) > 1:
            raise ValueError("Repeated category " + category_code)
        if found:
            category = found[0].name
            if found[0].category_name != category_name:
                raise ValueError("Changed category name " + category_code)
        else:
            category = frappe.get_doc({"doctype": "Work Category",
                "category_code": category_code, "category_name": category_name,
                "active": 0}).insert().name
            created["categories"].append(category)
        code = task["source_code"]
        # Source row 140 carries 010502001 under section 03 (Phun búp).
        # Keep the source code in report; use a distinct local key by its actual section.
        corrected = code[:6] != task["section_code"]
        if corrected:
            if task["work_name"] != "Phun búp" or code != "010502001":
                raise ValueError("Unexpected code / section mismatch: " + str(task))
            code = "010503001"
        work_code = PREFIX + code
        if work_code in codes:
            raise ValueError("Local work code repeated: " + work_code)
        codes.add(work_code)
        alias_list = old_names.get(fold(task["work_name"]), [])
        if len(alias_list) > 1:
            raise ValueError("Ambiguous Lotus work name: " + task["work_name"])
        meta = dict(**task, proposed_local_code=work_code,
                    source_code_corrected=corrected)
        if alias_list:
            meta.update(status="mapped_existing_lotus", existing_work_type=alias_list[0].name,
                        existing_work_code=alias_list[0].work_code)
            aliases.append(meta)
        else:
            found = frappe.get_all("Work Type", filters={"work_code": work_code},
                                  fields=["name"], limit_page_length=2)
            if len(found) > 1:
                raise ValueError("Repeated Work Type " + work_code)
            if found:
                doc = frappe.get_doc("Work Type", found[0].name)
                if doc.work_name != task["work_name"] or doc.category != category:
                    raise ValueError("Changed staged Work Type " + work_code)
                meta.update(status="already_staged", work_type=doc.name)
            else:
                doc = frappe.get_doc({"doctype": "Work Type", "work_code": work_code,
                    "work_name": task["work_name"], "category": category,
                    "uom": uom, "active": 0, "allow_daywork": 0, "allow_piecework": 0,
                    "productivity_per_workday": 0, "piecework_rate": 0}).insert()
                created["works"].append(doc.name)
                meta.update(status="staged_inactive", work_type=doc.name)
        records.append(meta)
    report = {
        "source_name": "250903_HỆ THỐNG DANH MỤC_15H30.xlsx",
        "source_sheet": SOURCE_SHEET, "source_sha256": hashlib.sha256(raw).hexdigest(),
        "tasks_in_source": len(tasks), "sections": len({t["section_code"] for t in tasks}),
        "groups": dict(collections.Counter(t["stage"] for t in tasks)),
        "source_duplicate_codes": [dict(source_code=t["source_code"],
                      title=t["work_name"], source_row=t["source_row"]) for t in conflicts],
        "existing_lotus_aliases": aliases,
        "created_count": {k:len(v) for k,v in created.items()},
        "records": records,
        "status": "committed_as_inactive" if args.commit else "dry_run_rolled_back",
        "notes": "Catalog staged only. Unit 'Việc' is a placeholder; source has no UOM. "
                 "No work is selectable while inactive. No productivity/rates/payroll/plans changed."
    }
    with open(args.report, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    if args.commit:
        frappe.db.commit()
    else:
        frappe.db.rollback()
    print(json.dumps({k:report[k] for k in
            ("status","tasks_in_source","sections","created_count","existing_lotus_aliases")},
            ensure_ascii=False, default=str))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--site", default="frontend")
    parser.add_argument("--commit", action="store_true")
    options = parser.parse_args()
    frappe.init(site=options.site)
    frappe.connect()
    frappe.set_user("Administrator")
    try:
        run(options)
    except Exception:
        frappe.db.rollback()
        raise
    finally:
        frappe.destroy()
