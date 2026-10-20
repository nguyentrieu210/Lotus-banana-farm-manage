"""Run on an isolated cloned site. Rolls back every fixture and journal."""
import os
import uuid
import frappe

os.chdir('/home/frappe/frappe-bench/sites')
frappe.init(site='frontend');frappe.connect();frappe.set_user('Administrator')
from lotus_farm import work_journal as j


def expect_error(fn, types=(frappe.ValidationError, frappe.PermissionError, frappe.TimestampMismatchError)):
    point='j_'+uuid.uuid4().hex
    frappe.db.savepoint(point)
    try:
        fn()
    except types:
        frappe.db.rollback(save_point=point)
        return
    raise AssertionError('Expected operation to be denied')


try:
    official_types=['Daily Work Plan','Daily Work Result','Labor Allocation','Attendance','Salary Slip','Stock Entry','Stock Ledger Entry']
    official_before={dt:frappe.db.count(dt) for dt in official_types}
    farm=frappe.get_all('Farm',pluck='name')[0]
    team=frappe.get_all('Work Team',filters={'farm':farm,'active':1},pluck='name')[0]
    block=frappe.get_all('Farm Block',filters={'farm':farm,'active':1},pluck='name')[0]
    work=frappe.get_all('Work Type',filters={'active':1},pluck='name')[0]
    today=frappe.utils.nowdate()
    users={}
    for kind in ('clerk','viewer','outside'):
        user=f'journal-{kind}-{uuid.uuid4().hex[:8]}@example.invalid'
        doc=frappe.get_doc({'doctype':'User','email':user,'first_name':kind,'send_welcome_email':0,'user_type':'System User'})
        doc.insert(ignore_permissions=True)
        if kind=='clerk':doc.add_roles(j.CLERK)
        if kind!='outside':frappe.get_doc({'doctype':'User Permission','user':user,'allow':'Farm','for_value':farm,'apply_to_all_doctypes':1}).insert(ignore_permissions=True)
        users[kind]=user
    frappe.set_user(users['clerk'])
    line={'row_id':str(uuid.uuid4()),'work_team':team,'farm_block':block,'work_type':work,'quantity':None,'workdays':0,'notes':'Nhật ký theo dõi'}
    args={'farm':farm,'date':today,'rows':[line],'expected_modified':None,'request_id':str(uuid.uuid4()),'expected_user':users['clerk']}
    first=j.save(**args)
    assert first['rows'][0]['quantity'] is None and first['rows'][0]['workdays']==0
    original_child_name=frappe.get_doc('Work Daily Journal',first['name']).get('rows')[0].name
    assert j.save(**args)==first
    assert frappe.db.count('Work Daily Journal',{'farm':farm,'posting_date':today})==1
    expect_error(lambda:j.save(**{**args,'rows':[{**line,'notes':'different request payload'}]}))
    changed={**args,'request_id':str(uuid.uuid4()),'expected_modified':first['modified'],'rows':[{**line,'quantity':3.5,'workdays':1.25}]}
    second=j.save(**changed)
    expect_error(lambda:j.save(**{**changed,'request_id':str(uuid.uuid4())}))
    assert j.history(farm,today), 'Changes must produce history'
    for field,value in [('workdays',-1),('quantity','nan'),('work_team',''),('farm_block',''),('work_type','')]:
        expect_error(lambda:j.save(**{**changed,'expected_modified':second['modified'],'request_id':str(uuid.uuid4()),'rows':[{**line,field:value}]}))
    expect_error(lambda:j.save(**{**changed,'expected_user':'another-user'}))
    expect_error(lambda:j.save(**{**changed,'date':'2999-01-01'}))
    assert original_child_name==frappe.get_doc('Work Daily Journal',second['name']).get('rows')[0].name
    frappe.set_user(users['viewer'])
    assert j.get(farm,today)['can_write'] is False
    assert j.summary(farm,today,today)['total_workdays']==1.25
    assert frappe.get_doc('Work Daily Journal',first['name']).has_permission('read')
    expect_error(lambda:j.save(**{**changed,'expected_user':users['viewer'],'request_id':str(uuid.uuid4())}))
    frappe.set_user(users['outside'])
    for fn in (lambda:j.get(farm,today),lambda:j.history(farm,today),lambda:j.summary(farm,today,today),lambda:j.export(farm,today,today)):
        expect_error(fn)
    assert not frappe.get_doc('Work Daily Journal',first['name']).has_permission('read')
    frappe.set_user('Administrator')
    expect_error(lambda:j.save(**{**changed,'expected_modified':second['modified'],'expected_user':'Administrator','request_id':str(uuid.uuid4())}))
    updated=j.save(**{**changed,'expected_modified':second['modified'],'expected_user':'Administrator','request_id':str(uuid.uuid4()),'correction_reason':'Đối chiếu lại Zalo'})
    assert updated['owner']==users['clerk'] and updated['modified_by']=='Administrator'
    doc=frappe.get_doc('Work Daily Journal',first['name'])
    expect_error(lambda:doc.save(ignore_permissions=True))
    expect_error(lambda:frappe.delete_doc('Work Daily Journal',doc.name,ignore_permissions=True))
    assert {dt:frappe.db.count(dt) for dt in official_types}==official_before
    print('PASS: separate journal / null vs zero / stable rows / request retry / optimistic conflict / validation / same-farm readers / outside denial / correction audit / direct write/delete denied')
finally:
    frappe.db.rollback();frappe.destroy()
