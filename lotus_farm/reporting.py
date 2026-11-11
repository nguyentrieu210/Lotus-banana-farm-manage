"""Permission-filtered management data for Tổng quan."""
import frappe
from frappe.utils import flt, getdate
from lotus_farm.scoping import land_scope, land_filters

ENTRY, SHIFT = 'Lotus Work Entry', 'Packhouse Shift'


def records(doctype,filters,fields):
    if not frappe.has_permission(doctype,'read'):
        frappe.throw('Cần quyền xem '+getattr(frappe, "_", str)(doctype),frappe.PermissionError)
    result=frappe.get_list(doctype,filters=filters,fields=fields,limit_page_length=10000)
    if len(result)==10000 and frappe.get_list(doctype,filters=filters,fields=['name'],limit_start=10000,limit_page_length=1):
        frappe.throw('Phạm vi báo cáo vượt 10.000 bản ghi cho '+getattr(frappe, "_", str)(doctype)+'; hãy thu hẹp vườn/khoảng ngày.')
    return result


def scope(farm):
    doc=frappe.get_doc('Farm',farm);doc.check_permission('read');return doc


def _section(build):
    """One chart section; a missing read permission hides that section instead of failing the page."""
    try:
        return dict(allowed=True,**build())
    except frappe.PermissionError:
        frappe.clear_messages()
        return dict(allowed=False)


@frappe.whitelist()
def charts(from_date,to_date,farm=None,company=None,block=None,zone=None,report_filters=None):
    """Aggregated series for the report charts, within one land scope and the reader's permissions. The garden figures
    come from confirmed lines of the sổ lô, closed ca đóng gói and the shared forecast (block_forecast.board)."""
    from lotus_farm import report_charts as rc
    start,end=getdate(from_date),getdate(to_date)
    if start>end or (end-start).days>365:frappe.throw('Chọn kỳ báo cáo tối đa 366 ngày.')
    selected=land_scope(company,farm,block,zone=zone)
    farms=[f.name for f in records('Farm',land_filters(frappe.get_meta('Farm'),selected),['name'])]
    in_farms={'farm':['in',farms or ['__none__']]}
    land_only=bool(zone or block)
    report_filters=frappe.parse_json(report_filters or '{}')
    if not isinstance(report_filters,dict):frappe.throw('Bộ lọc báo cáo không hợp lệ')
    def choices(rows,field):return sorted({r.get(field) for r in rows if r.get(field)})
    def matching(rows,fields):
        return [r for r in rows if all(not report_filters.get(key) or r.get(field)==report_filters[key] for key,field in fields.items())]
    def ledger(extra,fields):
        return records(ENTRY,{**land_filters(frappe.get_meta(ENTRY),selected),**in_farms,'state':'Confirmed','posting_date':['between',[start,end]],**extra},fields)

    def land():
        meta=frappe.get_meta('Farm Block')
        fields=['name','farm_zone','area_ha']+[f for f in ('lotus_tree_count','lotus_estimated_flowering_date') if meta.has_field(f)]
        blocks=records('Farm Block',{**land_filters(meta,selected),**({} if selected['farm'] else in_farms)},fields)
        return dict(zones=rc.land_by_zone(blocks),flowering=rc.flowering_by_month(blocks),blocks=len(blocks),
            area_ha=sum(flt(b.area_ha) for b in blocks),trees=sum(flt(b.get('lotus_tree_count')) for b in blocks),
            counted_blocks=sum(1 for b in blocks if flt(b.get('lotus_tree_count'))>0))

    def work():
        # One point per day and one query for every line of the period: keep the window small.
        if (end-start).days>93:return dict(days=None,types=None,note='Chọn tối đa 94 ngày để xem công việc theo ngày.')
        from lotus_farm.field_report import _weights
        lines=ledger({},['name','posting_date','work_type'])
        names={w.name:w.work_name for w in frappe.get_all('Work Type',filters={'name':['in',list({l.work_type for l in lines}) or ['']]},fields=['name','work_name'])}
        # A whole buổi is half a công.
        weights=_weights({'_by':'entry','names':[l.name for l in lines]})
        rows=[dict(posting_date=l.posting_date,work_name=names.get(l.work_type,l.work_type),workdays=sum(weights.get(l.name,{}).values())/2) for l in lines]
        return dict(days=rc.work_by_day(rows,start,end),types=rc.work_by_type(rows))

    def harvest():
        rows=ledger({'stage':'Harvest'},['posting_date','qty','weight_kg'])
        return dict(weeks=rc.weekly(rows,'posting_date',['qty','weight_kg'],start,end))

    def packout():
        # A ca takes bunches from many lô; it stays at farm level.
        if land_only:return dict(weeks=None,note='Đóng gói chỉ xem theo vườn, không chia theo khu/lô.')
        rows=records(SHIFT,{**in_farms,'docstatus':1,'posting_date':['between',[start,end]]},['posting_date','input_kg','finished_kg','cartons'])
        return dict(weeks=rc.weekly(rows,'posting_date',['input_kg','finished_kg','cartons'],start,end))

    def losses():
        rows=ledger({'stage':'Reject'},['reason','qty'])
        names={r.name:r.reason_name for r in frappe.get_all('Cancellation Reason',filters={'name':['in',list({r.reason for r in rows if r.reason}) or ['']]},fields=['name','reason_name'])}
        for row in rows:row['reason']=names.get(row.reason,row.reason)
        return dict(reasons=rc.top_totals(rows,'reason','qty'),total=sum(flt(r.qty) for r in rows))

    def forecast():
        # The one forecast of the system: the same call the Dự thu page makes.
        from lotus_farm.block_forecast import board
        months,totals,horizon={},dict(bunches=0,kg=0.0,cartons=0.0),None
        for name in farms:
            bunch=board(name,selected.get('zone'),selected['block'])['bunch']
            horizon=bunch['horizon']
            for key in totals:totals[key]+=flt(bunch['totals'][key])
            for month in bunch['months']:
                slot=months.setdefault(month['month'],dict(month=month['month'],bunches=0,kg=0.0,cartons=0.0))
                for key in totals:slot[key]+=flt(month[key])
        return dict(months=[months[key] for key in sorted(months)],horizon_weeks=horizon,**totals)

    def stock():
        filters={'docstatus':1,'posting_date':['between',[start,end]],**({'company':selected['company']} if selected['company'] else {})}
        if selected['farm'] and not selected['company']:
            filters['company']=frappe.db.get_value('Farm',selected['farm'],'company')
        rows=records('Stock Entry',filters,['posting_date','stock_entry_type'])
        options=dict(stock_type=choices(rows,'stock_entry_type'))
        return dict(scope_label='Toàn công ty',options=options,months=rc.stock_by_month(matching(rows,{'stock_type':'stock_entry_type'})))

    def people():
        companies={frappe.db.get_value('Farm',f,'company') for f in farms}
        employees=records('Employee',{'company':['in',list(companies)],
            **({'lotus_farm':farm} if farm else {})},['name','status','lotus_onboarding_state','lotus_worker_category','department'])
        options=dict(department=choices(employees,'department'),worker_category=choices(employees,'lotus_worker_category'))
        employees=matching(employees,{'department':'department','worker_category':'lotus_worker_category'})
        names=[e.name for e in employees]
        attendance=records('Attendance',{'employee':['in',names or ['__none__']],
            'docstatus':1,'attendance_date':['between',[start,end]]},['status'])
        slips=records('Salary Slip',{'employee':['in',names or ['__none__']],
            'docstatus':1,'start_date':['<=',end],'end_date':['>=',start]},['currency','net_pay'])
        payroll={}
        for slip in slips:payroll[slip.currency]=payroll.get(slip.currency,0)+flt(slip.net_pay)
        from collections import Counter
        return dict(scope_label='Theo vườn' if farm else 'Toàn công ty',options=options,employees=len(employees),active=sum(e.status=='Active' for e in employees),
            pending=sum(e.lotus_onboarding_state!='Ready' for e in employees),
            attendance=[dict(status=k,count=v) for k,v in Counter(a.status for a in attendance).items()],
            payroll=[dict(currency=k,net=v) for k,v in payroll.items()],salary_slips=len(slips))

    def orders(doctype):
        companies={frappe.db.get_value('Farm',f,'company') for f in farms}
        kind='buying' if doctype=='Purchase Order' else 'sales'
        party='supplier' if kind=='buying' else 'customer'
        rows=records(doctype,{'company':['in',list(companies)],'docstatus':1,
            'transaction_date':['between',[start,end]]},['name','status','currency','grand_total',party])
        options={kind+'_status':choices(rows,'status'),party:choices(rows,party)}
        rows=matching(rows,{kind+'_status':'status',party:party})
        from collections import Counter
        totals={}
        for row in rows:totals[row.currency]=totals.get(row.currency,0)+flt(row.grand_total)
        return dict(scope_label='Toàn công ty',options=options,count=len(rows),statuses=[dict(status=k,count=v) for k,v in Counter(r.status for r in rows).items()],
                    totals=[dict(currency=k,value=v) for k,v in totals.items()])

    return dict(from_date=str(start),to_date=str(end),farms=farms,land=_section(land),work=_section(work),
        harvest=_section(harvest),packout=_section(packout),losses=_section(losses),forecast=_section(forecast),
        stock=_section(stock),people=_section(people),
        buying=_section(lambda:orders('Purchase Order')),sales=_section(lambda:orders('Sales Order')))
