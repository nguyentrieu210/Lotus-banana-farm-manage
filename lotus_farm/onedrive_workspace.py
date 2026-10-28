"""Source-backed Lotus process adoption, handover and planning workspace.

Source references are versioned. Zone history never creates lot actuals, stock
or released supply. All reads and writes obey the existing farm permissions.
"""
import hashlib
import gzip
import json
from collections import defaultdict
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

import frappe
from frappe.model.document import Document
from frappe.utils import cint, getdate, nowdate
from lotus_farm.controls import check_farm, command, command_allowed, lock, require_role
from lotus_farm.scoping import land_scope, land_filters
from lotus_farm.onedrive_protocol import (
    PROCESS_STEPS, SELECTION_SOURCE, color_periods, forecast_quantities,
    harvest_curve, parse_handover_workbook, selection_schedule,
    window_months, source_balance,
)

PARAMETERS = ("density", "cut_rate", "harvest_rate", "processed_rate", "gross_bunch_kg", "processed_bunch_kg")
LIBRARY_PATH = Path(__file__).parent / "data" / "onedrive_protocol_v1.json"


@lru_cache(maxsize=1)
def library():
    data = LIBRARY_PATH.read_bytes()
    return json.loads(data), hashlib.sha256(data).hexdigest()


@lru_cache(maxsize=1)
def _reference_library():
    return json.loads(gzip.decompress((LIBRARY_PATH.parent/'onedrive_reference_v1.json.gz').read_bytes()))


@frappe.whitelist()
def reference_table(table, start=0, length=100, search=None):
    require_role('Lotus Farm Manager','Lotus Auditor','Lotus Sales Planner','Lotus Integration User')
    source=_reference_library()
    if table not in source:frappe.throw('Bảng tham chiếu không được hỗ trợ.')
    rows=source[table]
    if search:
        query=str(search).casefold()[:200]
        rows=[r for r in rows if query in ' '.join(str(v) for v in r.values()).casefold()]
    start=max(cint(start),0);length=min(max(cint(length),1),200)
    return dict(rows=rows[start:start+length],total=len(rows),start=start,has_more=len(rows)>start+length,
                columns=list(source[table][0]) if source[table] else [],reference_only=True)


def _farm(name, permission="read"):
    doc = frappe.get_doc("Farm", name)
    doc.check_permission("read")
    if permission != "read" and not frappe.has_permission("Lotus Process Adoption", permission):
        frappe.throw("Không có quyền cấu hình quy trình.", frappe.PermissionError)
    return doc


def _rows(doctype, fields, filters=None, limit=10000):
    if not frappe.has_permission(doctype, "read"):
        return []
    return frappe.get_list(doctype, fields=fields, filters=filters or {}, limit_page_length=limit, order_by="name asc")


class HandoverCohort(Document):
    def validate(self):
        check_farm(self)
        before = self.get_doc_before_save()
        immutable = ("farm", "farm_zone", "cohort_key", "source_family", "source_event_date",
                     "equivalent_selection_date", "source_cut_qty", "source_attachment", "source_sha256", "source_cells")
        if self.is_new() and not command_allowed(self, "handover_import"):
            frappe.throw("Nhập đợt bàn giao qua chức năng đối soát nhật ký.")
        if before and any(self.get(k) != before.get(k) for k in immutable):
            frappe.throw("Lịch sử bàn giao đã đối soát không được sửa; giữ nguyên chứng cứ nguồn.")
        if cint(self.source_cut_qty) <= 0:
            frappe.throw("Số cây cũ đã chặt phải dương.")
        if getdate(self.source_event_date) > getdate(nowdate()):
            frappe.throw("Ngày bàn giao thực tế không thể ở tương lai.")
        self.equivalent_selection_date = self.source_event_date

    def on_trash(self):
        frappe.throw("Không được xóa lịch sử bàn giao đã đối soát.")


class ProcessAdoption(Document):
    def validate(self):
        check_farm(self)
        require_role("Lotus Farm Manager")
        data, digest = library()
        before = self.get_doc_before_save()
        if before and before.approval_state == "Approved":
            if any(before.get(f.fieldname) != self.get(f.fieldname) for f in self.meta.fields
                   if not (f.fieldname == 'valid_to' and command_allowed(self,'retire_process'))):
                frappe.throw("Phiên bản đã duyệt được giữ nguyên. Tạo phiên bản mới.")
            if self.valid_to and getdate(self.valid_to)<getdate(self.valid_from):
                frappe.throw('Hiệu lực kết thúc trước ngày bắt đầu.')
            # Never recalculate an approved version from a newer source library.
            return
        if cint(self.version) < 1:
            frappe.throw("Phiên bản phải dương.")
        if frappe.db.exists(self.doctype, {"farm": self.farm, "version": self.version, "name": ["!=", self.name]}):
            frappe.throw("Vườn đã có phiên bản này.")
        preset = next((r for r in data["defaults"] if r["key"] == self.preset_key), None)
        if not preset:
            frappe.throw("Chọn bộ hệ số có trong thư viện OneDrive.")
        self.source_version, self.source_hash = data["version"], digest
        self.source_label = f"{preset['enterprise']} / {preset['source_farm']} / năm {preset['year_band']} / tsSXKD dòng {preset['source_row']}"
        for key in PARAMETERS:
            self.set(key, preset[key])
        if self.condition_class:
            override = next((r for r in data["conditions"] if r["condition"] == self.condition_class and r["year_band"] == preset["year_band"]), None)
            if not override:
                frappe.throw("Thiếu hệ số đánh giá cho năm vụ này.")
            for key in PARAMETERS[:4]:
                self.set(key, override[key])
        forecast_quantities(1, self.as_dict())
        if self.valid_to and getdate(self.valid_to) < getdate(self.valid_from):
            frappe.throw("Hiệu lực kết thúc trước ngày bắt đầu.")
        if self.color_anchor_code not in [r["code"] for r in data["colors"]] or not 1 <= cint(self.color_period_days) <= 31:
            frappe.throw("Mốc hoặc số ngày màu dây không hợp lệ.")
        # An approved version cannot overlap another approved interval.
        if self.approval_state == "Approved":
            for other in frappe.get_all(self.doctype, filters={"farm": self.farm, "approval_state": "Approved", "name": ["!=", self.name]}, fields=["valid_from", "valid_to"]):
                if getdate(self.valid_from) <= getdate(other.valid_to or "9999-12-31") and getdate(other.valid_from) <= getdate(self.valid_to or "9999-12-31"):
                    frappe.throw("Khoảng hiệu lực trùng phiên bản quy trình đã duyệt.")

    def on_trash(self):
        if self.approval_state == "Approved":
            frappe.throw("Không được xóa phiên bản đã duyệt.")


def validate_handover_link(doc, method=None):
    if not doc.get("handover_cohort"):
        return
    source = frappe.get_doc("Lotus Handover Cohort", doc.handover_cohort)
    source.check_permission("read")
    block = frappe.get_doc("Farm Block", doc.farm_block)
    block.check_permission("read")
    if doc.farm != source.farm or block.farm != source.farm or block.farm_zone != source.farm_zone:
        frappe.throw("Lô của vụ mới phải thuộc đúng vườn và khu bàn giao tham chiếu.")
    when = doc.get("selection_date") or doc.get("anchor_date")
    if when and getdate(when) < getdate(source.source_event_date):
        frappe.throw("Mốc vụ mới không thể trước đợt bàn giao tham chiếu.")
    # This link documents context, not an allocation of the old cut count.


def _handover_preview(farm, file_url):
    _farm(farm)
    from lotus_farm.importing import file_bytes
    try:
        result = parse_handover_workbook(file_bytes(file_url))
    except (ValueError, KeyError) as exc:
        frappe.throw(str(exc))
    zones = set(frappe.get_list("Farm Block", filters={"farm": farm}, pluck="farm_zone", limit_page_length=10000))
    if any(zone not in zones for zone in result["zone_totals"]):
        frappe.throw("Nhật ký có khu chưa được khai báo tại vườn đã chọn.")
    result.update(new_count=0, existing_count=0, conflicts=[])
    for row in result["rows"]:
        row["cohort_key"] = hashlib.sha256(f"{farm}|first-cut-journal|{row['farm_zone']}|{row['source_event_date']}".encode()).hexdigest()
        existing = frappe.db.get_value("Lotus Handover Cohort", {"cohort_key": row["cohort_key"]}, ["name", "source_cut_qty"], as_dict=True)
        if existing:
            if cint(existing.source_cut_qty) != row["source_cut_qty"]:
                result["conflicts"].append({"name": existing.name, "farm_zone": row["farm_zone"], "date": row["source_event_date"], "stored_qty": existing.source_cut_qty, "file_qty": row["source_cut_qty"]})
            result["existing_count"] += 1
        else:
            result["new_count"] += 1
    return result


@frappe.whitelist()
def preview_handover(farm, file_url):
    require_role("Lotus Farm Manager", "Lotus Integration User")
    return _handover_preview(farm, file_url)


@frappe.whitelist(methods=["POST"])
def import_handover(farm, file_url, source_sha256):
    require_role("Lotus Farm Manager", "Lotus Integration User")
    _farm(farm)
    if not frappe.has_permission("Lotus Handover Cohort", "create"):
        frappe.throw("Không có quyền nhập bàn giao.", frappe.PermissionError)
    lock("Farm", farm)  # Serialize file retries and overlapping daily journals.
    result = _handover_preview(farm, file_url)
    if source_sha256 != result["source_sha256"]:
        frappe.throw("File đã đổi sau khi xem trước. Hãy đối soát lại.")
    if result["conflicts"]:
        frappe.throw("Số cây theo ngày khác lịch sử đã nhập. Dừng nhập để kiểm tra bản nguồn.")
    created = []
    for row in result["rows"]:
        if frappe.db.exists("Lotus Handover Cohort", {"cohort_key": row["cohort_key"]}):
            continue
        values = {key: row[key] for key in ("farm_zone", "cohort_key", "source_event_date", "equivalent_selection_date", "source_cut_qty", "source_sha256")}
        doc = frappe.get_doc(dict(doctype="Lotus Handover Cohort", farm=farm, source_family="first-cut-journal", source_attachment=file_url,
                                  source_cells=json.dumps(row["source_cells"], ensure_ascii=False), **values))
        with command(doc, "handover_import"):
            doc.insert()
        created.append(doc.name)
    return {"created": len(created), "existing": result["existing_count"], "total_cut_qty": result["total_cut_qty"], "zone_totals": result["zone_totals"], "warnings": result["warnings"]}


def _active(adoptions, farm, on_date):
    return next((r for r in adoptions if r.farm == farm and r.approval_state == "Approved" and getdate(r.valid_from) <= getdate(on_date)
                 and (not r.valid_to or getdate(r.valid_to) >= getdate(on_date))), None)


GRADE_FIELDS=('tl_A456','tl_A789','tl_B456','tl_B789','tl_CL','tl_CP','tl_CNB13','tl_CNB18')


def _grade_quantities(params, month, processed_kg):
    data,_=library()
    preset=next((p for p in data['defaults'] if p['key']==params.preset_key),None)
    if not preset:return {}
    matches=[r for r in _reference_library()['tsPC_C'] if r['Nông trường']==preset['source_farm']
             and str(r['Năm'])==month[:4] and cint(r['Tháng'])==int(month[5:7])]
    if len(matches)!=1:return {}
    shares=[float(matches[0].get(key) or 0) for key in GRADE_FIELDS]
    if abs(sum(shares)-1)>1e-7 or any(v<0 or v>1 for v in shares):return {}
    return {key.replace('tl_','grade_')+'_kg':round(processed_kg*share,3) for key,share in zip(GRADE_FIELDS,shares)}


@frappe.whitelist()
def board(company=None, farm=None, zone=None, block=None, cycle=None, from_date=None):
    if not frappe.has_permission("Lotus Handover Cohort", "read"):
        frappe.throw("Không có quyền xem quy trình.", frappe.PermissionError)
    scope = land_scope(company=company, farm=farm, zone=zone, block=block, cycle=cycle)
    data, digest = library()
    start = getdate(from_date or nowdate()).replace(day=1)
    end = getdate(selection_schedule(start, basis="Planting", count=6)[-1]["selection_date"]) - timedelta(days=1)
    farm_filters = {"company": company} if company else {}
    if scope.get("farm"):
        farm_filters["name"] = scope["farm"]
    farms = _rows("Farm", ["name", "farm_name"], farm_filters, 1000)
    farm_names = [r.name for r in farms]
    base = {"farm": ["in", farm_names or ["__none__"]]}
    blocks = _rows("Farm Block", ["name", "farm", "farm_zone", "block_name"], land_filters(frappe.get_meta("Farm Block"), scope))
    block_index = {r.name: r for r in blocks if r.farm in farm_names}
    history_filters = dict(base)
    if scope.get("zone"):
        history_filters["farm_zone"] = scope["zone"]
    # A zone cannot be attributed to an individual lot. Hide historical cohorts for lot/cycle filters.
    handovers = [] if scope.get("block") or scope.get("cycle") else _rows("Lotus Handover Cohort",
        ["name", "farm", "farm_zone", "source_event_date", "equivalent_selection_date", "source_cut_qty", "source_attachment", "source_sha256", "source_cells"], history_filters)
    handovers.sort(key=lambda r: (r.farm, r.farm_zone, str(r.source_event_date)))
    adoptions = _rows("Lotus Process Adoption", ["name", "farm", "version", "approval_state", "valid_from", "valid_to", "preset_key", "source_label", "condition_class", "source_version", "source_hash", "color_anchor", "color_anchor_code", "color_period_days", *PARAMETERS], base, 1000)
    selected_filters = land_filters(frappe.get_meta("Sucker Selection Batch"), scope)
    selected_filters.update(farm=base["farm"], docstatus=["<", 2])
    selections = _rows("Sucker Selection Batch", ["name", "farm", "farm_block", "crop_cycle", "selection_date", "selected_sucker_qty", "status", "docstatus"], selected_filters)
    selections = [r for r in selections if r.farm_block in block_index]
    schedules = []
    for source in handovers:
        for planned in selection_schedule(source.source_event_date, count=7):
            schedules.append(dict(source=source.name, farm=source.farm, farm_zone=source.farm_zone, source_cut_qty=source.source_cut_qty, **planned))
    monthly = defaultdict(lambda: defaultdict(float))
    for r in schedules:
        if r["date_kind"] == "Planned" and r["selection_date"] <= str(end):
            key = (r["farm"], r["farm_zone"], r["selection_date"][:7])
            monthly[key]["cohort_count"] += 1
            monthly[key]["source_cut_qty"] += r["source_cut_qty"]
    selection_months = [dict(farm=k[0],farm_zone=k[1],month=k[2],
        verification='Đã đến kỳ · cần đối chiếu thực tế' if k[2]<=nowdate()[:7] else 'Kế hoạch',**v) for k,v in sorted(monthly.items())]
    workflow = []
    for key, title, doctype, route, evidence in PROCESS_STEPS:
        permitted = bool(frappe.has_permission(doctype, "read"))
        count = None
        if permitted and frappe.db.exists("DocType", doctype):
            meta = frappe.get_meta(doctype)
            filters = land_filters(meta, scope)
            if meta.has_field("farm"):
                filters["farm"] = base["farm"]
            if not meta.issingle and (not scope.get('farm') or meta.has_field('farm') or doctype=='Farm'):
                # permission-filtered count, never get_all of operational rows
                count = len(frappe.get_list(doctype, filters=filters, pluck="name", limit_page_length=10000))
        workflow.append(dict(key=key,title=title,doctype=doctype,route=route,evidence=evidence,count=count,can_read=permitted,can_create=bool(frappe.has_permission(doctype,"create"))))
    colors = []
    for a in adoptions:
        if a.approval_state != "Approved":
            continue
        periods = color_periods(a.color_anchor, a.color_anchor_code, data["colors"], max(start,getdate(a.valid_from)), min(end,getdate(a.valid_to or end)), a.color_period_days) if getdate(a.valid_from) <= end and (not a.valid_to or getdate(a.valid_to)>=start) else []
        for r in periods:
            colors.append(dict(farm=a.farm,process_adoption=a.name, **r,
                injection_from=str(getdate(r["valid_from"])-timedelta(days=14)),injection_to=str(getdate(r["valid_to"])-timedelta(days=14)),
                harvest_from=str(getdate(r["valid_from"])+timedelta(days=55)),harvest_to=str(getdate(r["valid_to"])+timedelta(days=70))))
    return dict(source_version=data["version"],source_hash=digest,selection_source=SELECTION_SOURCE,farms=farms,blocks=list(block_index.values()),
                handovers=handovers,selection_calendar=schedules,selection_months=selection_months,observed_selections=selections,
                adoptions=adoptions,workflow=workflow,colors=colors,library=data,
                from_date=str(start),to_date=str(end),
                can_configure=bool(frappe.has_permission("Lotus Process Adoption","create")),
                can_import=bool(frappe.has_permission("Lotus Handover Cohort","create")),
                warnings=(["Lịch sử bàn giao chỉ có theo khu, không gán xuống lô/vụ."] if scope.get("block") or scope.get("cycle") else []))


@frappe.whitelist(methods=["POST"])
def create_adoption(farm, preset_key, condition_class=None, valid_from=None, valid_to=None, approve=False):
    require_role("Lotus Farm Manager")
    _farm(farm, "create")
    lock("Farm", farm)
    data, _ = library()
    extension=data["color_extension"]
    versions = frappe.get_all("Lotus Process Adoption", filters={"farm":farm}, pluck="version")
    if cint(approve):
        effective=getdate(valid_from or nowdate())
        for previous in frappe.get_all('Lotus Process Adoption',filters={'farm':farm,'approval_state':'Approved'},fields=['name','valid_from','valid_to']):
            if getdate(previous.valid_from)<effective and (not previous.valid_to or getdate(previous.valid_to)>=effective):
                if effective<getdate(nowdate()):frappe.throw('Không thay đổi hồi tố hiệu lực quy trình đã duyệt.')
                # Future yield settings may change while the color cadence stays identical.
                # Issued tags retain their original provenance; new cuts must use the
                # adoption effective on the actual cut day, checked by tag_lineage.
                tags=frappe.get_all('Bunch Tag',filters={'process_adoption':previous.name},pluck='name')
                if tags and frappe.db.exists('Bunch Operation',{'bunch_tag':['in',tags],'operation_type':'Cut Bud',
                        'operation_date':['>=',effective],'docstatus':['<',2]}):
                    frappe.throw('Phiên bản cũ đã có đợt cắt bắp trong kỳ mới. Chọn hiệu lực sau các chứng từ đó.')
                old=frappe.get_doc('Lotus Process Adoption',previous.name)
                old.valid_to=str(effective-timedelta(days=1))
                with command(old,'retire_process'):old.save()
    doc=frappe.get_doc(dict(doctype="Lotus Process Adoption",farm=farm,version=max([cint(v) for v in versions] or [0])+1,
        preset_key=preset_key,condition_class=condition_class or "",valid_from=valid_from or nowdate(),valid_to=valid_to,
        approval_state="Approved" if cint(approve) else "Draft", color_anchor=extension["anchor"],color_anchor_code=extension["anchor_code"],
        color_period_days=extension["period_days"],notes="Áp dụng bộ tham số tham chiếu OneDrive; sản lượng là dự phóng, không phải thực tế."))
    doc.insert()
    return doc.as_dict()


@frappe.whitelist(methods=["POST"])
def generate_tags(process_adoption, from_date, to_date):
    require_role("Lotus Farm Manager")
    adoption=frappe.get_doc("Lotus Process Adoption",process_adoption);adoption.check_permission("read")
    weekly_start=frappe.db.get_value("Bunch Tag", {"farm":adoption.farm, "source_kind":"Lotus Weekly", "enabled":1}, "valid_from", order_by="valid_from asc")
    if weekly_start and getdate(to_date)>=getdate(weekly_start):
        frappe.throw("Vườn đã chuyển sang lịch màu dây 7 ngày/tuần. Không tạo lịch tham chiếu 5 ngày từ tuần áp dụng.")
    _farm(adoption.farm,"write")
    lock("Lotus Process Adoption", adoption.name)
    if adoption.approval_state!="Approved":
        frappe.throw("Chỉ tạo lịch màu từ phiên bản đã duyệt.")
    if getdate(from_date)<getdate(adoption.valid_from) or (adoption.valid_to and getdate(to_date)>getdate(adoption.valid_to)):
        frappe.throw("Khoảng lịch màu phải trong hiệu lực quy trình.")
    data,_=library()
    periods=color_periods(adoption.color_anchor,adoption.color_anchor_code,data["colors"],from_date,to_date,adoption.color_period_days)
    created=0
    for row in periods:
        # Include farm + version: two farms and revised future programs never collide.
        code=f"{adoption.farm}:v{adoption.version}:{row['tag_code']}"
        if frappe.db.exists("Bunch Tag",{"tag_code":code}):
            continue
        doc=frappe.get_doc(dict(doctype="Bunch Tag",tag_code=code,display_name=f"{row['color_label']} ({row['valid_from']} – {row['valid_to']})",
            enabled=1,farm=adoption.farm,process_adoption=adoption.name,color_code=row["color_code"],period_basis="Cut Bud",source_kind="Extended Plan",source_version=adoption.source_version,
            valid_from=row["valid_from"],valid_to=row["valid_to"]))
        with command(doc,"process_tag"):
            doc.insert()
        created+=1
    return dict(created=created,existing=len(periods)-created)


@frappe.whitelist()
def forecast(company=None,farm=None,zone=None,block=None,cycle=None,from_date=None,include_handover=False):
    """36-month planning outlook. Handover simulation remains a separate result."""
    if not frappe.has_permission("Harvest Forecast","read"):
        frappe.throw("Không có quyền xem dự thu.",frappe.PermissionError)
    payload=board(company,farm,zone,block,cycle,from_date)
    start,end=payload['from_date'],payload['to_date']
    output=[];simulation=[];planned=[];issues=[];cut_details=[]
    source_scope=land_scope(company=company,farm=farm,zone=zone,block=block,cycle=cycle)
    permitted_blocks={b.name:b for b in payload['blocks']}
    operation_filters=land_filters(frappe.get_meta('Bunch Operation'),source_scope)
    operation_filters.update(docstatus=1,operation_type='Cut Bud',farm_block=['in',list(permitted_blocks) or ['__none__']])
    cuts=_rows('Bunch Operation',['name','farm','farm_block','farm_plot','crop_cycle','sucker_selection_batch','operation_date','bunch_qty','net_bunch_qty',
        'expected_harvest_from','expected_harvest_to','expected_harvest_date','bunch_tag'],operation_filters)
    claims=defaultdict(float)
    for cut in cuts:
        claims[(cut.crop_cycle,cut.sucker_selection_batch or '')]+=float(cut.bunch_qty or 0)
        from lotus_farm.onedrive_supply import source_cut, source_rows
        try:
            parts=source_rows(source_cut(cut.name))
        except frappe.ValidationError as exc:
            issues.append(dict(farm=cut.farm,source=cut.name,message=str(exc)));continue
        for part in parts:
            if not start<=part['month']+'-01'<=end:continue
            part['farm_zone']=permitted_blocks[cut.farm_block].farm_zone
            output.append(part);cut_details.append(part)
    for row in payload['observed_selections']:
        for part in harvest_curve(row.selection_date,basis='Selection',cycles=1 if row.status=='Closed' else 6):
            when=part['month']+'-01'
            if not start<=when<=end:continue
            adoption=_active(payload['adoptions'],row.farm,when)
            if not adoption:
                issues.append(dict(farm=row.farm,source=row.name,message='Thiếu phiên bản hệ số đã duyệt trong kỳ thu.'));continue
            quantity=float(row.selected_sucker_qty)
            if not part['cycle_offset']:
                balance=source_balance(quantity*adoption.cut_rate,claims[(row.crop_cycle,row.name)],0)
                quantity=balance['unobserved_cut']/adoption.cut_rate if adoption.cut_rate else 0
            if quantity:
                output.append(dict(farm=row.farm,farm_zone=permitted_blocks[row.farm_block].farm_zone,farm_block=row.farm_block,source=row.name,
                    source_kind='Observed Selection' if not part['cycle_offset'] else 'Projected Ratoon',
                    month=part['month'],process_adoption=adoption.name,**forecast_quantities(quantity,adoption,part['share'])))
    # Approved lot plans stay separate from observed cohorts: no implicit match to
    # a later actual selection, which could be a different partial cohort.
    plan_filters=land_filters(frappe.get_meta('Plan Cohort'),source_scope)
    plan_filters.update(approval_state='Approved',farm_block=['in',list(permitted_blocks) or ['__none__']])
    versions={}
    for row in _rows('Plan Cohort',['name','farm','farm_block','cohort_code','anchor','anchor_date','quantity_basis','planned_qty','version'],plan_filters):
        key=(row.farm,row.farm_block,row.cohort_code)
        if key not in versions or row.version>versions[key].version:versions[key]=row
    for row in versions.values():
        if row.anchor in ('Planting','Selection'):
            periods=harvest_curve(row.anchor_date,basis=row.anchor,cycles=1)
        elif row.anchor=='Cut Bud':
            periods=window_months(getdate(row.anchor_date)+timedelta(days=55),getdate(row.anchor_date)+timedelta(days=70))
        else:
            issues.append(dict(farm=row.farm,source=row.name,message='Kế hoạch từ trổ cần cửa sổ thu đã hiệu chuẩn.'));continue
        for part in periods:
            when=part['month']+'-01'
            if not start<=when<=end:continue
            adoption=_active(payload['adoptions'],row.farm,when)
            if not adoption:continue
            params=dict(adoption)
            if row.quantity_basis=='Bunches':params['cut_rate']=1
            planned.append(dict(farm=row.farm,farm_zone=permitted_blocks[row.farm_block].farm_zone,source=row.name,source_kind='Plan Cohort',month=part['month'],
                process_adoption=adoption.name,**forecast_quantities(row.planned_qty,params,part['share'])))
    if cint(include_handover):
        for row in payload['handovers']:
            for part in harvest_curve(row.source_event_date,basis='First Cut Equivalent',cycles=6):
                when=part['month']+'-01'
                if not start<=when<=end:continue
                adoption=_active(payload['adoptions'],row.farm,when)
                if not adoption:
                    issues.append(dict(farm=row.farm,source=row.name,message='Thiếu phiên bản hệ số đã duyệt trong kỳ thu.'));continue
                simulation.append(dict(farm=row.farm,farm_zone=row.farm_zone,source=row.name,source_kind='Handover Simulation',
                    quantity_assumption='1 cây cũ đã chặt = 1 chồi giả định; chưa kiểm đếm chồi',
                    month=part['month'],process_adoption=adoption.name,**forecast_quantities(row.source_cut_qty,adoption,part['share'])))
    def aggregate(rows):
        totals=defaultdict(lambda:defaultdict(float))
        bases=defaultdict(set)
        for r in rows:
            adoption=next(a for a in payload['adoptions'] if a.name==r['process_adoption'])
            r.update(_grade_quantities(adoption,r['month'],r['processed_kg']))
            bases[(r['farm'],r.get('farm_zone') or '',r['month'])].add(r['source_kind'])
            for key in ('cut_bunches','harvest_bunches','processed_bunches','gross_kg','processed_kg'):
                totals[(r['farm'],r.get('farm_zone') or '',r['month'])][key]+=r[key]
            for key,value in r.items():
                if key.startswith('grade_'):totals[(r['farm'],r.get('farm_zone') or '',r['month'])][key]+=value
        return [dict(farm=k[0],farm_zone=k[1],month=k[2],source_kinds=sorted(bases[k]),**{f:round(v,3) for f,v in values.items()}) for k,values in sorted(totals.items())]
    return dict(rows=aggregate(output),plan_rows=aggregate(planned),handover_scenario=aggregate(simulation),source_rows=cut_details,issues=list({(r['farm'],r['message']):r for r in issues}.values()),
        from_date=start,to_date=end,planning_only=True,
        window_distribution='Đợt cắt bắp ưu tiên thực tế, trừ đã thu/hủy; phân bổ đều ngày trong cửa sổ khi chưa có đo trái.',
        handover_assumption='Mô phỏng riêng: một cây cũ đã chặt tương ứng một chồi giả định. Chưa có kiểm đếm chồi; không cộng vào dự thu thực tế.')


def validate_tag_master(doc,method=None):
    check_farm(doc)
    if not doc.get('process_adoption'):return
    before=doc.get_doc_before_save()
    if doc.is_new() and not command_allowed(doc,'process_tag'):
        frappe.throw('Tạo màu dây qua lịch chương trình đã duyệt.')
    if before and any(before.get(k)!=doc.get(k) for k in ('farm','process_adoption','color_code','tag_code','valid_from','valid_to','period_basis','source_kind','source_version')):
        frappe.throw('Giữ nguyên mã và kỳ màu dây đã phát hành.')


def tag_lineage(doc,method=None):
    tag_name=doc.get('bunch_tag') or doc.get('ribbon_color')
    source_name=doc.get('source_cut_operation')
    active=False
    when=doc.get('operation_date') or doc.get('harvest_date') or doc.get('posting_date')
    if when:
        active=frappe.get_all('Lotus Process Adoption',filters={'farm':doc.farm,'approval_state':'Approved','valid_from':['<=',when]},fields=['valid_to'])
        active=any(not a.valid_to or getdate(a.valid_to)>=getdate(when) for a in active)
        if active and ((doc.doctype=='Bunch Operation' and doc.operation_type!='Shooting') or doc.doctype in ('Fruit Measurement','Harvest Actual')):
            if doc.doctype=='Bunch Operation' and doc.operation_type in ('Cut Bud','Bud Injection'):
                if not tag_name:frappe.throw('Vườn đã áp dụng OneDrive: đợt chích/cắt bắp phải chọn mã màu dây.')
            elif not source_name:
                frappe.throw('Vườn đã áp dụng OneDrive: chọn đợt cắt bắp gốc để truy xuất công đoạn.')
    if source_name:
        if doc.doctype=='Bunch Operation' and doc.operation_type in ('Cut Bud','Bud Injection','Shooting'):
            frappe.throw('Chỉ công đoạn sau cắt bắp được liên kết đợt cắt bắp gốc.')
        source=frappe.get_doc('Bunch Operation',source_name);source.check_permission('read')
        if source.docstatus!=1 or source.operation_type!='Cut Bud':frappe.throw('Đợt cắt bắp gốc phải là chứng từ đã xác nhận.')
        for key in ('farm','farm_block','crop_cycle','sucker_selection_batch','farm_plot'):
            if (doc.get(key) or '')!=(source.get(key) or ''):frappe.throw('Đợt buồng phải cùng vườn, lô, thửa và vụ/chồi.')
        if tag_name and tag_name!=source.bunch_tag:frappe.throw('Màu dây phải theo đợt cắt bắp gốc.')
        tag_name=source.bunch_tag
        doc.set('bunch_tag' if doc.doctype=='Bunch Operation' else 'ribbon_color',tag_name)
        when=doc.get('operation_date') or doc.get('harvest_date') or doc.get('posting_date')
        if getdate(when)<getdate(source.operation_date):frappe.throw('Ngày thực hiện không thể trước cắt bắp gốc.')
        qty=doc.get('bunch_qty') if doc.doctype=='Bunch Operation' else doc.get('harvested_bunch_qty')
        if qty and cint(qty)>cint(source.net_bunch_qty):frappe.throw('Số buồng vượt đợt cắt bắp gốc.')
        if doc.doctype=='Harvest Actual':
            # Serialize cumulative harvests against the same cut cohort.
            lock('Bunch Operation',source.name)
            other=frappe.get_all('Harvest Actual',filters={'source_cut_operation':source.name,'docstatus':['<',2],'name':['!=',doc.name]},fields=['harvested_bunch_qty'])
            cancelled=sum(cint(r.bunch_qty) for r in frappe.get_all('Bunch Cancellation',filters={'source_operation':source.name,'docstatus':1},fields=['bunch_qty']))
            if sum(cint(r.harvested_bunch_qty) for r in other)+cint(qty)+cancelled>cint(source.net_bunch_qty):frappe.throw('Tổng thu hoạch và hủy vượt số buồng cắt bắp của đợt.')
    if not tag_name:return
    tag=frappe.get_doc('Bunch Tag',tag_name);tag.check_permission('read')
    if tag.get('farm') and tag.farm!=doc.farm:frappe.throw('Màu dây thuộc vườn khác.')
    if active and doc.doctype=='Bunch Operation' and doc.operation_type in ('Cut Bud','Bud Injection') and not tag.get('process_adoption') and tag.get('source_kind')!='Lotus Weekly':
        frappe.throw('Chọn mã màu có phiên bản quy trình OneDrive cho đợt mới.')
    if not tag.get('process_adoption'):return  # Legacy guard still handles unversioned operation tags.
    if not tag.enabled:frappe.throw('Màu dây đã ngừng sử dụng.')
    operation=doc.get('operation_type')
    if doc.doctype=='Bunch Operation' and operation in ('Cut Bud','Bud Injection'):
        offset=14 if operation=='Bud Injection' else 0
        when=getdate(doc.operation_date)+timedelta(days=offset)
        if not getdate(tag.valid_from)<=when<=getdate(tag.valid_to):frappe.throw('Ngày công đoạn ngoài kỳ màu dây cắt bắp (chích bắp sớm 14 ngày).')
        adoption=frappe.get_doc('Lotus Process Adoption',tag.process_adoption)
        if when<getdate(adoption.valid_from) or (adoption.valid_to and when>getdate(adoption.valid_to)):
            frappe.throw('Phiên bản màu dây đã ngoài hiệu lực cho đợt mới; chọn phiên bản đang áp dụng.')
        if operation=='Cut Bud':
            doc.expected_harvest_from=str(getdate(tag.valid_from)+timedelta(days=55))
            doc.expected_harvest_to=str(getdate(tag.valid_to)+timedelta(days=70))
            if doc.sucker_selection_batch:
                lock('Sucker Selection Batch',doc.sucker_selection_batch)
                selected=cint(frappe.db.get_value('Sucker Selection Batch',doc.sucker_selection_batch,'selected_sucker_qty'))
                others=frappe.get_all('Bunch Operation',filters={'sucker_selection_batch':doc.sucker_selection_batch,'operation_type':'Cut Bud','docstatus':['<',2],
                    'name':['!=',doc.name]},fields=['bunch_qty'])
                if sum(cint(r.bunch_qty) for r in others)+cint(doc.bunch_qty)>selected:
                    frappe.throw('Tổng số buồng cắt bắp vượt số chồi đã kiểm đếm trong đợt.')
    elif not source_name:
        frappe.throw('Chọn đợt cắt bắp gốc để giữ màu dây khi chăm sóc, đo trái hoặc thu hoạch.')


def preserve_cut_source(doc,method=None):
    if doc.operation_type!='Cut Bud':return
    used=any(frappe.db.exists(dt,{'source_cut_operation':doc.name,'docstatus':['<',2]}) for dt in ('Bunch Operation','Fruit Measurement','Harvest Actual'))
    before=doc.get_doc_before_save()
    claim=frappe.qb.DocType('Forecast Source Claim');forecast=frappe.qb.DocType('Harvest Forecast')
    published=(frappe.qb.from_(claim).join(forecast).on(claim.parent==forecast.name).select(claim.name)
        .where((claim.source_cut_operation==doc.name)&(claim.parenttype=='Harvest Forecast')&(forecast.supply_state!='Draft')).limit(1).for_update().run())
    used=bool(used or published)
    if used and (method=='before_cancel' or (before and any(before.get(k)!=doc.get(k) for k in ('farm','farm_block','farm_plot','crop_cycle','sucker_selection_batch','operation_date','bunch_tag','bunch_qty','rejected_qty')))):
        frappe.throw('Đợt cắt bắp đã có công đoạn tiếp nối; giữ nguyên dữ liệu truy xuất.')
