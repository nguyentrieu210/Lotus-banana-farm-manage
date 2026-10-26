"""Farm work workspace: permission-filtered catalog and readiness, no seed data."""
import frappe
from frappe.utils import getdate, flt


@frappe.whitelist()
def load(farm, posting_date=None, zone=None):
    record=frappe.get_doc('Farm',farm)
    record.check_permission('read')
    date=getdate(posting_date)
    def rows(dt,fields,filters=None):
        if not frappe.has_permission(dt,'read'):
            return []
        return frappe.get_list(dt,filters=filters or {},fields=fields,
            limit_page_length=20000,order_by='name asc')
    all_blocks=rows('Farm Block',['name','block_code','block_name','farm_zone','area_ha','active'],{'farm':farm})
    from lotus_farm.scoping import land_scope
    selected=land_scope(farm=farm,zone=zone)
    blocks=[b for b in all_blocks if not zone or b.farm_zone==zone]
    plots=rows('Farm Plot',['name','plot_code','plot_name','farm_block','area_ha','active'],{'farm':farm})
    teams=rows('Work Team',['name','team_code','team_name','active'],{'farm':farm})
    categories=rows('Work Category',['name','category_code','category_name','active'])
    works=rows('Work Type',['name','work_code','work_name','category','uom','payment_basis','allow_piecework','allow_daywork','productivity_per_workday','piecework_rate','active'])
    norms=rows('Material Norm Profile',['name','profile_name','version','work_type','valid_from','valid_to','approval_state'],{'farm':farm})
    bases=rows('Norm Basis',['name','basis_code','basis_name','uom','active'])
    cycles=rows('Crop Cycle',['name','farm_block','farm_plot','cycle_no','variety','planting_date','status'],{'farm':farm})
    cycles=[c for c in cycles if c.farm_block in {b.name for b in blocks}]
    varieties=rows('Banana Variety',['name','variety_code','variety_name','active'])
    plans=rows('Daily Work Plan',['name','posting_date','docstatus','modified','owner','rate_approval_state','rate_requested_by','rate_approved_by','rate_approval_note'],{'farm':farm,'posting_date':date})
    if zone:
        from lotus_farm.console import _source_scope_names
        allowed=set(_source_scope_names('Daily Work Plan',selected))
        plans=[p for p in plans if p.name in allowed]
    category_names={c.name:c.category_name for c in categories}
    work_names={w.name:w.work_name for w in works}
    for p in plans:
        if p.get("rate_approval_state") in ("Pending", "Approved", "Rejected"):
            plan=frappe.get_doc("Daily Work Plan",p.name)
            plan.check_permission("read")
            p["rate_details"]="; ".join(
                f"{work_names.get(r.work_type,r.work_type)}: {r.list_piecework_rate:g} → {r.requested_piecework_rate:g} đ/{r.uom} (SL {r.planned_qty:g})"
                for r in plan.lines if (r.requested_piecework_rate or 0) > (r.list_piecework_rate or 0)
            )
            p["rate_request_reason"]=plan.rate_request_reason or ""
    for work in works:work['category_label']=category_names.get(work.category,work.category)
    active_cycles={}
    for c in cycles:
        if c.status in ('Active','Harvesting'):
            active_cycles.setdefault(c.farm_block,[]).append(c.name)
    missing=[p.name for p in blocks if p.active and not active_cycles.get(p.name)]
    ambiguous=[p.name for p in plots if p.active and len(active_cycles.get(p.name,[]))>1]
    pending=[w.name for w in works if w.active and (flt(w.productivity_per_workday)<=0 or (w.allow_piecework and flt(w.piecework_rate)<=0))]
    return dict(farm=record.name,farm_name=record.farm_name,company=record.company,
        posting_date=str(date),zones=sorted({b.farm_zone for b in all_blocks if b.farm_zone}),blocks=blocks,plots=plots,teams=teams,categories=categories,
        works=works,cycles=cycles,varieties=varieties,plans=plans,norms=norms,bases=bases,
        readiness=dict(missing_productivity=pending,missing_active_cycles=missing,
            ambiguous_active_cycles=ambiguous,
            active_teams=sum(bool(t.active) for t in teams),active_works=sum(bool(w.active) for w in works)),
        permissions={dt:{p:frappe.has_permission(dt,p) for p in ('read','create','write','submit')}
            for dt in ('Farm Block','Farm Plot','Work Team','Work Category','Work Type','Crop Cycle','Banana Variety','Daily Work Plan','Daily Work Result','Material Norm Profile','Norm Basis')})


@frappe.whitelist()
def norm_options(farm, doctype, search='', work_type=None):
    frappe.get_doc('Farm',farm).check_permission('read')
    if doctype not in ('Item','UOM','Work Type','Norm Basis'):
        frappe.throw('Lựa chọn định mức vật tư không hợp lệ.')
    if not frappe.has_permission(doctype,'read'):
        frappe.throw('Cần quyền xem.',frappe.PermissionError)
    filters={}
    if doctype=='Item':filters={'is_stock_item':1,'disabled':0}
    elif doctype=='Work Type':filters={'active':1}
    elif doctype=='Norm Basis':
        if not work_type:return []
        work=frappe.get_doc('Work Type',work_type);work.check_permission('read')
        filters={'active':1,'uom':work.uom}
    title=frappe.get_meta(doctype).title_field or 'name'
    values=frappe.get_list(doctype,filters=filters,
        or_filters={'name':['like','%'+search[:80]+'%'],title:['like','%'+search[:80]+'%']} if search else None,
        fields=list(dict.fromkeys(['name',title])),limit_page_length=30,order_by='name')
    return [dict(value=r.name,label=r.get(title) or r.name) for r in values]
