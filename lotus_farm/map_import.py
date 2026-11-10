"""Review-only bridge: Lotus Map PDF draft -> Frappe geometry revisions of the lô.

Never creates/changes Farm Block master records, never approves geometry.
Import requires a private uploaded bundle, explicit acknowledgement, and manager role.
Missing masters or conflicting areas remain visible for manual review.
"""
import json

import frappe
from lotus_farm.controls import require_role, lock
from lotus_farm.map_bundle import load_bundle
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
    return block_by_code


def _plan(farm, bundle):
    blocks = _master_index(farm)
    block_rows, missing_blocks, area_warnings = [], [], []
    for block in bundle["care_blocks"]:
        current = blocks.get(block["code"])
        if current is None:
            missing_blocks.append(block["code"])
            continue
        if abs(float(current.area_ha) - float(block["area_ha_pdf"])) > max(.02, .3 * block["area_ha_pdf"]):
            area_warnings.append(dict(code=block["code"], erp_area=current.area_ha, pdf_area=block["area_ha_pdf"]))
            continue
        block_rows.append((current.name, block))
    return dict(blocks=block_rows, missing_blocks=missing_blocks, area_warnings=area_warnings)


def _version(block, shape):
    """Never overwrite an approved or prior draft geometry."""
    existing = frappe.get_all("Farm Block Geometry", filters={"farm_block": block}, fields=["name", "version", "geojson"],
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
                care_blocks_in_source=len(bundle["care_blocks"]),
                ready_block_geometries=len(plan["blocks"]),
                missing_block_masters=plan["missing_blocks"],
                area_conflicts=plan["area_warnings"],
                note="Chỉ tạo ranh nháp cho mã lô đã khớp với Farm Block đang có.")


@frappe.whitelist(methods=["POST"])
def stage_map_bundle(farm, file_url, acknowledge_unverified=False):
    if acknowledge_unverified not in (True, 1, "1"):
        frappe.throw("Xác nhận UNVERIFIED_PDF_ALIGNMENT trước khi tạo hình học nháp.")
    bundle = _load(farm, file_url)
    plan = _plan(farm, bundle)
    lock("Farm", farm)
    created = []
    skipped = 0
    for block, source in plan["blocks"]:
        # Validate shape again using the same WGS84 rules as approved geometry.
        shape = geometry(source["geometry"])
        version = _version(block, shape)
        if version is None:
            skipped += 1
            continue
        doc = frappe.get_doc(dict(
            doctype="Farm Block Geometry", farm=farm, farm_block=block,
            version=version, approval_state="Draft",
            geojson=json.dumps(shape, separators=(",", ":")),
            reason=("DỰ THẢO từ bản PDF lô 222 ha; căn vệ tinh CHƯA kiểm tra GPS thực địa. "
                    "Không tự động duyệt. Mã nguồn: " + source["code"])))
        doc.check_permission("create")
        doc.insert()
        created.append(doc.name)
    return dict(status="drafts_created", farm=farm, created=created, already_present=skipped,
                missing_block_masters=plan["missing_blocks"],
                area_conflicts=plan["area_warnings"],
                approved_count=0)
