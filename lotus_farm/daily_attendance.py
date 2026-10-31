"""One employee/day row with independent morning/afternoon presence, backed by HRMS Attendance."""
import hashlib
import json
from datetime import datetime, time

import frappe
from frappe.utils import cint, flt, get_datetime, getdate, nowdate
from lotus_farm import timekeeping as t
from lotus_farm.controls import lock
from lotus_farm.presence_rules import POLICY,presence_session,presence_status

FIELDS=['name','employee','status','working_hours','docstatus','modified','shift','in_time','out_time',
    'lotus_note','lotus_overtime_hours','lotus_presence_mode','lotus_morning_present','lotus_afternoon_present',
    'lotus_morning_punch','lotus_afternoon_punch','lotus_allowance','lotus_allowance_amount']


def values(day,entry):
    result={}
    for session in ('morning','afternoon'):
        flag=entry.get(session+'_present',0)
        if flag not in (0,1,False,True,'0','1'):
            frappe.throw('Chọn có mặt hoặc vắng cho từng buổi.')
        flag=cint(flag)
        stamp=entry.get(session+'_time') if flag else None
        if stamp:
            stamp=get_datetime(stamp)
            if stamp.date()!=day or presence_session(stamp)!=session:
                frappe.throw('Giờ chấm không thuộc buổi/ngày công đã chọn.')
        result[session+'_present']=flag
        result[session+'_time']=str(stamp) if stamp else None
    count=result['morning_present']+result['afternoon_present']
    result.update(status=('Absent','Half Day','Present')[count],working_hours=count*4)
    return result


def set_presence(doc,presence):
    doc.lotus_presence_mode=1
    for session in ('morning','afternoon'):
        doc.set('lotus_'+session+'_present',presence[session+'_present'])
        doc.set('lotus_'+session+'_punch',presence[session+'_time'])
    doc.shift=None
    doc.in_time=doc.out_time=None
    doc.late_entry=doc.early_exit=0
    doc.lotus_shift_start=doc.lotus_shift_end=None


def saved_presence(record):
    if record.get('lotus_presence_mode'):
        return {**{s+'_present':cint(record.get('lotus_'+s+'_present')) for s in ('morning','afternoon')},
            **{s+'_time':str(record.get('lotus_'+s+'_punch')) if record.get('lotus_'+s+'_punch') else None for s in ('morning','afternoon')}}
    # Read legacy documents without changing their approved hours or meaning.
    clocks=presence_status(getdate(record.get('attendance_date') or nowdate()),[])
    for stamp in (record.get('in_time'),record.get('out_time')):
        if stamp:
            session='morning' if get_datetime(stamp).hour<12 else 'afternoon'
            if not clocks.get(session+'_time'):clocks[session+'_time']=str(stamp)
    full=record.get('status') in ('Present','Work From Home')
    half=record.get('status')=='Half Day'
    if record.get('shift') and 0<flt(record.get('working_hours'))<8:
        from lotus_farm.checkin_rules import _clock
        start=_clock(frappe.get_cached_value('Shift Type',record['shift'],'start_time'))
        if start:
            clocks['morning_present']=int(start.hour<12)
            clocks['afternoon_present']=int(start.hour>=12)
            return {k:clocks[k] for k in ('morning_present','afternoon_present','morning_time','afternoon_time')}
    clocks['morning_present']=int(full or (half and not clocks.get('afternoon_time')))
    clocks['afternoon_present']=int(full or (half and bool(clocks.get('afternoon_time'))))
    return {k:clocks[k] for k in ('morning_present','afternoon_present','morning_time','afternoon_time')}


def board(company,date,search=None,sync=1):
    from lotus_farm import attendance_day as ad
    from lotus_farm.hr_period import holiday_map,is_closed
    t._company(company);day=t._date(date)
    if not frappe.has_permission('Attendance','read'):
        frappe.throw('Chưa có quyền đọc chấm công.',frappe.PermissionError)
    synced=ad.sync_day(company,day) if cint(sync) else None
    people=t._day_people(company,day)
    records=frappe.get_list('Attendance',filters={'company':company,'attendance_date':day,'docstatus':['<',2]},
        fields=FIELDS,order_by='docstatus desc, name',limit_page_length=0)
    saved={}
    for record in records:saved.setdefault(record.employee,[]).append(record)
    punches={};readable=False
    if frappe.has_permission('Employee Checkin','read'):
        try:
            rows=frappe.get_list('Employee Checkin',filters={'employee':['in',[p.name for p in people] or ['']],
                'time':['between',[datetime.combine(day,time.min),datetime.combine(day,time.max)]]},
                fields=['name','employee','time','log_type'],order_by='time, name',limit_page_length=0)
            for row in rows:punches.setdefault(row.employee,[]).append(row)
            readable=True
        except frappe.PermissionError:pass
    closed=is_closed(company,day);result=[];counts=dict(matching=0,review=0,manual=0)
    # Buổi worked on a khoán phiếu (công việc ngoài vườn) are paid by the phiếu, not as công nhật.
    khoan={}
    if frappe.db.table_exists('Lotus Work Session'):
        for s in frappe.get_all('Lotus Work Session',filters={'company':company,'posting_date':day,'pay_mode':['in',['Count','Lot']]},
                fields=['employee','session'],limit_page_length=0):
            khoan.setdefault(s.employee,[]).append('morning' if s.session=='Morning' else 'afternoon')
    for person in people:
        if search and str(search).casefold() not in (person.name+' '+person.employee_name).casefold():continue
        docs=saved.get(person.name,[]);record=docs[0] if len(docs)==1 else None
        proposal=presence_status(day,punches.get(person.name,[])) if readable else None
        if proposal:
            proposal['clean']=bool(proposal['morning_present'] and proposal['afternoon_present'] or
                (day<getdate(nowdate()) and proposal['workdays']>0))
        row=dict(employee=person.name,employee_name=person.employee_name,department=person.department,designation=person.designation,
            row_key=person.name,name=None,modified=None,status='',working_hours=0,overtime_hours=0,note='',docstatus=0,
            shift=None,in_time=None,out_time=None,late_entry=0,early_exit=0,daily_presence=True,records=docs,
            morning_present=0,afternoon_present=0,morning_time=None,afternoon_time=None,allowance=0,allowance_amount=0)
        if proposal:
            row.update({k:proposal[k] for k in ('status','working_hours','morning_present','afternoon_present','morning_time','afternoon_time')})
        if record:
            row.update(name=record.name,modified=str(record.modified),status=record.status,working_hours=flt(record.working_hours),
                overtime_hours=flt(record.lotus_overtime_hours),note=record.lotus_note or '',docstatus=record.docstatus,
                allowance=cint(record.get('lotus_allowance')),allowance_amount=flt(record.get('lotus_allowance_amount')),
                **saved_presence(record))
        row['khoan_sessions']=khoan.get(person.name,[])
        row['legacy_conflict']=len(docs)>1
        if row['legacy_conflict']:
            row.update(status='Present' if sum(flt(d.working_hours) for d in docs)>=8 else 'Half Day',
                working_hours=sum(flt(d.working_hours) for d in docs),docstatus=1)
            for doc in docs:
                old=saved_presence(doc)
                for session in ('morning','afternoon'):
                    row[session+'_present']=max(row[session+'_present'],old[session+'_present'])
        same=False
        if proposal:
            same=not record or (bool(record.get('lotus_presence_mode')) and row['status']==proposal['status']
                and all(flt(row.get(k))==flt(proposal.get(k)) for k in ('working_hours','morning_present','afternoon_present'))
                and all((str(get_datetime(row[k])) if row.get(k) else '')==(str(get_datetime(proposal[k])) if proposal.get(k) else '') for k in ('morning_time','afternoon_time'))
                and row['overtime_hours']==0)
        row.update(machine=proposal,manual=bool(record and proposal and not same),
            matches=bool(proposal and proposal['clean'] and same and row['docstatus']==0 and not docs[1:] and not closed))
        row['workdays']=round(row['working_hours']/8,3)
        row['review_hash']=hashlib.sha256(json.dumps(dict(policy=POLICY,row_key=row['row_key'],records=docs,evidence=punches.get(person.name,[])),
            sort_keys=True,default=str).encode()).hexdigest()
        counts['matching']+=row['matches'];counts['review']+=row['legacy_conflict'];counts['manual']+=row['manual']
        result.append(row)
    holidays=holiday_map(company,day,day)
    holiday=frappe.db.get_value('Holiday',{'parent':holidays.name,'holiday_date':day},['description','weekly_off'],as_dict=True) if holidays else None
    return dict(rows=result,date=str(day),counts=counts,holiday=dict(holiday) if holiday else None,has_calendar=bool(holidays),
        period_closed=closed,synced=synced,can_sync=ad._can_sync(),machine_readable=readable,missing_shift_count=0,daily_presence=True)


def save(company,date,rows,client_event_id):
    t._company(company);day=t._date(date);entries=frappe.parse_json(rows)
    t._request(client_event_id,[])
    if not isinstance(entries,list) or not 1<=len(entries)<=300:frappe.throw('Chọn từ 1 đến 300 nhân viên.')
    lock('Company',company);names=[];seen=set()
    from lotus_farm.warehouse import _number
    for entry in sorted(entries,key=lambda r:str(r.get('employee'))):
        employee=t._employee(entry.get('employee'),company,day=day)
        if employee.name in seen:frappe.throw('Nhân viên bị trùng trong danh sách.')
        seen.add(employee.name);presence=values(day,entry)
        overtime=_number(entry.get('overtime_hours') or 0,'Giờ tăng ca',allow_zero=True)
        if overtime>16 or (presence['status']=='Absent' and overtime):frappe.throw('Giờ tăng ca không hợp lệ.')
        # Clients that do not send allowance keep what the day already has.
        allowance=None if entry.get('allowance') is None else cint(entry.get('allowance'))
        if allowance and presence['status']=='Absent':frappe.throw(employee.employee_name+': vắng cả ngày, không có phụ cấp.')
        payload=dict(company=company,date=str(day),employee=employee.name,overtime=overtime,note=str(entry.get('note') or '')[:2000],
            allowance=allowance,**presence)
        key,digest=t._request(str(client_event_id)+':presence:'+employee.name,payload)
        retry=frappe.db.get_value('Attendance',{'lotus_client_key':key},['name','lotus_payload_hash'],as_dict=True)
        if retry:
            doc=frappe.get_doc('Attendance',retry.name);doc.check_permission('read')
            if retry.lotus_payload_hash!=digest:frappe.throw('Yêu cầu đã lưu với nội dung khác.')
            names.append(doc.name);continue
        existing=frappe.get_all('Attendance',filters={'employee':employee.name,'attendance_date':day,'docstatus':['<',2]},pluck='name',limit_page_length=0)
        if entry.get('name'):
            doc=frappe.get_doc('Attendance',entry['name']);doc.check_permission('write')
            if existing!=[doc.name] or doc.company!=company or doc.docstatus!=0 or str(doc.modified)!=str(entry.get('modified')):
                frappe.throw('Phiếu công đã thay đổi. Tải lại trước khi sửa.')
            if doc.status=='On Leave':frappe.throw('Nghỉ phép được quản lý bằng HRMS.')
        else:
            if existing:frappe.throw('Ngày đã có phiếu công. Tải lại bảng để sửa phiếu hiện có.')
            doc=frappe.new_doc('Attendance')
        doc.update(dict(company=company,employee=employee.name,attendance_date=day,status=presence['status'],working_hours=presence['working_hours'],
            lotus_overtime_hours=overtime,lotus_note=payload['note'],lotus_client_key=key,lotus_payload_hash=digest))
        set_presence(doc,presence);set_allowance_values(doc,company,day,doc.get('lotus_allowance') if allowance is None else allowance);doc.save();names.append(doc.name)
    return dict(names=names)


def approve(company,date,client_event_id,reviewed_rows):
    if not (frappe.has_permission('Attendance','create') and frappe.has_permission('Attendance','submit')):
        frappe.throw('Chưa có quyền lưu và duyệt chấm công.',frappe.PermissionError)
    t._company(company);lock('Company',company)
    reviewed=frappe.parse_json(reviewed_rows) if isinstance(reviewed_rows,str) else reviewed_rows
    if not isinstance(reviewed,list) or not 1<=len(reviewed)<=300:frappe.throw('Chọn người khớp máy để duyệt.')
    wanted={r['row_key']:r['review_hash'] for r in reviewed}
    data=board(company,date,sync=0);rows=[r for r in data['rows'] if r['row_key'] in wanted]
    if len(wanted)!=len(reviewed) or len(rows)!=len(reviewed) or any(not r['matches'] or r['review_hash']!=wanted[r['row_key']] for r in rows):
        frappe.throw('Dữ liệu chấm công đã thay đổi sau khi xem. Tải lại và kiểm tra trước khi duyệt.')
    entries=[dict(employee=r['employee'],name=r['name'],modified=r['modified'],note=r['note'],overtime_hours=0,allowance=r['allowance'],
        **{k:r['machine'][k] for k in ('morning_present','afternoon_present','morning_time','afternoon_time')}) for r in rows]
    saved=save(company,date,entries,client_event_id)
    docs=[frappe.get_doc('Attendance',name) for name in saved['names']]
    t.staff_action(company,[dict(name=d.name,modified=str(d.modified)) for d in docs if d.docstatus==0],'submit')
    return dict(approved=len(docs),names=[d.name for d in docs])


def set_allowance_values(doc,company,day,allowance):
    """Phụ cấp công việc of the day, fixed on the record at the rate in force that day (lotus_farm.work_allowance)."""
    from lotus_farm.work_allowance import amount_for
    allowance=cint(allowance) if doc.status!='Absent' else 0
    doc.lotus_allowance=allowance
    doc.lotus_allowance_amount=amount_for(company,day,allowance,min(flt(doc.working_hours),8)/8)


def set_allowance(company,date,rows,allowance):
    """Tick or clear Phụ cấp on days already saved (draft or approved) while the month is open. rows: employee, name, modified."""
    from lotus_farm.hr_period import is_closed
    t._company(company);day=t._date(date);entries=frappe.parse_json(rows)
    if not isinstance(entries,list) or not 1<=len(entries)<=300:frappe.throw('Chọn từ 1 đến 300 nhân viên.')
    if is_closed(company,day):frappe.throw('Tháng công đã khóa, không sửa phụ cấp.')
    lock('Company',company);changed=[]
    for entry in entries:
        doc=frappe.get_doc('Attendance',entry.get('name'))
        doc.check_permission('write' if doc.docstatus==0 else 'submit')
        if doc.company!=company or str(doc.attendance_date)!=str(day) or doc.docstatus>1 or str(doc.modified)!=str(entry.get('modified')):
            frappe.throw('Phiếu công đã thay đổi. Tải lại trước khi sửa phụ cấp.')
        if cint(allowance) and doc.status=='Absent':frappe.throw(frappe.db.get_value('Employee',doc.employee,'employee_name')+': vắng cả ngày, không có phụ cấp.')
        if cint(doc.get('lotus_allowance'))==cint(allowance):continue
        set_allowance_values(doc,company,day,allowance)
        doc.add_comment('Comment',('Tick' if cint(allowance) else 'Bỏ')+' phụ cấp công việc.')
        doc.save();changed.append(doc.name)
    return dict(changed=len(changed),names=changed)
