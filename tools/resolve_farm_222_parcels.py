"""Apply owner-confirmed split codes to Farm 222; dry run unless --commit."""
import argparse
import hashlib
import json
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
import frappe


def apply(args):
    raw = Path(args.resolutions).read_bytes()
    data = json.loads(raw)
    assert data['format'] == 'lotus-farm-222-parcel-resolutions-v1'
    farm = data['farm']
    doc = frappe.get_doc('Farm', farm)
    assert doc.company == 'Lotus Agritech'
    rows = data['resolutions']
    assert len({r['code'] for r in rows}) == len(rows)
    assert len({(r['source_code'],r['parent_block']) for r in rows}) == len(rows), 'Merge components of the same source code and block before importing'
    report = dict(farm=farm, created=[], adjusted_existing=[], resolutions=rows,
                  remaining_unresolved=data['remaining_unresolved'])
    for code in sorted({r['parent_block'] for r in rows}):
        block = frappe.get_doc('Farm Block', {'farm':farm,'block_code':code})
        incoming = [r for r in rows if r['parent_block']==code]
        new_codes = {r['code'] for r in incoming}
        existing = frappe.get_all('Farm Plot',filters={'farm':farm,'farm_block':block.name},
            fields=['name','plot_code','area_ha','active'])
        siblings = [p for p in existing if p.plot_code not in new_codes and p.active]
        capacity = Decimal(str(block.area_ha)) - sum((Decimal(str(r['area_ha'])) for r in incoming), Decimal(0))
        total = sum((Decimal(str(p.area_ha)) for p in siblings), Decimal(0))
        if capacity <= 0:
            raise ValueError('Invalid remaining block area: '+code)
        if total > capacity:
            # Preserve exact areas confirmed by the owner; reduce only the previous
            # source-derived planning areas to fit the rounded PDF block total.
            scale = capacity / total
            for p in siblings:
                updated = (Decimal(str(p.area_ha))*scale).quantize(Decimal('.000001'),rounding=ROUND_DOWN)
                target = frappe.get_doc('Farm Plot',p.name)
                target.area_ha = float(updated)
                target.save()
                report['adjusted_existing'].append(dict(code=p.plot_code,block=code,
                    old_area_ha=p.area_ha,planning_area_ha=float(updated)))
        for r in incoming:
            assert r['confirmation']=='user-confirmed'
            assert abs(sum(r['component_areas_ha'])-r['area_ha'])<1e-9
            if frappe.db.exists('Farm Plot',{'farm':farm,'plot_code':r['source_code']}):
                raise ValueError('Source plot exists; resolve its history first')
            found = frappe.get_all('Farm Plot',filters={'farm':farm,'plot_code':r['code']},
                fields=['name','farm_block','area_ha'])
            if found:
                assert len(found)==1 and found[0].farm_block==block.name
                assert abs(found[0].area_ha-r['area_ha'])<1e-6
            else:
                p = frappe.get_doc(dict(doctype='Farm Plot',farm=farm,company=doc.company,
                    farm_block=block.name,plot_code=r['code'],plot_name='Thửa tưới '+r['code'],
                    area_ha=r['area_ha'],active=1)).insert()
                report['created'].append(r['code'])
        note = 'Xác nhận chủ nông trường 2026-10-14: '+ '; '.join(
            r['code']+' = '+' + '.join(str(a) for a in r['component_areas_ha'])+
            ' ha, tách từ '+r['source_code'] for r in incoming)+'. Ranh mới chờ rà soát.'
        if note not in (block.notes or ''):
            block.notes=(block.notes or '')+'\n'+note
            if total>capacity:
                block.notes+=' Diện tích thửa nguồn khác giảm theo tỷ lệ để khớp số lô PDF làm tròn; lưu báo cáo riêng tư.'
            block.save()
    status_note = 'Xác nhận tách mã hiện tại: '+str(len(rows))+' thửa; còn chờ xác nhận: '+(', '.join(data['remaining_unresolved']) or 'không còn')+'. Các phần cùng mã gốc và lô cha đã gộp diện tích; mã gốc khác nhau giữ riêng.'
    if status_note not in (doc.notes or ''):
        doc.notes=(doc.notes or '')+'\n'+status_note
        doc.save()
    from frappe.utils.file_manager import save_file
    digest=hashlib.sha256(raw).hexdigest()[:12]
    for filename,content in [('farm-222-resolutions-'+digest+'.json',raw),
        ('farm-222-resolution-report-'+digest+'.json',json.dumps(report,ensure_ascii=False,indent=2).encode())]:
        if not frappe.db.exists('File',{'attached_to_doctype':'Farm','attached_to_name':farm,
            'file_name':['like',filename.removesuffix('.json')+'%.json']}):
            save_file(filename,content,'Farm',farm,is_private=1)
    report['plot_count']=frappe.db.count('Farm Plot',{'farm':farm})
    assert report['plot_count']==200+len(rows)
    if args.commit:frappe.db.commit()
    else:frappe.db.rollback()
    report['status']='committed' if args.commit else 'dry_run_rolled_back'
    Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k!='resolutions'},ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--resolutions',required=True)
    p.add_argument('--report',required=True)
    p.add_argument('--site',default='frontend')
    p.add_argument('--commit',action='store_true')
    args=p.parse_args()
    frappe.init(site=args.site);frappe.connect();frappe.set_user('Administrator')
    try:apply(args)
    except Exception:
        frappe.db.rollback();raise
    finally:frappe.destroy()
