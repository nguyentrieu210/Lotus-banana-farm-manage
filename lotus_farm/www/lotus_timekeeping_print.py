import frappe
from base64 import b64encode
from pathlib import Path
from urllib.parse import urlencode
import re
no_cache=1


def get_context(context,company=None,month=None,kind=None,farm=None):
    from lotus_farm.timekeeping import monthly,crew_monthly,_company
    args=frappe.form_dict
    company=company or args.get('company');month=month or args.get('month');kind=kind or args.get('kind') or 'staff';farm=farm or args.get('farm')
    if kind not in ('staff','crew'):frappe.throw('Loại bảng công không hợp lệ.')
    dt='Attendance' if kind=='staff' else 'Lotus Crew Attendance'
    if not frappe.has_permission(dt,'print'):frappe.throw('Chưa có quyền in bảng công.',frappe.PermissionError)
    doc=_company(company)
    context.data=monthly(company,month) if kind=='staff' else crew_monthly(company,month,farm)
    context.info=frappe._dict(company=company);context.project_label=re.sub(r'^\s*dự\s+án\s+chuối\b','VƯỜN CHUỐI',doc.get('lotus_print_project') or '',flags=re.IGNORECASE);context.farm_label=doc.get('lotus_print_farm') or ''
    context.logo_data='data:image/jpeg;base64,'+b64encode(Path(frappe.get_app_path('lotus_farm','public','images','lotus-agritech.jpg')).read_bytes()).decode('ascii')
    context.kind=kind;context.month_label=str(month)[5:7]+'/'+str(month)[:4]
    context.label='Nhân sự chính thức' if kind=='staff' else 'Đội khoán'
    context.codes={'Present':'X','Absent':'V','Half Day':'½','Work From Home':'TX','On Leave':'P'}
    context.number=lambda v:format(float(v or 0),',.3f').rstrip('0').rstrip('.').replace(',','_').replace('.',',').replace('_','.')
    context.pdf_url='/api/method/lotus_farm.www.lotus_timekeeping_print.download_pdf?'+urlencode(dict(company=company,month=month,kind=kind,**({'farm':farm} if farm else {})))
    context.no_cache=1


@frappe.whitelist()
def download_pdf(company,month,kind='staff',farm=None):
    from frappe.utils.pdf import get_pdf
    context=frappe._dict();get_context(context,company,month,kind,farm)
    content=get_pdf(frappe.render_template('lotus_farm/www/lotus_timekeeping_print.html',context),options={'page-size':'A4','orientation':'Landscape','print-media-type':None})
    frappe.local.response.filename='bang-cong-'+kind+'-'+str(month)+'.pdf';frappe.local.response.filecontent=content;frappe.local.response.type='pdf';frappe.local.response.display_content_as='attachment'
