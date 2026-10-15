"""Import repo work names/UOMs and nine temporary teams; never run demo seed.

Run with bench Python from bench/sites. Default rolls back; --commit saves.
Demo productivity, demo crop cycles, tasks and results are deliberately excluded.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import frappe


def run(args):
    raw=Path(args.source).read_bytes()
    tree=ast.parse(raw.decode('utf8'))
    works=next(ast.literal_eval(node.value) for node in tree.body
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='WORKS' for t in node.targets))
    assert len(works)==8 and len({r[0] for r in works})==8
    categories={'Chăm sóc buồng':'LOTUS-BUNCH','Chăm sóc cây':'LOTUS-PLANT','Trồng và chăm sóc':'LOTUS-GROW'}
    farm=frappe.get_doc('Farm','LOTUS-222')
    assert farm.company=='Lotus Agritech' and farm.active
    before={dt:frappe.db.count(dt) for dt in ('Farm','Farm Block','Farm Plot','Crop Cycle','Daily Work Plan','Stock Entry')}
    created={dt:[] for dt in ('Work Team','Work Category','Work Type','UOM')}

    def ensure(dt,filters,values):
        found=frappe.get_all(dt,filters=filters,fields=['name'])
        if len(found)>1:raise ValueError('Ambiguous existing '+dt+': '+str(filters))
        if found:
            doc=frappe.get_doc(dt,found[0].name)
            for key,value in values.items():
                if key=='productivity_per_workday':continue # preserve later approved configuration
                if doc.get(key)!=value:raise ValueError('Conflicting '+dt+' '+doc.name+': '+key)
            return doc.name
        doc=frappe.get_doc(dict(doctype=dt,**values)).insert()
        created[dt].append(doc.name)
        return doc.name

    team_names=[]
    for i in range(1,10):
        code=f'T{i:02d}'
        team_names.append(ensure('Work Team',dict(farm=farm.name,team_code=code),
            dict(farm=farm.name,team_code=code,team_name=f'Tổ {i:02d} (tạm)',active=1)))
    cat_names={name:ensure('Work Category',dict(category_code=code),
        dict(category_code=code,category_name=name,active=1)) for name,code in categories.items()}
    catalog=[]
    for code,name,uom,_demo_norm,category in works:
        ensure('UOM',dict(uom_name=uom),dict(uom_name=uom))
        values=dict(work_code='LOTUS-'+code,work_name=name,category=cat_names[category],
            uom=uom,productivity_per_workday=0,active=1)
        work=ensure('Work Type',dict(work_code=values['work_code']),values)
        catalog.append(dict(name=work,code=values['work_code'],work_name=name,
            category=category,uom=uom,productivity_per_workday=frappe.db.get_value('Work Type',work,'productivity_per_workday')))
    note='Cấu hình tạm: 9 tổ T01–T09; danh mục 8 công việc/3 nhóm lấy tên và đơn vị từ code repo. Chưa gán tổ trưởng/nhân sự hoặc địa bàn cố định; định mức năng suất mẫu không nhập. Cần cấu hình năng suất và vụ cây trước khi giao việc.'
    if note not in (farm.notes or ''):
        farm.notes=(farm.notes or '')+'\n'+note;farm.save()
    assert before=={dt:frappe.db.count(dt) for dt in before}
    from lotus_farm.mobile_assignment import options
    o=options(farm.name)
    assert set(team_names).issubset({x.name for x in o['teams']})
    assert {r['name'] for r in catalog}.issubset({x.name for x in o['works']})
    assert len(o['plots'])==210 and len(o['blocks'])==64
    report=dict(farm=farm.name,created=created,teams=team_names,work_catalog=catalog,
        source='lotus_farm/mobile_demo_seed.py:WORKS',source_sha256=hashlib.sha256(raw).hexdigest(),
        imported_fields=['work_code','work_name','category','uom','active'],
        excluded_fields=['demo_productivity','demo_farm','demo_variety','demo_cycles','demo_plans','demo_results'],
        planning_options={k:len(o[k]) for k in ('teams','works','blocks','plots')},
        pending=['Cấu hình năng suất được xác nhận','Vụ cây thực tế'],
        status='committed' if args.commit else 'dry_run_rolled_back')
    from frappe.utils.file_manager import save_file
    filename='farm-222-work-catalog-'+report['source_sha256'][:12]+'.json'
    if not frappe.db.exists('File',{'attached_to_doctype':'Farm','attached_to_name':farm.name,
        'file_name':['like',filename.removesuffix('.json')+'%.json']}):
        save_file(filename,json.dumps(report,ensure_ascii=False,indent=2).encode(),'Farm',farm.name,is_private=1)
    Path(args.report).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    if args.commit:frappe.db.commit()
    else:frappe.db.rollback()
    print(json.dumps(dict(status=report['status'],created={k:len(v) for k,v in created.items()},
        options=report['planning_options'],work_names=[r['work_name'] for r in catalog]),ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True)
    p.add_argument('--report',required=True)
    p.add_argument('--site',default='frontend')
    p.add_argument('--commit',action='store_true')
    args=p.parse_args()
    frappe.init(site=args.site);frappe.connect();frappe.set_user('Administrator')
    try:run(args)
    except Exception:
        frappe.db.rollback();raise
    finally:frappe.destroy()
