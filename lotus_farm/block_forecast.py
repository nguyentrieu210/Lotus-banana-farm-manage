"""Public read-only forecast and separately-authorized DAILY draft planning.

Only Farm Block census, approved Plan Cohort, observed/estimated plant stages.
NO use of cut-mother journals, uploads or synthetic mother-cut dates.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import timedelta
import frappe
from lotus_farm.block_forecast_engine import forecast, date
from lotus_farm import plan_book2_reference as book2

SPRAY_CODES={"CV024","CV026","CV028","CV031"}
MATERIAL_CODES=SPRAY_CODES|{"CV030","CV032","CV033"}
REQUIRES_FIELD_SURVEY={"CV021"}
# work code / offset after injection / basis / readable note
INJECTION_WORK=(
    ("CV020",0,"bunches_shoot","Chích bắp: cần kiểm tra trổ ngoài vườn"),
    ("CV021",5,"bunches_shoot","Chống đổ: phải khảo sát cây cần chống thực tế"),
    ("CV022",7,"bunches_shoot","Vén lá, tỉa"),
    ("CV023",7,"bunches_shoot","Lặt hoa 1"),
    ("CV024",7,"bunches_shoot","Phun buồng 1"),
    ("CV025",10,"bunches_shoot","Lặt hoa 2"),
    ("CV026",10,"bunches_shoot","Phun buồng 2"),
    ("CV027",13,"bunches_shoot","Lặt hoa 3"),
    ("CV028",13,"bunches_shoot","Phun buồng 3"),
    ("CV029",16,"bunches_cut","Cắt bắp"),
    ("CV030",16,"bunches_cut","Cột dây màu"),
    ("CV031",16,"bunches_cut","Phun buồng 4"),
    ("CV032",16,"bunches_cut","Lót, chèn xốp"),
    ("CV033",16,"bunches_cut","Bao buồng"),
)
HARVEST_WORK=(
    ("CV034",-10,"bunches_harvest","Đo trái: cửa sổ thu -10 đến -7 ngày"),
    ("CV035",0,"bunches_harvest","Cắt/vác buồng: theo đo trái thực tế"),
    ("CV036",0,"bunches_harvest","Vận chuyển buồng"),
)

def _farm(farm, permission="read"):
    if not farm:
        frappe.throw("Chọn vườn.")
    doc=frappe.get_doc("Farm",farm)
    doc.check_permission(permission)
    return doc

def _sources(farm,zone=None,block=None):
    """All records are filtered through Frappe read permissions and farm scope."""
    _farm(farm)
    meta=frappe.get_meta("Farm Block")
    fields=["name","farm","block_code","block_name","farm_zone","area_ha","active","variety"]
    for optional in ("lotus_tree_count","lotus_estimated_flowering_date","lotus_estimation_basis"):
        if meta.has_field(optional):
            fields.append(optional)
    filters={"farm":farm,"active":1}
    if block:
        filters["name"]=block
    if zone:
        filters["farm_zone"]=zone
    blocks=frappe.get_list("Farm Block",filters=filters,fields=fields,limit_page_length=1000)
    names={b.name for b in blocks}
    co=[]
    if names and frappe.has_permission("Plan Cohort","read"):
        co=frappe.get_list("Plan Cohort",
            filters={"farm":farm,"approval_state":"Approved","farm_block":["in",list(names)]},
            fields=["name","farm_block","crop_cycle","cohort_code","cohort_name",
                    "anchor","anchor_date","quantity_basis","planned_qty",
                    "version","approval_state","modified"],limit_page_length=2000)
    cycle_names={c.crop_cycle for c in co if c.crop_cycle}
    cycles={}
    if cycle_names and frappe.has_permission("Crop Cycle","read"):
        cycles={c.name:c for c in frappe.get_list("Crop Cycle",
            filters={"name":["in",list(cycle_names)],"farm":farm},
            fields=["name","farm_block","cycle_no"],limit_page_length=2000)}
    for c in co:
        c["cycle_no"]=cycles[c.crop_cycle].cycle_no if c.crop_cycle in cycles else None
    return blocks,co

@frappe.whitelist()
def board(farm=None,zone=None,block=None):
    farms=frappe.get_list("Farm",fields=["name","farm_name"],limit_page_length=0)
    chosen=farm or (farms[0].name if farms else None)
    if not chosen:
        return dict(farms=[],farm=None,rows=[],months=[],warnings=["Không có vườn được cấp quyền."])
    blocks,cohorts=_sources(chosen,zone,block)
    result=forecast(blocks,cohorts)
    all_zones=frappe.get_list("Farm Block",filters={"farm":chosen,"active":1},
                              fields=["farm_zone"],limit_page_length=0)
    zones=sorted({b.farm_zone for b in all_zones if b.farm_zone})
    return dict(farms=farms,farm=chosen,zone=zone or "",block=block or "",
        zone_list=zones,blocks=blocks,cohorts=cohorts,rows=result["rows"],
        months=result["monthly"],warnings=result["warnings"],
        source_count=result["source_count"], rule=result["rule"],
        can_create=frappe.has_permission("Daily Work Plan","create"),
        params=dict(waves=[17,40,25,18],sucker_to_flower_months=6,
            flower_day_offset=14,flower_to_inject_days=5,
            inject_to_cut_days=16,cut_to_harvest_days=65,
            work_reference=book2.SOURCE))

def _work_events(waves,start,end):
    grouped={}
    for wave in waves:
        for code,off,basis,note,anchor in (
            [(a,b,c,d,"inject") for a,b,c,d in INJECTION_WORK]+
            [(a,b,c,d,"harvest") for a,b,c,d in HARVEST_WORK]):
            current=date(wave["inject_date"] if anchor=="inject" else wave["harvest_date"])+timedelta(days=off)
            if current<start or current>end:
                continue
            qty=int(wave[basis])
            if qty<1:continue
            key=(str(current),wave["farm_block"],code)
            if key not in grouped:
                grouped[key]=dict(date=str(current),farm_block=wave["farm_block"],
                    work_code=code,planned_qty=0,uom="Cây" if code=="CV021" else "Buồng",
                    note=note,sources=[],crop_cycle=wave.get("crop_cycle"),cohort=wave.get("cohort"))
            event=grouped[key]
            event["planned_qty"]+=qty
            event["sources"].append(wave["key"])
            if event["crop_cycle"]!=wave.get("crop_cycle"):event["crop_cycle"]=None
            if event["cohort"]!=wave.get("cohort"):event["cohort"]=None
    events=[]
    for (day,block,code),row in sorted(grouped.items()):
        row["sources"]=sorted(set(row["sources"]))
        row["schedule_key"]="BOOK2-"+hashlib.sha256("|".join([day,block,code]+row["sources"]).encode()).hexdigest()[:34]
        events.append(row)
    return events

def _preview(farm,from_date,to_date,block=None):
    first,last=date(from_date),date(to_date)
    if last<first or (last-first).days>45:
        frappe.throw("Chỉ xem tối đa 46 ngày.")
    blocks,cohorts=_sources(farm,block=block)
    projected=forecast(blocks,cohorts)
    events=_work_events(projected["rows"],first,last)
    works=frappe.get_list("Work Type",
        fields=["name","work_code","work_name","uom","active","allow_daywork",
                "productivity_per_workday"],
        filters={"active":1},limit_page_length=1000)
    workmap=defaultdict(list)
    for w in works:
        if w.work_code:workmap[w.work_code.strip().upper()].append(w)
    norms=frappe.get_list("Material Norm Profile",
        fields=["name","work_type","valid_from","valid_to","approval_state","version"],
        filters={"farm":farm,"approval_state":"Approved"},limit_page_length=1000) if frappe.has_permission("Material Norm Profile","read") else []
    materials=defaultdict(float)
    for e in events:
        matches=workmap.get(e["work_code"],[])
        w=matches[0] if len(matches)==1 else None
        issue=None
        if not w:issue="Mã công việc thiếu hoặc trùng trong ERP"
        elif not w.allow_daywork or float(w.productivity_per_workday or 0)<=0:issue="Chưa duyệt công nhật hoặc năng suất"
        elif str(w.uom).strip().casefold()!=e["uom"].casefold():issue="Đơn vị tính chưa khớp danh mục"
        if e["work_code"] in REQUIRES_FIELD_SURVEY:
            issue="Chống đổ cần số cây khảo sát thực tế; không giao theo dự thu"
        norm=None
        if w and not issue and e["work_code"] in MATERIAL_CODES:
            applicable=[n for n in norms if n.work_type==w.name and
                str(n.valid_from or "")<=e["date"] and (not n.valid_to or str(n.valid_to)>=e["date"])]
            norm=max(applicable,key=lambda r:int(r.version or 0)) if applicable else None
            if not norm:
                issue="Chưa có định mức vật tư được duyệt"
            else:
                p=frappe.get_doc("Material Norm Profile",norm.name)
                p.check_permission("read")
                if not p.lines:issue="Định mức vật tư chưa có dòng"
                else:
                    for line in p.lines:
                        if not all(float(v or 0)>0 for v in
                            (line.basis_qty,line.norm_qty,line.frequency,line.conversion_factor)):
                            issue="Định mức vật tư thiếu hệ số đã duyệt"
                            break
                    if not issue:
                        for line in p.lines:
                            amount=e["planned_qty"]*float(line.norm_qty)*float(line.frequency)*float(line.conversion_factor)/float(line.basis_qty)
                            materials[(e["date"],e["farm_block"],line.item,line.uom)]+=amount
        e.update(work_type=w.name if w else None,work_name=w.work_name if w else None,
            norm_profile=norm.name if norm else None,blocking_issue=issue,
            required_workdays=(round(e["planned_qty"]/float(w.productivity_per_workday),3)
                               if w and not issue else None))
    snapshot=dict(farm=farm,from_date=str(first),to_date=str(last),block=block,
        sources=[(c.get("name"),str(c.get("modified")),c.get("planned_qty"),c.get("anchor_date"))
                 for c in cohorts],
        blocks=[(b.get("name"),b.get("lotus_tree_count"),str(b.get("lotus_estimated_flowering_date"))) for b in blocks],
        events=[(e["schedule_key"],e["planned_qty"],e["work_type"],e["norm_profile"],e["blocking_issue"]) for e in events])
    fingerprint=hashlib.sha256(json.dumps(snapshot,sort_keys=True,default=str).encode()).hexdigest()
    return dict(rows=events,materials=[dict(date=k[0],farm_block=k[1],item=k[2],
        uom=k[3],quantity=round(v,5)) for k,v in sorted(materials.items())],
        warnings=projected["warnings"],fingerprint=fingerprint,
        ready_count=sum(not e["blocking_issue"] for e in events),
        total_count=len(events),source_count=projected["source_count"],
        from_date=str(first),to_date=str(last),block=block)

@frappe.whitelist()
def preview_care_plan(farm,from_date,to_date,block=None):
    return _preview(farm,from_date,to_date,block)

@frappe.whitelist(methods=["POST"])
def create_care_plan_draft(farm,block,posting_date,fingerprint):
    if not frappe.has_permission("Daily Work Plan","create"):
        frappe.throw("Không có quyền tạo kế hoạch nháp.",frappe.PermissionError)
    if not block:frappe.throw("Phải chọn lô lớn.")
    from lotus_farm.controls import lock
    lock("Farm",farm)
    day=str(date(posting_date))
    plan=_preview(farm,day,day,block)
    if fingerprint!=plan["fingerprint"]:
        frappe.throw("Dữ liệu lô/vụ/đợt vừa thay đổi. Tải lại lịch.")
    if not plan["rows"]:frappe.throw("Không có lịch chăm sóc cho ngày này.")
    blockers=[r["work_code"] for r in plan["rows"] if r["blocking_issue"]]
    if blockers:
        frappe.throw("Chưa đủ điều kiện giao việc: "+", ".join(sorted(set(blockers))))
    if len(plan["rows"])>100:frappe.throw("Quá nhiều việc trong ngày.")
    plans=frappe.get_list("Daily Work Plan",
        filters={"farm":farm,"posting_date":day,"docstatus":["<",2]},
        fields=["name"],limit_page_length=0)
    occupied=set()
    for p in plans:
        doc=frappe.get_doc("Daily Work Plan",p.name)
        doc.check_permission("read")
        occupied.update((line.farm_block,line.work_type) for line in doc.lines)
    lines=[]
    for row in plan["rows"]:
        if (block,row["work_type"]) in occupied:
            frappe.throw("Đã có kế hoạch ngày/lô/công việc: "+row["work_code"])
        lines.append(dict(farm_block=block,work_type=row["work_type"],
            planned_qty=row["planned_qty"],payment_mode="Daywork",
            norm_profile=row["norm_profile"],schedule_key=row["schedule_key"],
            lotus_forecast_sources=json.dumps(
                dict(source="Farm Block / Plan Cohort",waves=row["sources"],
                     crop_cycle=row["crop_cycle"],cohort=row["cohort"]),
                ensure_ascii=False),execution_state="Planned"))
    company=frappe.db.get_value("Farm",farm,"company")
    doc=frappe.get_doc(dict(doctype="Daily Work Plan",farm=farm,company=company,
        posting_date=day,lines=lines))
    doc.insert() # docstatus=0 only; never submit or issue material.
    return dict(plan=doc.name,docstatus=doc.docstatus,lines=len(lines))
