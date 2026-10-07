import frappe
from lotus_farm.daily_api import daily_overview


def execute(filters=None):
    filters=frappe._dict(filters or {})
    if not filters.farm or not filters.posting_date:
        frappe.throw('Select a Farm and a posting date.')
    result=daily_overview(filters.farm,filters.posting_date)
    columns=[dict(fieldname=n,label=label,fieldtype=t,options=o,width=w) for n,label,t,o,w in [
        ('farm_plot','Thửa','Link','Farm Plot',130),('work_type','Công việc','Link','Work Type',150),
        ('uom','Đơn vị','Link','UOM',85),('planned_qty','Kế hoạch','Float',None,100),
        ('completed_qty','Đã làm','Float',None,100),('required_workdays','Công cần','Float',None,100),
        ('allocated_workdays','Đã bố trí','Float',None,100),('actual_workdays','Công thực tế','Float',None,110),
        ('labor_gap','Thừa/thiếu công','Float',None,120),('unfinished_reason','Lý do chưa xong','Data',None,230),
        ('result','Phiếu kết quả','Link','Daily Work Result',130),('plan','Kế hoạch ngày','Link','Daily Work Plan',130),
    ]]
    tasks=result['tasks']
    summary=[dict(label='Công việc',value=len(tasks),datatype='Int'),
             dict(label='Việc hoàn thành',value=sum(1 for r in tasks if r['completed_qty']>=r['planned_qty']),datatype='Int'),
             dict(label='Buồng hủy',value=sum(r.bunch_qty for r in result['cancellations']),datatype='Int'),
             dict(label='Đã chốt ngày',value='Có' if result['closed'] else 'Chưa',datatype='Data')]
    return columns,tasks,None,None,summary
