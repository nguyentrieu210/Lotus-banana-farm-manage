"""Rolling 36-month LIVE planning outlook for actual Lotus 222 VIP 126 census.

Observed milestones supersede older ones. A new selected sucker or observed
flowering updates the first predicted harvest and ALL subsequent ratoon dates.
The observed history is never edited, and these scenario forecasts are never
released stock. All rates/weights are unvalidated scenario assumptions.
"""
from datetime import timedelta
from collections import defaultdict
import frappe
from frappe.utils import getdate, add_months, flt, nowdate
from lotus_farm.reporting import records
from lotus_farm.scoping import land_scope, land_filters
from lotus_farm.vip126_live import VARIETY, FARM

SCENARIOS = {
    "low": {
        "name": "Thấp", "flower_share": .30, "survival": .85,
        "weight_kg": 16., "quality": .80, "packout": .70,
        "flower_to_harvest": 87, "flower_to_cut": 17, "plant_to_flower": 285,
        "sucker_to_harvest": 285, "cut_to_harvest": 70, "ratoon_days": 310,
    },
    "base": {
        "name": "Cơ sở", "flower_share": .60, "survival": .90,
        "weight_kg": 20., "quality": .85, "packout": .75,
        "flower_to_harvest": 82, "flower_to_cut": 17, "plant_to_flower": 255,
        "sucker_to_harvest": 245, "cut_to_harvest": 65, "ratoon_days": 270,
    },
    "high": {
        "name": "Cao", "flower_share": .85, "survival": .95,
        "weight_kg": 24., "quality": .90, "packout": .80,
        "flower_to_harvest": 77, "flower_to_cut": 17, "plant_to_flower": 240,
        "sucker_to_harvest": 215, "cut_to_harvest": 60, "ratoon_days": 240,
    },
}
CREDITS = (
    "Ngày trổ khu A dự kiến 01/11/2026 do người dùng cung cấp; "
    "thời gian trổ đến thu tham khảo FAO 10–14 tuần: "
    "https://www.fao.org/4/ad523e/ad523e05.htm . "
    "Tất cả tỷ lệ cây cùng trổ, kg/buồng, QC, đóng gói, ngày chọn chồi đến thu "
    "mốc trổ đến cắt bắp 17 ngày, cắt bắp đến thu 60–70 ngày do quản lý nhập ngày 18/10/2026. "
    "Tổng 77–87 ngày, cơ sở 82 ngày. Số ngày chưa hiệu chuẩn theo kết quả vườn. "
    "Các hệ số khác và khoảng cách vụ chồi vẫn chưa hiệu chuẩn."
)


def _validate_milestones():
    """Every scenario must be cut at day 17, then harvest 60–70 days later."""
    for config in SCENARIOS.values():
        if config["flower_to_cut"] != 17 or not 60 <= config["cut_to_harvest"] <= 70:
            raise ValueError("Invalid VIP 126 bud-cut to harvest schedule")
        if config["flower_to_harvest"] != config["flower_to_cut"] + config["cut_to_harvest"]:
            raise ValueError("Flower-to-harvest does not equal 17 + cut-to-harvest")


_validate_milestones()


def _month_end(start):
    return getdate(add_months(start, 36))-timedelta(days=1)


def _monthbins(start):
    return {str(add_months(start, i))[:7]: {
        "month": str(add_months(start, i))[:7], "bunches": 0,
        "gross_kg": 0, "packed_kg": 0, "actual_gross_kg": 0,
    } for i in range(36)}


def _event_candidates(blocks, config, from_date, to_date):
    """Only permission-readable observations. Unknown cohorts are not summed."""
    permitted = {b.name for b in blocks}
    anchors = defaultdict(list)
    scopes = {"farm": FARM}
    if frappe.has_permission("Bunch Operation", "read"):
        meta = frappe.get_meta("Bunch Operation")
        operations = records("Bunch Operation", {
            **land_filters(meta, scopes), "docstatus": 1,
            "operation_type": ["in", ["Shooting", "Cut Bud"]],
        }, ["name", "farm_block", "crop_cycle", "sucker_selection_batch",
            "operation_date", "operation_type", "net_bunch_qty", "expected_harvest_date"])
        for r in operations:
            if r.farm_block not in permitted or not r.operation_date:
                continue
            source = "cut" if r.operation_type == "Cut Bud" else "shoot"
            predicted = (getdate(r.expected_harvest_date) if r.expected_harvest_date and source=="cut"
                else getdate(r.operation_date)+timedelta(days=config[
                    "cut_to_harvest" if source=="cut" else "flower_to_harvest"]))
            anchors[r.farm_block].append({
                "priority": 4 if source == "cut" else 3,
                "source": source, "source_name": "Đã cắt bắp" if source == "cut" else "Đã trổ",
                "source_date": str(r.operation_date), "harvest_date": predicted,
                "bunches": max(flt(r.net_bunch_qty),0), "observed": True,
                "batch": r.sucker_selection_batch or None,
                "cycle": r.crop_cycle or None,
            })
    if frappe.has_permission("Sucker Selection Batch", "read"):
        meta = frappe.get_meta("Sucker Selection Batch")
        batches = records("Sucker Selection Batch", land_filters(meta, scopes),
                         ["name", "farm_block", "crop_cycle", "selection_date",
                          "selected_sucker_qty", "expected_productive_qty"])
        for r in batches:
            if r.farm_block not in permitted or not r.selection_date:
                continue
            amount = flt(r.expected_productive_qty) or flt(r.selected_sucker_qty)
            anchors[r.farm_block].append({
                "priority": 2, "source": "sucker", "source_name": "Đã chọn chồi",
                "source_date": str(r.selection_date),
                "harvest_date": getdate(r.selection_date)+timedelta(days=config["sucker_to_harvest"]),
                "bunches": max(amount, 0), "observed": True,
                "batch": r.name, "cycle": r.crop_cycle or None,
            })
    if frappe.has_permission("Harvest Actual", "read"):
        actuals = records("Harvest Actual", {
            **land_filters(frappe.get_meta("Harvest Actual"), scopes), "docstatus": 1,
        }, ["name", "farm_block", "crop_cycle", "sucker_selection_batch",
            "harvest_date", "harvested_bunch_qty", "gross_weight_kg"])
        for r in actuals:
            if r.farm_block not in permitted or not r.harvest_date:
                continue
            anchors[r.farm_block].append({
                "priority": 5, "source": "harvest_actual",
                "source_name": "Đã thu hoạch (thực tế)",
                "source_date": str(r.harvest_date), "harvest_date": getdate(r.harvest_date),
                "bunches": max(flt(r.harvested_bunch_qty), 0), "observed": True,
                "batch": r.sucker_selection_batch or None, "cycle": r.crop_cycle or None,
            })
    return anchors


def _pick_anchor(block, events, config):
    """Most advanced *observed* stage wins over inferred timeline.

    Do not aggregate multiple partially linked events (could double count).
    A later dated event at the same priority becomes the anchor.
    """
    positive = [r for r in events if r["bunches"] > 0]
    if positive:
        return max(positive, key=lambda r: (r["source_date"], r["priority"], str(r["batch"] or "")))
    count = int(block.get("lotus_tree_count") or 0)
    if count <= 0:
        return None
    estimated = block.get("lotus_estimated_flowering_date")
    if estimated:
        return {
            "priority": 1, "source": "estimated_flower",
            "source_name": "Ngày trổ dự kiến (khu A)",
            "source_date": str(estimated),
            "harvest_date": getdate(estimated)+timedelta(days=config["flower_to_harvest"]),
            "bunches": count*config["flower_share"], "observed": False,
            "batch": None, "cycle": None,
        }
    planting = block.get("planting_date")
    if planting:
        return {
            "priority": 1, "source": "plant",
            "source_name": "Ngày trồng thực tế",
            "source_date": str(planting),
            "harvest_date": getdate(planting)+timedelta(
                days=config["plant_to_flower"]+config["flower_to_harvest"]),
            "bunches": count*config["flower_share"], "observed": False,
            "batch": None, "cycle": None,
        }
    return None


def _year_rows(block, anchor, config, start, end):
    output = []
    # Project future cycles using the latest active anchor, NEVER from the
    # original planting date when later observations are available.
    # An actual harvest is historical; only its following ratoons are forecasts.
    for i in range(1 if anchor["source"]=="harvest_actual" else 0, 16):
        expected = anchor["harvest_date"]+timedelta(days=i*config["ratoon_days"])
        if expected>end:
            break
        if expected<start:
            continue
        bunches=round(anchor["bunches"]*config["survival"])
        gross=round(bunches*config["weight_kg"],2)
        packed=round(gross*config["quality"]*config["packout"],2)
        output.append({
            "farm": block.farm, "block": block.name,
            "block_code": block.block_code, "zone": block.block_code[0],
            "variety": block.variety,
            "cycle_no": i+1, "source": anchor["source"] if i==0 else "future",
            "source_label": anchor["source_name"] if i==0 else "Vụ chồi sau mốc mới",
            "source_date": anchor["source_date"], "expected_date":str(expected),
            "month":str(expected)[:7], "bunches":bunches,
            "gross_kg":gross,"packed_kg":packed,
            "confidence":"Thấp" if i==0 and not anchor["observed"] else
                         ("Trung bình" if i==0 else "Dự phóng"),
            "projected":True,"approved":False,"commit_ready":False,
            "assumed_rates":True,
            "anchor_stage":anchor["source"],"anchor_harvest_date":str(anchor["harvest_date"]),
        })
    return output


@frappe.whitelist()
def calendar(farm=None, zone=None, block=None, scenario="base", from_date=None):
    if scenario not in SCENARIOS:
        frappe.throw("Kịch bản không hợp lệ.")
    if zone and zone not in ("A","B","C","D","E"):
        frappe.throw("Khu không hợp lệ; chọn A, B, C, D hoặc E.")
    if farm and farm!=FARM:
        return {"available":False,"note":"Bản dự phóng VIP 126 hiện dành cho Vườn 222."}
    if not frappe.has_permission("Harvest Forecast","read"):
        frappe.throw("Không có quyền đọc dự thu.",frappe.PermissionError)
    selected=land_scope(farm=FARM,block=block)
    config=SCENARIOS[scenario]
    start=getdate(from_date or nowdate()).replace(day=1)
    end=_month_end(start)
    meta=frappe.get_meta("Farm Block")
    fields=["name","farm","block_code","block_name","variety",
            "planting_date","lotus_tree_count","lotus_estimated_flowering_date",
            "lotus_inferred_planting_date"]
    blocks=records("Farm Block",land_filters(meta,selected),fields)
    blocks=[b for b in blocks if b.farm==FARM and b.variety==VARIETY and (
        not zone or (b.block_code or "").startswith(zone))]
    anchors=_event_candidates(blocks,config,start,end)
    issues=[]
    rows=[]
    monthbins=_monthbins(start)
    for b in blocks:
        candidates=anchors.get(b.name,[])
        top_candidates=[c for c in candidates if c["bunches"]>0]
        if len(top_candidates)>1:
            issues.append({"block_code":b.block_code,"reason":"Có nhiều đợt quan sát, chỉ lấy mốc ưu tiên cao nhất để tránh cộng trùng. Cần gắn đợt chồi."})
        anchor=_pick_anchor(b,candidates,config)
        if not anchor:
            issues.append({"block_code":b.block_code,"reason":"Chưa đủ số cây và mốc sinh trưởng để tính 36 tháng."})
            continue
        if int(b.get("lotus_tree_count") or 0)<=0 and not anchor["observed"]:
            issues.append({"block_code":b.block_code,"reason":"Chưa có số cây trong bảng kiểm kê."})
            continue
        for row in _year_rows(b,anchor,config,start,end):
            rows.append(row)
            bin=monthbins[row["month"]]
            for col in ("bunches","gross_kg","packed_kg"):
                bin[col]+=row[col]
    rows.sort(key=lambda r:(r["expected_date"],r["block_code"],r["cycle_no"]))
    return {
        "available":True,"status":"LIVE_DRAFT_SCENARIO","farm":FARM,
        "zone":zone or "ALL","scenario":scenario,"scenario_name":config["name"],
        "from_date":str(start),"to_date":str(end),
        "config":config,
        "config_status":"Chưa hiệu chuẩn – KHÔNG là bộ hệ số Approved",
        "source_notice":CREDITS,
        "rows":rows,"months":list(monthbins.values()),
        "issues":issues,
        "summary":{
            "total_lots":len(blocks),
            "projected_lots":len({r["block"] for r in rows}),
            "missing_lots":len({x["block_code"] for x in issues if x["reason"].startswith("Chưa đủ")}),
            "gross_kg":round(sum(r["gross_kg"] for r in rows),2),
            "packed_kg":round(sum(r["packed_kg"] for r in rows),2),
            "bunches":sum(r["bunches"] for r in rows),
            "releasable_kg":0,
        },
        "note":"Dự phóng vận hành từ số cây thật và mốc dự kiến; mọi hệ số sản lượng chưa đo thực tế. Mốc mới sẽ thay đổi toàn bộ các kỳ chồi tiếp theo. Không phải sản lượng đã duyệt hoặc cam kết."
    }