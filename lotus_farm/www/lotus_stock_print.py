"""Full, permission-checked stock print. No virtualized grid or Desk redirect."""
import frappe
from frappe.utils import getdate,strip_html
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
    context.info=info;context.heading=title;context.date=getdate(doc.get('posting_date') or doc.get('transaction_date')).strftime('%d/%m/%Y')
    context.status=['NHÁP — CHƯA GHI SỔ','ĐÃ GHI SỔ','ĐÃ HỦY'][doc.docstatus]
    if dt=='Material Request':context.status=['NHÁP — CHƯA DUYỆT','ĐÃ DUYỆT','ĐÃ HỦY'][doc.docstatus]
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
