"""Small Desk-facing commands. Permissions apply to parents before child data is read."""
import frappe
from frappe.utils import flt, getdate
from lotus_farm.controls import require_role, lock, validate_warehouse
from lotus_farm.daily_operations import close_checks


@frappe.whitelist()
def daily_overview(farm, posting_date, block=None, plot=None, cycle=None, status=None, view=None):
    record=frappe.get_doc('Farm',farm)
    record.check_permission('read')
    from lotus_farm.scoping import land_scope
    selected=land_scope(farm=farm,block=block,plot=plot,cycle=cycle)
    date=getdate(posting_date)
    tasks=[]
    for name in frappe.get_list('Daily Work Plan',filters={'farm':farm,'posting_date':date,'docstatus':1},pluck='name',limit_page_length=10000):
        plan=frappe.get_doc('Daily Work Plan',name)
        for line in plan.lines:
            if any(selected[k] and line.get(f)!=selected[k] for k,f in [('block','farm_block'),('plot','farm_plot'),('cycle','crop_cycle')]):continue
            results=frappe.get_list('Daily Work Result',filters={'work_plan_line':line.name,'docstatus':1},fields=['name','completed_qty','actual_workdays','unfinished_reason'])
            from lotus_farm.reporting import records
            allocations=records('Labor Allocation',{'work_plan_line':line.name,'docstatus':1},['name','employee','work_team','allocated_workdays'])
            allocated=sum(flt(v.allocated_workdays) for v in allocations)
            result=results[0] if results else {}
            tasks.append(dict(plan=plan.name,line=line.name,farm_block=line.farm_block,farm_plot=line.farm_plot,
                              crop_cycle=line.crop_cycle,cohort=line.sucker_selection_batch,work_type=line.work_type,
                              work_category=frappe.db.get_value('Work Type',line.work_type,'category'),work_name=frappe.db.get_value('Work Type',line.work_type,'work_name'),plot_code=frappe.db.get_value('Farm Plot',line.farm_plot,'plot_code'),uom=line.uom,planned_qty=line.planned_qty,completed_qty=flt(result.get('completed_qty')),
                              required_workdays=line.required_workdays,allocated_workdays=allocated,
                              actual_workdays=flt(result.get('actual_workdays')),
                              labor_gap=(0 if (frappe.db.get_value('Work Type',line.work_type,'payment_basis') or 'Daywork')=='Piece' else allocated-flt(line.required_workdays)),
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
    for row in doc.lines:
        item=frappe.get_doc('Item',row.item);item.check_permission('read')
        data=frappe.db.get_value('Bin',{'item_code':row.item,'warehouse':warehouse},['actual_qty','reserved_stock','stock_uom'],as_dict=True) or {}
        # Firm physical reservations only. Show planning reservations separately in ERPNext.
        actual=flt(data.get('actual_qty'));reserved=flt(data.get('reserved_stock'))
        available=max(actual-reserved,0)
        rows.append(dict(item=row.item,uom=row.uom,required_qty=row.required_qty,
                         actual_qty=actual,reserved_stock=reserved,available_qty=available,
                         shortage_qty=max(flt(row.required_qty)-available,0)))
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
    values=material_availability(doc.name,warehouse)
    shortages=[r for r in values['rows'] if r['shortage_qty']>0]
    if not shortages:
        frappe.throw('No physical shortage for this Warehouse.')
    if getdate(schedule_date)<getdate(doc.posting_date):
        frappe.throw('Material request date cannot precede the work date.')
    request=frappe.get_doc(dict(doctype='Material Request',company=doc.company,material_request_type='Purchase',
        transaction_date=doc.posting_date,schedule_date=schedule_date,
        items=[dict(item_code=r['item'],qty=r['shortage_qty'],uom=r['uom'],stock_uom=r['uom'],
                    conversion_factor=1,warehouse=warehouse,schedule_date=schedule_date) for r in shortages])).insert()
    frappe.db.set_value('Material Requirement',doc.name,'material_request',request.name)
    return dict(material_request=request.name,docstatus=request.docstatus)


@frappe.whitelist()
def preview_close(farm, posting_date):
    require_role('Lotus Farm Manager','Lotus Auditor')
    record=frappe.get_doc('Farm',farm);record.check_permission('read')
    return close_checks(farm,getdate(posting_date))
