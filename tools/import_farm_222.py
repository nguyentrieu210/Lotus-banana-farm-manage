"""Run with the site's Python from bench/sites; dry run unless --commit.

Creates real Farm 222 masters from the Lotus Map bundle, with draft geometry.
Original PDF areas and unresolved ownership remain in a private source File.
"""
import argparse
import hashlib
import json
from decimal import Decimal, ROUND_DOWN
from pathlib import Path

import frappe


def run(args):
    from lotus_farm.map_bundle import load_bundle
    from lotus_farm.map_import import _version

    raw = Path(args.bundle).read_bytes()
    bundle = load_bundle(raw)
    farm_code = "LOTUS-222"
    if frappe.db.exists("File", {"attached_to_doctype":"Farm", "attached_to_name":farm_code,
            "file_name":["like", "farm-222-resolutions-%.json"]}):
        raise ValueError("Farm 222 now has owner-confirmed split codes. Use resolve_farm_222_parcels.py; the original PDF import must not overwrite resolved data.")
    if not frappe.db.exists("Company", args.company):
        raise ValueError("Company does not exist")
    marker = "Lotus Map / Farm 222 / " + hashlib.sha256(raw).hexdigest()
    created = dict(farm=0, blocks=0, plots=0, block_geometries=0, plot_geometries=0)
    adjustments = []
    farm = frappe.db.exists("Farm", {"farm_code": farm_code})
    if farm:
        doc = frappe.get_doc("Farm", farm)
        if doc.company != args.company or marker not in (doc.notes or ""):
            raise ValueError("Existing Farm 222 differs; refusing to change it")
    else:
        doc = frappe.get_doc(dict(doctype="Farm", farm_code=farm_code,
            farm_name="Farm 222 Thuận Phú", company=args.company, area_ha=222,
            location="Thuận Phú, Bình Phước", active=1,
            notes=marker + "\nNông trường 222 ha. Diện tích lô chăm sóc theo PDF: 215.16 ha. "
                "Ranh PDF căn tạm, chưa xác minh GPS. 5 mã thửa chờ xác nhận lô cha."))
        doc.insert()
        farm = doc.name
        created["farm"] += 1

    def geometry(doctype, field, name, source, reason, counter):
        version = _version(doctype, field, name, source["geometry"])
        if version is not None:
            frappe.get_doc(dict(doctype=doctype, farm=farm, **{field: name},
                version=version, approval_state="Draft",
                geojson=json.dumps(source["geometry"]), reason=reason)).insert()
            created[counter] += 1

    for block in bundle["care_blocks"]:
        code = block["code"]
        rows = [p for p in bundle["irrigation_plots"] if p["parent_block"] == code]
        total = sum((Decimal(str(p["area_ha_pdf"])) for p in rows), Decimal(0))
        capacity = Decimal(str(block["area_ha_pdf"]))
        scale = min(Decimal(1), capacity / total) if total else Decimal(1)
        notes = marker + "\nDiện tích PDF: " + str(capacity) + " ha. Mã tưới: " + ", ".join(block["irrigation_codes"])
        if scale < 1:
            notes += "\nTổng diện tích thửa nguồn " + str(total) + " ha vượt số lô làm tròn; " \
                "diện tích thửa dùng lập kế hoạch được giảm theo tỷ lệ, số nguồn lưu trong File riêng tư."
        name = frappe.db.exists("Farm Block", {"farm": farm, "block_code": code})
        if not name:
            d = frappe.get_doc(dict(doctype="Farm Block", farm=farm, block_code=code,
                block_name="Lô chăm sóc " + code, area_ha=float(capacity), active=1, notes=notes)).insert()
            name = d.name
            created["blocks"] += 1
        else:
            old = frappe.get_doc("Farm Block", name)
            if marker not in (old.notes or "") or abs(old.area_ha-float(capacity)) > 1e-6:
                raise ValueError("Conflicting block: " + code)
        geometry("Farm Block Geometry", "farm_block", name, block,
            "DỰ THẢO PDF Farm 222, chưa kiểm tra GPS. " + marker, "block_geometries")
        for p in rows:
            area = (Decimal(str(p["area_ha_pdf"])) * scale).quantize(Decimal(".000001"), rounding=ROUND_DOWN)
            if scale < 1:
                adjustments.append(dict(code=p["code"], block=code, source_area_ha=p["area_ha_pdf"], planning_area_ha=float(area)))
            plot = frappe.db.exists("Farm Plot", {"farm": farm, "farm_block": name, "plot_code": p["code"]})
            if not plot:
                d = frappe.get_doc(dict(doctype="Farm Plot", company=args.company, farm=farm,
                    farm_block=name, plot_code=p["code"], plot_name="Thửa tưới " + p["code"],
                    area_ha=float(area), active=1)).insert()
                plot = d.name
                created["plots"] += 1
            else:
                old = frappe.get_doc("Farm Plot", plot)
                if abs(old.area_ha-float(area)) > 1e-6:
                    raise ValueError("Conflicting plot: " + p["code"])
            geometry("Plot Geometry", "farm_plot", plot, p,
                "DỰ THẢO PDF, chưa kiểm tra GPS. Ranh: " + p["boundary_method"] +
                "; diện tích nguồn: " + str(p["area_ha_pdf"]) + "; diện tích kế hoạch: " + str(area) + ". " + marker,
                "plot_geometries")

    report = dict(farm=farm, company=args.company, created=created,
        counts={d:frappe.db.count(d, {"farm": farm}) for d in
            ("Farm Block", "Farm Plot", "Farm Block Geometry", "Plot Geometry")},
        farm_nominal_area_ha=222, care_area_ha_pdf=215.16,
        unresolved=bundle["manual_review"], area_adjustments=adjustments,
        status="committed" if args.commit else "dry_run_rolled_back")
    assert report["counts"]["Farm Block"] == 64
    assert report["counts"]["Farm Plot"] == 200
    assert not frappe.db.count("Plot Geometry", {"farm": farm, "approval_state": "Approved"})
    assert not frappe.db.count("Farm Block Geometry", {"farm": farm, "approval_state": "Approved"})
    from frappe.utils.file_manager import save_file
    for filename, content in (("farm-222-map-source.json", raw),
        ("farm-222-import-report.json", json.dumps(report, ensure_ascii=False).encode())):
        # Frappe can suffix the file stem with a content hash on save.
        if not frappe.db.exists("File", {"attached_to_doctype":"Farm", "attached_to_name":farm,
                "file_name":["like", filename.removesuffix(".json") + "%.json"]}):
            save_file(filename, content, "Farm", farm, is_private=1)
    Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
    if args.commit:
        frappe.db.commit()
    else:
        frappe.db.rollback()
    print(json.dumps(dict(farm=farm, created=created, counts=report["counts"],
        unresolved=[x["code"] for x in bundle["manual_review"]],
        adjusted_plots=len(adjustments), status=report["status"]), ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default="frontend")
    parser.add_argument("--company", required=True)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args()
    frappe.init(site=args.site)
    frappe.connect()
    frappe.set_user("Administrator")
    try:
        run(args)
    except Exception:
        frappe.db.rollback()
        raise
    finally:
        frappe.destroy()
