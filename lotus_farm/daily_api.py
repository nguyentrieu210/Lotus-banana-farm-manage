"""Small Desk-facing commands. Permissions apply to parents before child data is read."""
import frappe
from frappe.utils import flt, getdate
from lotus_farm.controls import require_role, lock, validate_warehouse
from lotus_farm.daily_operations import close_checks


@frappe.whitelist()
def daily_overview(farm, posting_date, block=None, plot=None, cycle=None, status=None, view=None,zone=None):
    record=frappe.get_doc('Farm',farm)
    record.check_permission('read')
    from lotus_farm.scoping import land_scope
    selected=land_scope(farm=farm,block=block,plot=plot,cycle=cycle,zone=zone)
    date=getdate(posting_date)
    tasks=[]
    for name in frappe.get_list('Daily Work Plan',filters={'farm':farm,'posting_date':date,'docstatus':1},pluck='name',limit_page_length=10000):
        plan=frappe.get_doc('Daily Work Plan',name)
        for line in plan.lines:
            if selected.get('zone_blocks') and line.farm_block not in selected['zone_blocks']:continue
            if any(selected[k] and line.get(f)!=selected[k] for k,f in [('block','farm_block'),('plot','farm_plot'),('cycle','crop_cycle')]):continue
            results=frappe.get_list('Daily Work Result',filters={'work_plan_line':line.name,'docstatus':1},fields=['name','completed_qty','actual_workdays','unfinished_reason'])
            from lotus_farm.reporting import records
            allocations=records('Labor Allocation',{'work_plan_line':line.name,'docstatus':1},['name','employee','work_team','allocated_workdays'])
            allocated=sum(flt(v.allocated_workdays) for v in allocations)
            result=results[0] if results else {}
            tasks.append(dict(plan=plan.name,line=line.name,farm_block=line.farm_block,farm_plot=line.farm_plot,
                              crop_cycle=line.crop_cycle,cohort=line.sucker_selection_batch,work_type=line.work_type,
                              work_category=frappe.db.get_value('Work Type',line.work_type,'category'),work_name=frappe.db.get_value('Work Type',line.work_type,'work_name'),block_code=frappe.db.get_value('Farm Block',line.farm_block,'block_code'),plot_code=frappe.db.get_value('Farm Plot',line.farm_plot,'plot_code') if line.farm_plot else None,uom=line.uom,planned_qty=line.planned_qty,completed_qty=flt(result.get('completed_qty')),
                              required_workdays=line.required_workdays,allocated_workdays=allocated,
                              actual_workdays=flt(result.get('actual_workdays')),labor_gap=allocated-flt(line.required_workdays),
                              result=result.get('name'),unfinished_reason=result.get('unfinished_reason'),
                              status='Completed' if results else (line.execution_state or 'Planned'),
                              responsible=line.responsible,work_team=line.work_team,start_at=line.start_at,due_at=line.due_at,
                              blocked_reason=line.blocked_reason,allocations=allocations))
    for task in tasks:task['posting_date']=str(date)
    if status:tasks=[t for t in tasks if t['status']==status]
    if view=='my-work':tasks=[t for t in tasks if t['responsible']==frappe.session.user]
    if view=='at-risk':tasks=[t for t in tasks if t['status']=='Blocked' or t['labor_gap']<0 or (t['due_at'] and frappe.utils.get_datetime(t['due_at'])<frappe.utils.now_datetime() and t['status']!='Completed')]
    return dict(farm=farm,posting_date=str(date),tasks=tasks,
                labor=frappe.get_list('Daily Labor Summary',filters={'farm':farm,'posting_date':date,'docstatus':1},fields=['name','work_category','work_area','headcount','present','absent','staffing_gap','workdays_per_ha']),
                cancellations=frappe.get_list('Bunch Cancellation',filters={'farm':farm,'posting_date':date,'docstatus':1},fields=['name','farm_block','farm_plot','crop_cycle','reason','bunch_qty']),
                closed=bool(frappe.get_list('Daily Production Close',filters={'farm':farm,'posting_date':date,'docstatus':1},pluck='name')))


@frappe.whitelist(methods=['POST'])
def create_requirements(work_plan):
    require_role('Lotus Farm Manager')
    plan=frappe.get_doc('Daily Work Plan',work_plan)
    plan.check_permission('read')
    lock('Farm',plan.farm)
    lock('Daily Work Plan',plan.name)
    if plan.docstatus!=1:
        frappe.throw('Submit the Work Plan first.')
    names=[]
    for line in plan.lines:
        if not line.norm_profile:
            continue
        existing=frappe.get_all('Material Requirement',filters={'work_plan_line':line.name,'docstatus':['<',2]},pluck='name')
        if existing:
            for name in existing:frappe.get_doc('Material Requirement',name).check_permission('read')
            names.extend(existing);continue
        values={f:line.get(f) for f in ('farm','farm_block','farm_plot','crop_cycle','sucker_selection_batch')}
        doc=frappe.get_doc(dict(doctype='Material Requirement',**values,posting_date=plan.posting_date,
                               work_plan=plan.name,work_plan_line=line.name)).insert()
        names.append(doc.name)
    return names


@frappe.whitelist()
def material_availability(requirement, warehouse):
    doc=frappe.get_doc('Material Requirement',requirement)
    doc.check_permission('read')
    validate_warehouse(warehouse,doc.company)
    if not frappe.has_permission('Stock Ledger Entry','read'):
        frappe.throw('Stock Ledger read permission is required.',frappe.PermissionError)
    rows=[]
    from lotus_farm.warehouse_planning import source_allocations,_draft_holds,stock_quantity
    from lotus_farm.warehouse_rules import coverage
    holds=_draft_holds(doc.company,{warehouse})
    for row in doc.lines:
        item=frappe.get_doc('Item',row.item);item.check_permission('read')
        data=frappe.db.get_value('Bin',{'item_code':row.item,'warehouse':warehouse},['actual_qty','reserved_stock','stock_uom'],as_dict=True) or {}
        # Firm physical reservations only. Show planning reservations separately in ERPNext.
        actual=flt(data.get('actual_qty'));reserved=flt(data.get('reserved_stock'))
        allocations=source_allocations('Material Requirement',doc.name,row.name)
        amounts=coverage(stock_quantity(item,row.uom,row.required_qty),allocations['posted'],actual,reserved,
            holds.get((row.item,warehouse),0),allocations['draft'])
        rows.append(dict(item=row.item,uom=item.stock_uom,reserved_stock=reserved,**amounts))
    return dict(requirement=doc.name,warehouse=warehouse,rows=rows)


@frappe.whitelist(methods=['POST'])
def create_material_request(requirement, warehouse, schedule_date):
    require_role('Lotus Farm Manager')
    doc=frappe.get_doc('Material Requirement',requirement)
    doc.check_permission('write')
    from lotus_farm.daily_operations import day_guard
    day_guard(doc)
    lock('Material Requirement',doc.name)
    if doc.docstatus!=1:
        frappe.throw('Submit the requirement first.')
    if doc.material_request:
        existing=frappe.get_doc('Material Request',doc.material_request)
        existing.check_permission('read')
        if existing.docstatus!=2:
            return dict(material_request=existing.name,docstatus=existing.docstatus)
    if getdate(schedule_date)<getdate(doc.posting_date):
        frappe.throw('Material request date cannot precede the work date.')
    from lotus_farm.warehouse_planning import create_purchase_request,assign_warehouse
    if not doc.get('lotus_warehouse'):
        assign_warehouse(doc.company,doc.name,warehouse)
    result=create_purchase_request(doc.company,warehouse,doc.posting_date,schedule_date,[r.item for r in doc.lines])
    if result.get('name'):frappe.db.set_value('Material Requirement',doc.name,'material_request',result['name'])
    return dict(material_request=result.get('name'),docstatus=result.get('docstatus'),note=result.get('note'))


@frappe.whitelist()
def preview_close(farm, posting_date,zone=None):
    require_role('Lotus Farm Manager','Lotus Auditor')
    record=frappe.get_doc('Farm',farm);record.check_permission('read')
    return close_checks(farm,getdate(posting_date))
