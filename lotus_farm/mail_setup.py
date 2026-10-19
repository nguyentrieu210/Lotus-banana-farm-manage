"""Configure native Frappe mail through Resend; credentials stay encrypted in Email Account."""
import json
from pathlib import Path
from urllib.request import Request, urlopen
import frappe

DOMAIN_ID='6294fb81-c7bc-4f2a-8682-4410dd4fdeeb'
SENDER='no-reply@lotus.gpcds.site'
TEMPLATES={
    'Lotus - Đặt lại mật khẩu':('Đặt lại mật khẩu Lotus Agritech','password_reset'),
    'Lotus - Chào mừng':('Chào mừng bạn đến với Lotus Agritech','welcome'),
    'Lotus - Thông báo':('Lotus Agritech · {{ title|default("Thông báo",true) }}','notification'),
    'Lotus - Nhắc công việc':('Lotus Agritech · Nhắc công việc {{ doc.name if doc is defined else name|default("") }}','work_reminder'),
    'Lotus - Phê duyệt chứng từ':('Lotus Agritech · Chứng từ cần xử lý {{ doc.name if doc is defined else name|default("") }}','approval'),
}

def configure(key_path):
    frappe.only_for('System Manager')
    key=Path(key_path).read_text().strip()
    if not key.startswith('re_'):frappe.throw('Invalid Resend credential file')
    request=Request('https://api.resend.com/domains/'+DOMAIN_ID,headers={'Authorization':'Bearer '+key,'User-Agent':'Lotus-Mail-Setup'})
    with urlopen(request,timeout=20) as response:domain=json.load(response)
    verified=domain.get('status')=='verified'
    name='Lotus Agritech'
    account=frappe.get_doc('Email Account',name) if frappe.db.exists('Email Account',name) else frappe.new_doc('Email Account')
    account.update(dict(email_account_name=name,email_id=SENDER,service='',enable_incoming=0,
        smtp_server='smtp.resend.com',smtp_port='465',use_ssl_for_outgoing=1,use_tls=0,
        login_id_is_different=1,login_id='resend',password=key,no_smtp_authentication=0,
        enable_outgoing=int(verified),default_outgoing=int(verified),
        always_use_account_email_id_as_sender=1,always_use_account_name_as_sender_name=1))
    account.save()
    root=Path(frappe.get_app_path('lotus_farm','templates','emails'))
    for name,(subject,filename) in TEMPLATES.items():
        template=frappe.get_doc('Email Template',name) if frappe.db.exists('Email Template',name) else frappe.new_doc('Email Template')
        template.update(dict(name=name,subject=subject,use_html=1,response_html=(root/(filename+'.html')).read_text(encoding='utf8')))
        template.save()
    settings=frappe.get_single('System Settings')
    settings.reset_password_template='Lotus - Đặt lại mật khẩu'
    settings.welcome_email_template='Lotus - Chào mừng'
    settings.save()
    frappe.db.commit()
    frappe.clear_cache()
    return dict(account=account.name,sender=SENDER,domain_status=domain.get('status'),outgoing_enabled=verified,
                templates=list(TEMPLATES),public_url=frappe.utils.get_url())
