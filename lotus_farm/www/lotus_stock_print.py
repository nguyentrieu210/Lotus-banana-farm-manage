"""Full, permission-checked stock print. No virtualized grid or Desk redirect."""
import frappe
from frappe.utils import flt,getdate,strip_html
import re
no_cache=1


def get_context(context,doctype=None,name=None):
    dt=doctype or frappe.form_dict.get('doctype');name=name or frappe.form_dict.get('name')
    if dt in ('Stock Entry','Stock Reconciliation'):
        from lotus_farm.warehouse import document
        info=document(dt,name)
        title={'Material Receipt':'PHIẾU NHẬP KHO','Material Issue':'PHIẾU XUẤT KHO','Material Transfer':'PHIẾU CHUYỂN KHO','Opening Stock':'PHIẾU TỒN ĐẦU KỲ'}.get(info['kind'],'PHIẾU KIỂM KÊ')
    elif dt in ('Purchase Receipt','Material Request'):
        from lotus_farm.warehouse_planning import purchase_receipt,purchase_request
        info=(purchase_receipt if dt=='Purchase Receipt' else purchase_request)(name)
        title='PHIẾU NHẬN HÀNG' if dt=='Purchase Receipt' else 'ĐỀ NGHỊ MUA VẬT TƯ'
    else:frappe.throw('Loại phiếu không hỗ trợ in.',frappe.PermissionError)
    doc=frappe.get_doc(dt,name);doc.check_permission('read');doc.check_permission('print')
    context.farm_label=frappe.get_cached_value('Company',info['company'],'lotus_print_farm') or ''
    context.company_label=frappe.get_cached_value('Company',info['company'],'company_name') or info['company']
    # Older Company settings may still say 'DỰ ÁN CHUỐI'; print uses the actual garden name.
    raw_garden_label=frappe.get_cached_value('Company',info['company'],'lotus_print_project') or ''
    context.project_label=re.sub(r'^\s*dự\s+án\s+chuối\b', 'VƯỜN CHUỐI', raw_garden_label, flags=re.IGNORECASE)
    from base64 import b64encode
    from pathlib import Path
    context.logo_data='data:image/png;base64,'+b64encode(Path(frappe.get_app_path('lotus_farm','public','images','lotus-agritech-header-v2.png')).read_bytes()).decode('ascii')
    context.info=info;context.heading=title;context.date=getdate(doc.get('posting_date') or doc.get('transaction_date')).strftime('%d/%m/%Y')
    context.extra_costs=[dict(description=strip_html(row.get('description') or '').strip() or row.get('expense_account') or 'Chi phí phụ khác',amount=flt(row.get('amount')))
                         for row in info.get('additional_costs',[]) if flt(row.get('amount'))]
    context.extra_cost_total=flt(info.get('additional_total')) or sum(row['amount'] for row in context.extra_costs)
    context.notes=strip_html(doc.get('remarks') or '')
    context.owner=doc.owner;context.show_cost=dt=='Purchase Receipt' or info.get('kind')=='Material Receipt'
    context.units={'Kg':'kg','Litre':'Lít','Nos':'Cái','Tonne':'Tấn','Gram':'g','Millilitre':'ml','Box':'Hộp / thùng','Pair':'Đôi','Meter':'Mét','Unit':'Đơn vị'}
    context.number=lambda value:format(float(value or 0),',.3f').rstrip('0').rstrip('.').replace(',','_').replace('.',',').replace('_','.')
    context.no_cache=1
    from urllib.parse import urlencode
    context.pdf_url='/api/method/lotus_farm.www.lotus_stock_print.download_pdf?'+urlencode({'doctype':dt,'name':name})


@frappe.whitelist()
def download_pdf(doctype,name):
    from frappe.utils.pdf import get_pdf
    from re import sub
    context=frappe._dict();get_context(context,doctype,name)
    html=frappe.render_template('lotus_farm/www/lotus_stock_print.html',context)
    content=get_pdf(html,options={'page-size':'A4','print-media-type':None})
    frappe.local.response.filename=sub(r'[^A-Za-z0-9._-]+','_',name)[:100]+'.pdf'
    frappe.local.response.filecontent=content
    frappe.local.response.type='pdf'
    frappe.local.response.display_content_as='attachment'
