"""Productivity from explicit actual attribution; aggregate totals are never guessed per person."""
from collections import defaultdict
import frappe
from frappe.utils import flt
from lotus_farm.daily_operations import number


def validate_actual_labor(doc):
    seen=set();days=quantity=0
    for row in doc.actual_labor:
        if bool(row.employee)==bool(row.work_team):frappe.throw('Select either an Employee or a Work Team for each actual line.')
        key=(row.employee or '',row.work_team or '')
        if key in seen:frappe.throw('Combine duplicate actual labor identities.')
        seen.add(key)
        allocations=frappe.get_all('Labor Allocation',filters={'work_plan_line':doc.work_plan_line,'docstatus':1},fields=['employee','work_team','allocated_workdays'])
        capacity=sum(flt(r.allocated_workdays) for r in allocations if (r.employee==row.employee if row.employee else (not r.employee and r.work_team==row.work_team)))
        actual=number(row.actual_workdays,'Actual workdays',positive=True)
        if actual>capacity+0.000001:frappe.throw('Actual labor exceeds its submitted allocation for this task.')
        days+=actual;quantity+=number(row.completed_qty,'Attributed completed quantity')
    if abs(days-flt(doc.actual_workdays))>0.000001 or abs(quantity-flt(doc.completed_qty))>0.000001:
        frappe.throw('Attributed actual workdays and quantity must reconcile to the work result totals.')


@frappe.whitelist()
def report(from_date,to_date,farm=None,company=None,block=None,plot=None,cycle=None):
    from lotus_farm.reporting import records
    filters={'docstatus':1,'posting_date':['between',[from_date,to_date]]}
    from lotus_farm.scoping import land_scope,land_filters
    filters.update(land_filters(frappe.get_meta('Daily Work Result'),land_scope(company,farm,block,plot,cycle)))
    groups={};unattributed=[]
    for row in records('Daily Work Result',filters,['name']):
        doc=frappe.get_doc('Daily Work Result',row.name);doc.check_permission('read')
        line=frappe.db.get_value('Daily Work Plan Line',doc.work_plan_line,['work_type','uom'],as_dict=True)
        if not doc.actual_labor:unattributed.append(doc.name);continue
        for actual in doc.actual_labor:
            key=(doc.farm,line.work_type,line.uom,actual.employee,actual.work_team)
            if key not in groups:groups[key]=dict(farm=doc.farm,work_type=line.work_type,uom=line.uom,employee=actual.employee,work_team=actual.work_team,completed_qty=0,actual_workdays=0,source_documents=[])
            record=groups[key];record['completed_qty']+=flt(actual.completed_qty);record['actual_workdays']+=flt(actual.actual_workdays);record['source_documents'].append(doc.name)
    return dict(rows=[dict(r,quantity_per_workday=r['completed_qty']/r['actual_workdays']) for r in groups.values()],unattributed=unattributed,
        note='Aggregate-only results are excluded from employee/team productivity until actual attribution is recorded.')
