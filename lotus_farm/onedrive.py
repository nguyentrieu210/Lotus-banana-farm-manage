"""Opt-in Graph folder feeds. Download/stage only; never auto-approve business data."""
import fnmatch
import hashlib
from urllib.parse import urlparse, quote
from pathlib import PurePosixPath
import requests
import frappe
from frappe.utils import nowdate, now_datetime
from lotus_farm.controls import require_role, command, lock
from lotus_farm.rules import canonical_hash
from lotus_farm.extraction import MAX_BYTES


def graph_url(url):
    parsed=urlparse(url)
    if parsed.scheme!='https' or parsed.hostname!='graph.microsoft.com' or not parsed.path.startswith('/v1.0/'):
        frappe.throw('Đường dẫn trang tiếp theo của Graph nằm ngoài máy chủ API được duyệt.')
    return url


def download(session,url):
    response=session.get(graph_url(url),timeout=30,allow_redirects=False)
    if response.status_code in (301,302,303,307,308):
        target=response.headers.get('Location','');host=urlparse(target).hostname or ''
        allowed=host.endswith('.sharepoint.com') or host.endswith('.1drv.com') or host.endswith('.1drvusercontent.com') or host.endswith('.onedrive.com')
        if urlparse(target).scheme!='https' or not allowed:frappe.throw('Máy chủ tải tệp Graph không đúng.')
        # No bearer token is forwarded to the preauthenticated download host.
        response=requests.get(target,timeout=30,stream=True,allow_redirects=False)
    response.raise_for_status()
    chunks=[];size=0
    for chunk in response.iter_content(1024*1024):
        size+=len(chunk)
        if size>MAX_BYTES:response.close();frappe.throw('Nguồn vượt giới hạn sổ Excel đã cấu hình.')
        chunks.append(chunk)
    response.close();return b''.join(chunks)


@frappe.whitelist(methods=['POST'])
def poll_feed(feed):
    require_role('System Manager')
    cfg=frappe.get_doc('OneDrive Feed',feed);cfg.check_permission('write')
    lock('OneDrive Feed',cfg.name);cfg.reload()
    if not cfg.enabled:frappe.throw('Bật nguồn dữ liệu đã duyệt trước khi lấy dữ liệu.')
    previous=frappe.session.user;created=[]
    try:
        token=requests.post('https://login.microsoftonline.com/'+quote(cfg.tenant_id,safe='')+'/oauth2/v2.0/token',
            data={'client_id':cfg.client_id,'client_secret':cfg.get_password('client_secret'),'scope':'https://graph.microsoft.com/.default','grant_type':'client_credentials'},timeout=30)
        token.raise_for_status();access=token.json()['access_token']
        session=requests.Session();session.headers['Authorization']='Bearer '+access
        url=cfg.delta_link or 'https://graph.microsoft.com/v1.0/drives/'+quote(cfg.drive_id,safe='')+'/items/'+quote(cfg.folder_id,safe='')+'/delta'
        frappe.set_user(cfg.integration_user)
        # Bounded paging saves nextLink only after that page has been fully recorded.
        for _ in range(5):
            response=session.get(graph_url(url),timeout=30);response.raise_for_status();page=response.json()
            for item in page.get('value',[]):
                inventory_key=canonical_hash([cfg.name,item['id']])
                existing=frappe.db.get_value('Source Inventory Item',{'inventory_key':inventory_key},'name')
                inventory=frappe.get_doc('Source Inventory Item',existing) if existing else None
                if item.get('deleted'):
                    if inventory:
                        inventory.deleted=1
                        with command(inventory,'source_inventory'):inventory.save()
                    continue
                if not item.get('file'):continue
                metadata=dict(source_family=canonical_hash([cfg.drive_id,item['id']]),
                        source_path=item.get('parentReference',{}).get('path','')+'/'+item['name'],source_filename=item['name'],
                    extension=PurePosixPath(item['name']).suffix.lower(),size_bytes=item.get('size'),source_created_at=item.get('createdDateTime'),source_modified_at=item.get('lastModifiedDateTime'),deleted=0)
                if not inventory:
                    inventory=frappe.get_doc(dict(doctype='Source Inventory Item',farm=cfg.farm,feed=cfg.name,external_item_id=item['id'],inventory_key=inventory_key,**metadata))
                    with command(inventory,'source_inventory'):inventory.insert()
                else:
                    inventory.update(metadata)
                    with command(inventory,'source_inventory'):inventory.save()
                if not fnmatch.fnmatch(item['name'],cfg.filename_pattern):continue
                if int(item.get('size',0))>MAX_BYTES:frappe.throw('Tệp khớp trong nguồn dữ liệu vượt giới hạn sổ Excel.')
                data=download(session,'https://graph.microsoft.com/v1.0/drives/'+quote(cfg.drive_id,safe='')+'/items/'+quote(item['id'],safe='')+'/content')
                hashed=hashlib.sha256(data).hexdigest();source_key=canonical_hash([cfg.drive_id,item['id'],hashed])
                source=frappe.db.get_value('Source File Registry',{'source_key':source_key},'name')
                if not source:
                    source=frappe.get_doc(dict(doctype='Source File Registry',source_key=source_key,
                        source_family=canonical_hash([cfg.drive_id,item['id']]),
                        source_path=item.get('parentReference',{}).get('path','')+'/'+item['name'],source_filename=item['name'],sha256=hashed,
                        business_period=cfg.business_period,source_modified_at=item.get('lastModifiedDateTime'),source_priority=cfg.source_priority,
                        migration_tier=cfg.migration_tier,source_status='Unknown')).insert().name
                inventory.source_file=source
                with command(inventory,'source_inventory'):inventory.save()
                if cfg.migration_tier in ('C','D'):continue
                external=canonical_hash([cfg.drive_id,item['id'],cfg.mapping,cfg.farm]);key=canonical_hash(['Microsoft Graph',external,hashed])
                task=frappe.db.get_value('Integration Task',{'event_key':key},'name')
                if not task:
                    from frappe.utils.file_manager import save_file
                    file=save_file(item['name'],data,'Source File Registry',source,is_private=1)
                    task=frappe.get_doc(dict(doctype='Integration Task',farm=cfg.farm,external_id=external,source_system='Microsoft Graph',source_hash=hashed,
                        source_file=source,mapping=cfg.mapping,file=file.file_url,posting_date=nowdate())).insert().name
                    created.append(task)
                if cfg.auto_stage:
                    from lotus_farm.importing import run_task
                    run_task(task)
            url=page.get('@odata.nextLink') or page.get('@odata.deltaLink')
            if not url:frappe.throw('Trang Graph thiếu điểm tiếp tục.')
            cfg.delta_link=graph_url(url)
            if '@odata.deltaLink' in page:break
        session.close();cfg.last_error=''
    except Exception as exc:
        cfg.last_error=type(exc).__name__+': feed could not finish; check account permissions, source files and mapping.'
    finally:
        frappe.set_user(previous)
    cfg.last_sync_at=now_datetime()
    with command(cfg,'poll_onedrive'):cfg.save()
    return dict(feed=cfg.name,created_tasks=created,error=cfg.last_error)


def scheduled_poll():
    previous=frappe.session.user
    try:
        frappe.set_user('Administrator')
        for name in frappe.get_all('OneDrive Feed',filters={'enabled':1},pluck='name'):
            try:poll_feed(name);frappe.db.commit()
            except Exception:frappe.db.rollback();frappe.log_error('OneDrive feed polling failed; review the feed status.','Lotus source ingestion')
    finally:frappe.set_user(previous)
