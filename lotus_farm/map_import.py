"""Review-only bridge: Lotus Map PDF draft -> Frappe geometry revisions.

Never creates/changes Farm Block or Farm Plot master records, never approves geometry.
Import requires a private uploaded bundle, explicit acknowledgement, and manager role.
Missing masters or conflicting source mappings remain visible for manual review.
"""
import json

import frappe
from lotus_farm.controls import require_role, lock
from lotus_farm.map_bundle import MapBundleError, load_bundle
from lotus_farm.promax_rules import geometry


def _load(farm, file_url):
    require_role("Lotus Farm Manager")
    farm_doc = frappe.get_doc("Farm", farm)
    farm_doc.check_permission("read")
    if not file_url:
        frappe.throw("Tải tệp JSON xuất ra lên dưới dạng tệp riêng tư trước khi nhập.")
    file_names = frappe.get_all("File", filters={"file_url": file_url, "is_private": 1}, pluck="name")
    if not file_names:
        frappe.throw("Tệp JSON bản đồ phải được tải lên dưới dạng tệp riêng tư.")
    source_file = frappe.get_doc("File", file_names[0])
    source_file.check_permission("read")
    try:
        raw = source_file.get_content()
        bundle = load_bundle(raw.encode() if isinstance(raw, str) else raw)
    except (ValueError, UnicodeDecodeError, TypeError, KeyError, json.JSONDecodeError) as exc:
        frappe.throw("Gói bản đồ Lotus không hợp lệ: " + str(exc))
    return bundle


def _master_index(farm):
    blocks = frappe.get_list("Farm Block", filters={"farm": farm},
                             fields=["name", "block_code", "area_ha"], limit_page_length=10000)
    block_by_code = {}
    for block in blocks:
        if block.block_code in block_by_code:
            frappe.throw("Mã lô bị trùng, không xác định được: " + block.block_code)
        block_by_code[block.block_code] = block
    plots = frappe.get_list("Farm Plot", filters={"farm": farm},
                            fields=["name", "farm_block", "plot_code", "area_ha"], limit_page_length=20000)
    plot_by_parent_code = {}
    for plot in plots:
        key = (plot.farm_block, plot.plot_code)
        if key in plot_by_parent_code:
            frappe.throw("Mã thửa bị trùng trong lô: " + plot.plot_code)
        plot_by_parent_code[key] = plot
    return block_by_code, plot_by_parent_code


def _plan(farm, bundle):
    blocks, plots = _master_index(farm)
    block_rows, plot_rows = [], []
    missing_blocks, missing_plots, area_warnings = [], [], []
    for block in bundle["care_blocks"]:
        current = blocks.get(block["code"])
        if current is None:
            missing_blocks.append(block["code"])
            continue
        if abs(float(current.area_ha) - float(block["area_ha_pdf"])) > max(.02, .3 * block["area_ha_pdf"]):
            area_warnings.append(dict(kind="block", code=block["code"], erp_area=current.area_ha,
                                      pdf_area=block["area_ha_pdf"]))
            continue
        block_rows.append((current.name, block))
    for plot in bundle["irrigation_plots"]:
        if plot.get("parent_block") is None:
            continue
        parent = blocks.get(plot["parent_block"])
        if not parent:
            missing_plots.append(dict(plot=plot["code"], block=plot["parent_block"],
                                      reason="Care Block master does not exist"))
            continue
        current = plots.get((parent.name, plot["code"]))
        if not current:
            missing_plots.append(dict(plot=plot["code"], block=plot["parent_block"],
                                      reason="Farm Plot master does not exist in that Block"))
            continue
        if abs(float(current.area_ha) - float(plot["area_ha_pdf"])) > max(.02, .3 * plot["area_ha_pdf"]):
            area_warnings.append(dict(kind="plot", code=plot["code"], block=plot["parent_block"],
                                      erp_area=current.area_ha, pdf_area=plot["area_ha_pdf"]))
            continue
        plot_rows.append((current.name, plot))
    return dict(blocks=block_rows, plots=plot_rows, missing_blocks=missing_blocks,
                missing_plots=missing_plots, area_warnings=area_warnings)


def _version(doctype, field, name, shape):
    """Never overwrite an approved or prior draft geometry."""
    existing = frappe.get_all(doctype, filters={field: name}, fields=["name", "version", "geojson"],
                              order_by="version desc", limit_page_length=1000)
    canonical = json.dumps(shape, sort_keys=True, separators=(",", ":"))
    for old in existing:
        try:
            if json.dumps(json.loads(old.geojson), sort_keys=True, separators=(",", ":")) == canonical:
                return None
        except (TypeError, ValueError):
            pass
    return max((int(x.version) for x in existing), default=0) + 1


@frappe.whitelist()
def preview_map_bundle(farm, file_url):
    bundle = _load(farm, file_url)
    plan = _plan(farm, bundle)
    return dict(farm=farm, source=bundle["source_pdf"],
                status="UNVERIFIED_PDF_ALIGNMENT", will_auto_approve=False,
                care_blocks_in_source=64, irrigation_plots_in_source=205,
                ready_block_geometries=len(plan["blocks"]), ready_plot_geometries=len(plan["plots"]),
                missing_block_masters=plan["missing_blocks"], missing_plot_masters=plan["missing_plots"],
                area_conflicts=plan["area_warnings"], manual_mapping=bundle["manual_review"],
                estimated_boundary_plots=[
                    p["code"] for p in bundle["irrigation_plots"]
                    if p["boundary_method"] != "vector-enclosed"],
                note="Chỉ tạo ranh nháp cho mã đã khớp với Farm Block/Farm Plot đang có. Không tự gán E6 hoặc các thửa chia đôi.")


@frappe.whitelist(methods=["POST"])
def stage_map_bundle(farm, file_url, acknowledge_unverified=False):
    if acknowledge_unverified not in (True, 1, "1"):
        frappe.throw("Xác nhận UNVERIFIED_PDF_ALIGNMENT trước khi tạo hình học nháp.")
    bundle = _load(farm, file_url)
    plan = _plan(farm, bundle)
    lock("Farm", farm)
    created = {"Farm Block Geometry": [], "Plot Geometry": []}
    skipped = 0
    for doctype, ref_field, rows in (
        ("Farm Block Geometry", "farm_block", plan["blocks"]),
        ("Plot Geometry", "farm_plot", plan["plots"]),
    ):
        for ref_name, source in rows:
            # Validate shape again using the same WGS84 rules as approved geometry.
            shape = geometry(source["geometry"])
            version = _version(doctype, ref_field, ref_name, shape)
            if version is None:
                skipped += 1
                continue
            reason = ("DỰ THẢO từ bản PDF lô 222 ha; căn vệ tinh CHƯA kiểm tra GPS thực địa. "
                      "Không tự động duyệt. Mã nguồn: " + source["code"])
            if doctype == "Plot Geometry":
                reason += "; ranh: " + source["boundary_method"]
            doc = frappe.get_doc(dict(
                doctype=doctype, farm=farm, **{ref_field: ref_name},
                version=version, approval_state="Draft",
                geojson=json.dumps(shape, separators=(",", ":")), reason=reason))
            doc.check_permission("create")
            doc.insert()
            created[doctype].append(doc.name)
    return dict(status="drafts_created", farm=farm, created=created, already_present=skipped,
                unresolved=bundle["manual_review"],
                missing_block_masters=plan["missing_blocks"],
                missing_plot_masters=plan["missing_plots"],
                area_conflicts=plan["area_warnings"],
                approved_count=0)
