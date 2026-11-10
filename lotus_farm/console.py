"""Permission-checked SPA data, paging, metadata and document saves."""
import frappe
from frappe.utils import cint, getdate, nowdate
from lotus_farm.controls import lock
from lotus_farm.scoping import land_scope, land_filters

MODULES={
 'alerts':['Lotus Alert'],
 'farms':['Farm','Farm Block'],
 'forecast':['Lotus Block Forecast Profile'],
 'map':['Farm Block Geometry'],'settings':['Lotus Farm Settings'],
 'mau-day':['Bunch Tag'],
 'masters':['Work Type','Work Team','Cancellation Reason Group','Cancellation Reason','Disease','Market','Bunch Tag','Warehouse Mapping','Work Schedule Rule','Banana Variety']}
ALLOWED={d for names in MODULES.values() for d in names}


def allowed(doctype,permission='read'):
    if doctype not in ALLOWED:frappe.throw('Chứng từ Lotus không được hỗ trợ.')
    if not frappe.has_permission(doctype,permission):frappe.throw('Không có quyền với '+getattr(frappe, "_", str)(doctype),frappe.PermissionError)
    return frappe.get_meta(doctype)


@frappe.whitelist()
def bootstrap():
    from lotus_farm.field import session_info
    from lotus_farm.forecast_snapshot import queue_missing_weeks
    queue_missing_weeks()
    session=session_info()
    session['farms']=frappe.get_list('Farm',fields=['name','farm_name','company'],limit_page_length=1000) if frappe.has_permission('Farm','read') else []
    session['modules']={k:[t for t in types if frappe.has_permission(t,'read')] for k,types in MODULES.items()}
    session['modules']={k:v for k,v in session['modules'].items() if v}
    session['creatable']={t:frappe.has_permission(t,'create') for t in ALLOWED}
    roles=set(frappe.get_roles());admin=frappe.session.user=='Administrator'
    has_role=lambda *names:admin or bool(roles.intersection(names))
    session['today']=nowdate()
    session.setdefault('capabilities',{})['user_admin']=has_role('System Manager') and bool(frappe.has_permission('User','read'))
    session.setdefault('capabilities',{})['hr']=has_role('HR Manager','HR User')
    from lotus_farm.hr_workspace import _is_hr_manager
    session['capabilities']['hr_manage']=session['capabilities']['hr'] and _is_hr_manager()
    session.setdefault('capabilities',{})['attendance']=bool(frappe.db.exists('DocType','Attendance') and frappe.has_permission('Attendance','read')) or bool(frappe.db.exists('DocType','Lotus Crew Attendance') and frappe.has_permission('Lotus Crew Attendance','read'))
    from lotus_farm.field_report import farm_names as report_farms
    session['capabilities']['field_report']=frappe.session.user=='Administrator' or (has_role('Lotus Farm Manager','Lotus Field Supervisor','Lotus Team Leader','Lotus Field Inspector') and bool(report_farms()))
    from lotus_farm.shift import can_open as packhouse_open
    # Xưởng: packhouse supervisors and the accountant who receives shifts into stock are not in the field teams.
    session['capabilities']['packhouse']=frappe.session.user=='Administrator' or (bool(report_farms()) and packhouse_open())
    from lotus_farm.finance.setup import can_view as finance_view
    from lotus_farm.signing_rules import CHIEF_ACCOUNTANTS, DIRECTORS
    installed=bool(frappe.db.exists('DocType','Lotus Finance Settings'))
    # Ledger readers see the whole finance page; payment approvers open it only to sign their vouchers.
    session['capabilities']['finance_ledger']=installed and finance_view()
    session['capabilities']['finance']=session['capabilities']['finance_ledger'] or (installed and has_role(*DIRECTORS, *CHIEF_ACCOUNTANTS))
    session['capabilities']['purchasing']=bool(frappe.has_permission('Purchase Order','read') or frappe.has_permission('Material Request','read')) and all(frappe.has_permission(dt,'read') for dt in ('Company','Warehouse','Item'))
    session['capabilities']['purchasing_finance']=installed and (finance_view() or has_role('Lotus Purchase Approver','Lotus Farm Manager'))
    session['capabilities']['purchasing_invoice_read']=session['capabilities']['purchasing_finance'] and frappe.has_permission('Purchase Invoice','read')
    # ERPNext/HRMS sections added into Kho, Mua hàng, Tài chính, Nhân sự (lotus_farm.erp_catalog), filtered by permission.
    from lotus_farm import erp_workbench
    session['erp_sections']=erp_workbench.catalog()['sections'] if erp_workbench.can_access() else {}
    if session['capabilities']['field_report'] or session['capabilities']['packhouse']:
        existing = {f['name'] for f in session['farms']}
        session['farms'] += frappe.get_all('Farm', filters={'name': ['in', [f for f in report_farms() if f not in existing] or ['']]}, fields=['name','farm_name','company'])
    return session


@frappe.whitelist()
def schema(doctype):
    meta=allowed(doctype)
    def fields(m):
        return [{k:f.get(k) for k in ('fieldname','label','fieldtype','options','reqd','read_only','default','description','depends_on')} for f in m.fields if f.fieldtype not in ('Section Break','Column Break','Tab Break','HTML','Button')]
    return dict(doctype=doctype,title_field=meta.title_field,fields=fields(meta),
        tables={f.options:fields(frappe.get_meta(f.options)) for f in meta.fields if f.fieldtype=='Table'},
        permissions={p:frappe.has_permission(doctype,p) for p in ('create','write')})


@frappe.whitelist()
def listing(doctype,farm=None,company=None,block=None,status=None,date=None,from_date=None,to_date=None,search=None,start=0,length=50,sort='modified desc',column_filters=None,include_filter_values=False,zone=None):
    meta=allowed(doctype)
    selected=land_scope(company,farm,block,zone=zone)
    filters=land_filters(meta,selected)
    # A table that has a farm but no lô cannot honour a khu/lô filter.
    if doctype not in ('Farm','Farm Block') and (zone or block) and meta.has_field('farm') and not meta.has_field('farm_block'):
        frappe.throw('Chứng từ này chỉ lọc theo vườn; hãy bỏ lọc khu/lô.')
    date_field='posting_date'
    if meta.has_field(date_field):
        if from_date and to_date:filters[date_field]=['between',[getdate(from_date),getdate(to_date)]]
        elif from_date:filters[date_field]=['>=',getdate(from_date)]
        elif to_date:filters[date_field]=['<=',getdate(to_date)]
        elif date:filters[date_field]=getdate(date)
    if from_date and to_date and getdate(from_date)>getdate(to_date):frappe.throw('Từ ngày không được sau Đến ngày.')
    status_field=next((f for f in ('approval_state','status') if meta.has_field(f)), 'docstatus')
    if status not in (None,''):
        choices=(meta.get_field(status_field).options or '').split('\n') if status_field!='docstatus' else ['0','1','2']
        if str(status) not in choices:frappe.throw('Trạng thái không hợp lệ với chứng từ này.')
        filters[status_field]=cint(status) if status_field=='docstatus' else status
    if search:filters=[[k,*(v if isinstance(v,list) else ['=',v])] for k,v in filters.items()]+[['name','like','%'+search[:100]+'%']]
    candidates=['name','docstatus','modified',meta.title_field,'company','farm','farm_block',date_field,'approval_state','status','area_ha','variety','planting_date','block_code']
    columns=list(dict.fromkeys(f for f in candidates if f and (f in ('name','docstatus','modified') or meta.has_field(f))))
    if sort not in ('modified desc','modified asc','name asc','name desc'):frappe.throw('Kiểu sắp xếp không được hỗ trợ.')
    from lotus_farm.table_filters import selections, distinct, matches
    selected_columns=selections(column_filters,columns)
    all_rows=frappe.get_list(doctype,filters=filters,fields=columns,order_by=sort+', name',limit_page_length=0) if cint(include_filter_values) or selected_columns else None
    filter_values=distinct(all_rows,columns) if cint(include_filter_values) else None
    length=max(1,min(cint(length),100));start=max(cint(start),0)
    rows=([row for row in all_rows if matches(row,selected_columns)][start:start+length+1] if all_rows is not None else
          frappe.get_list(doctype,filters=filters,fields=columns,order_by=sort+', name',limit_start=start,limit_page_length=length+1))
    choices=(meta.get_field(status_field).options or '').split('\n') if status_field!='docstatus' else ['0','1','2']
    return dict(rows=rows[:length],columns=columns,filter_values=filter_values,has_more=len(rows)>length,start=start,length=length,status_options=[c for c in choices if c])


@frappe.whitelist()
def scope_options(company=None,farm=None,block=None,zone=None):
    selected=land_scope(company,farm,block,zone=zone)
    from lotus_farm.reporting import records
    result={'scope':{k:v for k,v in selected.items() if k!='zone_blocks'},'zones':[],'blocks':[]}
    if selected['farm']:
        result['zones']=sorted({b.farm_zone for b in records('Farm Block',{'farm':selected['farm']},['farm_zone']) if b.farm_zone}) if frappe.has_permission('Farm Block','read') else []
        result['blocks']=records('Farm Block',{'farm':selected['farm'],**({'farm_zone':zone} if zone else {})},['name','block_name','block_code','farm_zone']) if frappe.has_permission('Farm Block','read') else []
    return result


@frappe.whitelist()
def detail(doctype,name):
    allowed(doctype);doc=frappe.get_doc(doctype,name);doc.check_permission('read')
    return doc.as_dict()


@frappe.whitelist()
def link_options(doctype,search='',farm=None,company=None):
    if not frappe.has_permission(doctype,'read'):frappe.throw('Cần quyền đọc dữ liệu liên kết.',frappe.PermissionError)
    meta=frappe.get_meta(doctype);filters={}
    if farm and meta.has_field('farm'):filters['farm']=farm
    if company and meta.has_field('company'):filters['company']=company
    title=meta.title_field or 'name'
    rows=frappe.get_list(doctype,filters=filters,or_filters={'name':['like','%'+search[:80]+'%'],title:['like','%'+search[:80]+'%']} if search else None,fields=list(dict.fromkeys(['name',title])),limit_page_length=500 if doctype=='UOM' else 30,order_by='name')
    return [dict(value=r.name,label=r.get(title) or r.name) for r in rows]


def payload_fields(meta,values):
    if not isinstance(values,dict):frappe.throw('Dữ liệu trường của chứng từ phải là một đối tượng.')
    editable={f.fieldname:f for f in meta.fields if not f.read_only and f.fieldtype not in ('Section Break','Column Break','Tab Break','HTML','Button')}
    if set(values)-set(editable):frappe.throw('Dữ liệu gửi lên có trường được bảo vệ hoặc không được hỗ trợ.')
    result={}
    for key,value in values.items():
        field=editable[key]
        if field.fieldtype=='Table':
            if not isinstance(value,list):frappe.throw('Bảng con phải là một danh sách.')
            if len(value)>1000:frappe.throw('Bảng con quá 1.000 dòng; hãy tách nhỏ.')
            result[key]=[payload_fields(frappe.get_meta(field.options),v) for v in value]
        else:result[key]=value
    return result


def _settings_result(doc,meta):
    from lotus_farm.rules import canonical_hash
    result=doc.as_dict()
    result['_settings_token']=canonical_hash([[f.fieldname,doc.get(f.fieldname)] for f in meta.fields])
    return result


@frappe.whitelist()
def settings():
    meta=allowed('Lotus Farm Settings')
    doc=frappe.get_single('Lotus Farm Settings');doc.check_permission('read')
    return _settings_result(doc,meta)


@frappe.whitelist(methods=['POST'])
def save_settings(values,base_token=None):
    meta=allowed('Lotus Farm Settings','write')
    values=frappe.parse_json(values) if isinstance(values,str) else values
    clean=payload_fields(meta,values)
    doc=frappe.get_single('Lotus Farm Settings');doc.check_permission('write')
    frappe.db.sql("select field from tabSingles where doctype=%s for update",('Lotus Farm Settings',))
    doc.reload()
    current=_settings_result(doc,meta)
    if base_token and current['_settings_token']!=base_token:frappe.throw('Thiết lập vừa được người khác thay đổi. Tải lại trước khi lưu; dữ liệu bạn nhập chưa ghi đè lên.')
    doc.update(clean);doc.save()
    return _settings_result(doc,meta)


@frappe.whitelist(methods=['POST'])
def save(doctype,values,name=None,base_modified=None):
    meta=allowed(doctype,'write' if name else 'create')
    values=frappe.parse_json(values) if isinstance(values,str) else values
    clean=payload_fields(meta,values)
    if name:
        doc=frappe.get_doc(doctype,name);doc.check_permission('write')
        if doc.get('farm'):lock('Farm',doc.farm)
        lock(doctype,name);doc.reload()
        if str(doc.modified)!=str(base_modified):frappe.throw('Chứng từ vừa thay đổi. Tải lại trước khi lưu; dữ liệu bạn nhập chưa ghi đè lên.')
        doc.update(clean);doc.save()
    else:
        doc=frappe.get_doc(dict(doctype=doctype,**clean));doc.insert()
    return doc.as_dict()


@frappe.whitelist()
def audit(doctype,name):
    allowed(doctype);doc=frappe.get_doc(doctype,name);doc.check_permission('read')
    return dict(owner=doc.owner,created=doc.creation,modified_by=doc.modified_by,modified=doc.modified,
        versions=frappe.get_all('Version',filters={'ref_doctype':doctype,'docname':name},fields=['name','creation','owner','data'],order_by='creation desc',limit_page_length=100),
        comments=frappe.get_all('Comment',filters={'reference_doctype':doctype,'reference_name':name,'comment_type':'Comment'},fields=['creation','owner','content'],order_by='creation desc',limit_page_length=100))
