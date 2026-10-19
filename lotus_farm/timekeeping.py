"""Lotus timekeeping: native HRMS Attendance plus contractor crew evidence."""
import calendar
import hashlib
import json
import frappe
from frappe.model.document import Document
from frappe.utils import add_days,get_datetime,getdate,nowdate,flt,cint
from lotus_farm.controls import lock,check_farm,require_role,command
from lotus_farm.timekeeping_rules import crew_values,status_days


def install_fields():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    fields={'Work Team':[dict(fieldname='lotus_team_type',label='Loại đội',fieldtype='Select',options='Internal\nContractor',default='Internal'),dict(fieldname='lotus_foreman',label='Đầu câu / người phụ trách',fieldtype='Data'),dict(fieldname='lotus_foreman_phone',label='Điện thoại đầu câu',fieldtype='Data')]}
    if frappe.db.exists('DocType','Attendance'):
        fields['Attendance']=[dict(fieldname='lotus_note',label='Ghi chú Lotus',fieldtype='Small Text'),dict(fieldname='lotus_cancel_reason',label='Lý do hủy Lotus',fieldtype='Small Text',allow_on_submit=1),dict(fieldname='lotus_client_key',label='Lotus request identity',fieldtype='Data',hidden=1,read_only=1,no_copy=1,unique=1),dict(fieldname='lotus_payload_hash',label='Lotus request content',fieldtype='Data',hidden=1,read_only=1,no_copy=1),dict(fieldname='lotus_overtime_hours',label='Lotus · Giờ tăng ca được duyệt',fieldtype='Float',insert_after='working_hours')]
    create_custom_fields(fields,update=True,ignore_validate=True)
    from frappe.permissions import add_permission,update_permission_property
    for role in ('HR Manager','HR User'):
        if not frappe.db.exists('Role',role):continue
        add_permission('Work Team',role)
        for action in ('read','create','write'):update_permission_property('Work Team',role,0,action,1)
        add_permission('Farm',role);update_permission_property('Farm',role,0,'read',1)
        add_permission('Work Type',role);update_permission_property('Work Type',role,0,'read',1)
    if not frappe.db.exists('Role','Lotus Crew Leader'):frappe.get_doc(dict(doctype='Role',role_name='Lotus Crew Leader',desk_access=1)).insert(ignore_permissions=True)
    for dt,actions in [('Lotus Crew Attendance',('read','create','write','print')),('Work Team',('read',)),('Work Type',('read',)),('Farm',('read',)),('Company',('read',)),('UOM',('read',))]:
        if not frappe.db.exists('DocType',dt):continue
        add_permission(dt,'Lotus Crew Leader')
        for action in actions:update_permission_property(dt,'Lotus Crew Leader',0,action,1)


def _company(name):
    if frappe.session.user=='Guest':frappe.throw('Vui lòng đăng nhập.',frappe.AuthenticationError)
    doc=frappe.get_doc('Company',name);doc.check_permission('read');return doc


def _employee(name,company,active=True):
    doc=frappe.get_doc('Employee',name);doc.check_permission('read')
    if doc.company!=company or (active and doc.status!='Active'):frappe.throw('Nhân viên phải đang làm việc tại công ty đã chọn.')
    return doc


def _date(value):
    if not value:frappe.throw('Chọn ngày công.')
    date=getdate(value)
    if date>getdate(nowdate()):frappe.throw('Không chấm công cho ngày chưa đến.')
    return date


def _request(event,payload):
    event=str(event or '').strip()
    if not event or len(event)>140:frappe.throw('Thiếu mã yêu cầu lưu.')
    return hashlib.sha256((frappe.session.user+':'+event).encode()).hexdigest(),hashlib.sha256(json.dumps(payload,sort_keys=True,default=str).encode()).hexdigest()


@frappe.whitelist()
def bootstrap():
    if frappe.session.user=='Guest':frappe.throw('Vui lòng đăng nhập.',frappe.AuthenticationError)
    from frappe.sessions import get_csrf_token
    installed=bool(frappe.db.exists('DocType','Attendance'))
    return dict(user=frappe.session.user,today=nowdate(),csrf_token=get_csrf_token(),hrms_installed=installed,companies=frappe.get_list('Company',fields=['name','default_currency'],limit_page_length=0),
        capabilities={dt:{action:bool(frappe.has_permission(dt,action)) for action in ('read','create','write','submit','cancel','delete','export','print')} for dt in ('Employee','Attendance','Work Team','Lotus Crew Attendance') if frappe.db.exists('DocType',dt)},
        can_create_farm=frappe.session.user=='Administrator' or ('System Manager' in frappe.get_roles() and frappe.has_permission('Farm','create')),
        is_hr_manager=frappe.session.user=='Administrator' or bool({'HR Manager','System Manager'}&set(frappe.get_roles())),
        can_read_checkins=bool(frappe.db.exists('DocType','Employee Checkin') and frappe.has_permission('Employee Checkin','read')))


@frappe.whitelist()
def catalogue(company):
    _company(company)
    def rows(dt,filters,fields):
        return frappe.get_list(dt,filters=filters,fields=fields,limit_page_length=0) if frappe.db.exists('DocType',dt) and frappe.has_permission(dt,'read') else []
    farms=rows('Farm',{'company':company,'active':1},['name','farm_name'])
    return dict(farms=farms,teams=rows('Work Team',{'active':1,'lotus_team_type':'Contractor','farm':['in',[f.name for f in farms]]},['name','team_name','farm','lotus_foreman','lotus_foreman_phone']),
        works=rows('Work Type',{'active':1,'allow_piecework':1},['name','work_name','uom','piecework_rate']),
        shifts=rows('Shift Type',{},['name','start_time','end_time','late_entry_grace_period','early_exit_grace_period','working_hours_threshold_for_half_day','working_hours_threshold_for_absent']),employees=rows('Employee',{'company':company,'status':'Active'},['name','employee_name']),departments=rows('Department',{'company':company,'is_group':0},['name','department_name']),genders=rows('Gender',{},['name']),uoms=rows('UOM',{'enabled':1},['name']))


@frappe.whitelist()
def staff_day(company,date,shift=None,search=None):
    _company(company);date=_date(date)
    if not frappe.has_permission('Attendance','read'):frappe.throw('Chưa có quyền đọc chấm công.',frappe.PermissionError)
    people=frappe.get_list('Employee',filters={'company':company,'status':'Active'},fields=['name','employee_name','department','designation'],order_by='employee_name',limit_page_length=0)
    # A shift filter shows that shift only; otherwise each employee appears once with the scheduled shift.
    filters={'company':company,'attendance_date':date,'docstatus':['<',2]}
    if shift:filters['shift']=shift
    attendance=frappe.get_list('Attendance',filters=filters,fields=['name','employee','status','working_hours','docstatus','modified','lotus_note','actual_overtime_duration','lotus_overtime_hours','in_time','out_time','late_entry','early_exit','leave_type','shift'],order_by='docstatus desc',limit_page_length=0)
    by_employee={}
    for record in attendance:by_employee.setdefault(record.employee,record)
    scheduled={} if shift else assigned_shifts(company,date,[p.name for p in people]);rows=[]
    for person in people:
        if search and str(search).casefold() not in (person.name+' '+person.employee_name).casefold():continue
        row=dict(employee=person.name,employee_name=person.employee_name,department=person.department,designation=person.designation,name=None,status='',working_hours=0,overtime_hours=0,in_time=None,out_time=None,late_entry=0,early_exit=0,note='',docstatus=0,modified=None,shift=shift or scheduled.get(person.name) or '')
        if person.name in by_employee:
            entry=by_employee[person.name];row.update(dict(entry));row['note']=entry.lotus_note or '';row['overtime_hours']=flt(entry.lotus_overtime_hours)
        rows.append(row)
    from lotus_farm.hr_period import holiday_map,is_closed
    holidays=holiday_map(company,date,date)
    holiday=frappe.db.get_value('Holiday',{'parent':holidays.name,'holiday_date':date},['description','weekly_off'],as_dict=True) if holidays else None
    return dict(rows=rows,date=str(date),holiday=dict(holiday) if holiday else None,has_calendar=bool(holidays),period_closed=is_closed(company,date))


@frappe.whitelist()
def propose_from_checkins(company,date,shift=None):
    """Device check-ins of one day -> proposed status per active employee. Nothing is saved here."""
    _company(company);date=_date(date)
    if not (frappe.has_permission('Attendance','create') and frappe.has_permission('Employee Checkin','read')):frappe.throw('Chưa có quyền lấy công từ máy chấm.',frappe.PermissionError)
    from datetime import datetime,timedelta
    from lotus_farm.checkin_rules import day_status,shift_window
    from lotus_farm.hr_period import holiday_map
    people=frappe.get_list('Employee',filters={'company':company,'status':'Active'},pluck='name',limit_page_length=0)
    # Each employee is read against the chosen shift, else the scheduled one, else the whole calendar day.
    plan={p:shift for p in people} if shift else assigned_shifts(company,date,people)
    settings={}
    for name in set(plan.values())-{None,''}:
        doc=frappe.get_doc('Shift Type',name);doc.check_permission('read');settings[name]=doc.as_dict()
    def window(name):
        begin,end=shift_window(date,settings.get(name) or {})
        if not begin:
            begin=datetime.combine(date,datetime.min.time());return begin,begin+timedelta(days=1)-timedelta(seconds=1)
        conf=settings[name]
        return begin-timedelta(minutes=cint(conf.get('begin_check_in_before_shift_start_time'))),end+timedelta(minutes=cint(conf.get('allow_check_out_after_shift_end_time')))
    windows={p:window(plan.get(p)) for p in people}
    first=min([w[0] for w in windows.values()] or [datetime.combine(date,datetime.min.time())]);last=max([w[1] for w in windows.values()] or [first])
    checkins=frappe.get_list('Employee Checkin',filters={'employee':['in',people or ['']],'time':['between',[first,last]]},fields=['employee','time','log_type'],order_by='time',limit_page_length=0)
    by_employee={}
    for row in checkins:
        begin,end=windows[row.employee]
        if begin<=get_datetime(row.time)<=end:by_employee.setdefault(row.employee,[]).append(row)
    holidays=holiday_map(company,date,date)
    off=bool(holidays and date in holidays.days)
    rows=[]
    for employee in people:
        proposal=day_status(date,by_employee.get(employee,[]),settings.get(plan.get(employee)) or {},is_holiday=off)
        rows.append(dict(employee=employee,shift=plan.get(employee) or '',checkins=len(by_employee.get(employee,[])),**{k:(str(v) if hasattr(v,'hour') else v) for k,v in proposal.items()}))
    return dict(rows=rows,date=str(date),shift=shift or '',checkins=sum(len(v) for v in by_employee.values()))


def assigned_shifts(company,date,employees):
    """{employee: Shift Type} from submitted, active HRMS Shift Assignments covering the date."""
    if not employees or not frappe.db.exists('DocType','Shift Assignment'):return {}
    rows=frappe.get_all('Shift Assignment',filters={'company':company,'employee':['in',employees],'docstatus':1,'status':'Active','start_date':['<=',date]},
        fields=['employee','shift_type','end_date'],order_by='start_date desc',limit_page_length=0)
    result={}
    for row in rows:
        if not row.end_date or getdate(row.end_date)>=date:result.setdefault(row.employee,row.shift_type)
    return result


@frappe.whitelist()
def shift_schedule(company,month):
    """Shift Assignments overlapping the month, for the schedule table."""
    _company(company)
    from lotus_farm.timekeeping_rules import month_range
    try:begin,end=month_range(month)
    except ValueError as exc:frappe.throw(str(exc))
    if not frappe.has_permission('Shift Assignment','read'):frappe.throw('Chưa có quyền xem lịch ca.',frappe.PermissionError)
    rows=frappe.get_list('Shift Assignment',filters={'company':company,'docstatus':1,'status':'Active','start_date':['<=',end]},
        fields=['name','employee','employee_name','shift_type','start_date','end_date'],order_by='start_date desc',limit_page_length=0)
    return dict(rows=[r for r in rows if not r.end_date or getdate(r.end_date)>=begin])


@frappe.whitelist(methods=['POST'])
def assign_shift(company,shift,employees,start_date,end_date=None):
    """Schedule employees on one shift for a date range (HRMS Shift Assignment, submitted)."""
    _company(company)
    if not frappe.has_permission('Shift Assignment','create'):frappe.throw('Chưa có quyền xếp ca.',frappe.PermissionError)
    frappe.get_doc('Shift Type',shift).check_permission('read')
    names=frappe.parse_json(employees) if isinstance(employees,str) else employees
    if not isinstance(names,list) or not 1<=len(names)<=300:frappe.throw('Chọn từ 1 đến 300 nhân viên.')
    begin=getdate(start_date) if start_date else None
    finish=getdate(end_date) if end_date else None
    if not begin or (finish and finish<begin):frappe.throw('Chọn khoảng ngày xếp ca hợp lệ.')
    lock('Company',company);created=[]
    for name in sorted(set(names)):
        _employee(name,company)
        doc=frappe.get_doc(dict(doctype='Shift Assignment',company=company,employee=name,shift_type=shift,start_date=begin,end_date=finish,status='Active'))
        doc.insert();doc.submit();created.append(doc.name)
    return dict(names=created)


@frappe.whitelist(methods=['POST'])
def end_shift(company,name,end_date):
    """Stop a scheduled shift from a date (HRMS keeps the assignment, only its end date moves)."""
    _company(company)
    doc=frappe.get_doc('Shift Assignment',name);doc.check_permission('write')
    if doc.company!=company or doc.docstatus!=1:frappe.throw('Lịch ca không hợp lệ.')
    finish=getdate(end_date)
    if finish<getdate(doc.start_date):frappe.throw('Ngày kết thúc phải sau ngày bắt đầu ca.')
    doc.end_date=finish;doc.save()
    return dict(name=doc.name)


@frappe.whitelist(methods=['POST'])
def save_staff(company,date,rows,client_event_id,shift=None):
    _company(company);date=_date(date);entries=frappe.parse_json(rows)
    _request(client_event_id,[])
    if not isinstance(entries,list) or not 1<=len(entries)<=300:frappe.throw('Chọn từ 1 đến 300 nhân viên.')
    if shift:frappe.get_doc('Shift Type',shift).check_permission('read')
    lock('Company',company);saved=[];seen=set()
    for entry in sorted(entries,key=lambda r:str(r.get('employee'))):
        employee=_employee(entry.get('employee'),company)
        if employee.name in seen:frappe.throw('Nhân viên bị trùng trong danh sách.')
        seen.add(employee.name)
        # Without a shift filter each row carries the employee's scheduled shift.
        row_shift=shift or entry.get('shift') or None
        if row_shift and row_shift!=shift:frappe.get_doc('Shift Type',row_shift).check_permission('read')
        if date<getdate(employee.date_of_joining):frappe.throw('Ngày công trước ngày vào làm của '+employee.employee_name)
        status=entry.get('status')
        if status not in ('Present','Absent','Half Day','Work From Home'):frappe.throw('Chọn trạng thái công hợp lệ. Nghỉ phép được quản lý bằng HRMS.')
        from lotus_farm.warehouse import _number
        hours=_number(entry.get('working_hours',0),'Giờ làm',allow_zero=True)
        if hours>24 or (status=='Absent' and hours):frappe.throw('Giờ làm không hợp lệ cho trạng thái đã chọn.')
        overtime=_number(entry.get('overtime_hours',0) or 0,'Giờ tăng ca',allow_zero=True)
        if overtime>16 or (status=='Absent' and overtime):frappe.throw('Giờ tăng ca không hợp lệ cho trạng thái đã chọn.')
        clock={}
        for field in ('in_time','out_time'):
            if entry.get(field):
                moment=get_datetime(entry[field])
                # A night shift may end on the next calendar day, never later.
                if not date<=moment.date()<=add_days(date,1):frappe.throw('Giờ vào/ra phải thuộc ngày công.')
                clock[field]=str(moment)
        if clock.get('in_time') and clock.get('out_time') and clock['out_time']<=clock['in_time']:frappe.throw('Giờ ra phải sau giờ vào.')
        payload=dict(company=company,date=str(date),employee=employee.name,status=status,hours=hours,overtime=overtime,shift=row_shift or '',note=str(entry.get('note') or '')[:2000],
            late=cint(entry.get('late_entry')),early=cint(entry.get('early_exit')),**clock)
        key,digest=_request(str(client_event_id)+':'+employee.name,payload)
        retry=frappe.db.get_value('Attendance',{'lotus_client_key':key},['name','lotus_payload_hash'],as_dict=True)
        if retry:
            doc=frappe.get_doc('Attendance',retry.name);doc.check_permission('read')
            if retry.lotus_payload_hash!=digest:frappe.throw('Yêu cầu đã lưu với nội dung khác. Tải lại bảng công.')
            saved.append(doc.name);continue
        if entry.get('name'):
            doc=frappe.get_doc('Attendance',entry['name']);doc.check_permission('write')
            if doc.company!=company or doc.employee!=employee.name or getdate(doc.attendance_date)!=date or (doc.shift or '')!=(row_shift or '') or doc.docstatus!=0 or str(doc.modified)!=str(entry.get('modified')):frappe.throw('Bảng công đã thay đổi. Tải lại trước khi sửa.')
        else:
            if frappe.db.exists('Attendance',{'employee':employee.name,'attendance_date':date,'docstatus':['<',2],'shift':row_shift or ['is','not set']}):frappe.throw('Nhân viên đã được chấm công. Tải lại bảng để sửa phiếu nháp.')
            doc=frappe.new_doc('Attendance')
        doc.company=company;doc.employee=employee.name;doc.attendance_date=date;doc.status=status;doc.shift=row_shift or None;doc.working_hours=hours;doc.lotus_overtime_hours=overtime;doc.in_time=clock.get('in_time');doc.out_time=clock.get('out_time');doc.late_entry=payload['late'];doc.early_exit=payload['early'];doc.lotus_note=payload['note'];doc.lotus_client_key=key;doc.lotus_payload_hash=digest
        doc.save();saved.append(doc.name)
    return dict(names=saved)


@frappe.whitelist(methods=['POST'])
def staff_action(company,rows,action,reason=None):
    _company(company);entries=frappe.parse_json(rows)
    if action not in ('submit','cancel','delete') or not isinstance(entries,list) or not 1<=len(entries)<=300:frappe.throw('Thao tác không hợp lệ.')
    if action=='cancel' and not str(reason or '').strip():frappe.throw('Cần lý do hủy công đã duyệt.')
    lock('Company',company)
    for entry in sorted(entries,key=lambda r:str(r.get('name'))):
        lock('Attendance',entry['name']);doc=frappe.get_doc('Attendance',entry['name']);doc.check_permission('read');_employee(doc.employee,company,active=False)
        if doc.company!=company or str(doc.modified)!=str(entry.get('modified')):frappe.throw('Phiếu công đã thay đổi. Tải lại để kiểm tra.')
        doc.check_permission(action)
        if action=='submit' and doc.docstatus==0:doc.submit()
        elif action=='cancel' and doc.docstatus==1:
            doc.lotus_cancel_reason=str(reason)[:2000];doc.save();doc.cancel()
        elif action=='delete' and doc.docstatus==0:frappe.delete_doc('Attendance',doc.name)
        else:frappe.throw('Trạng thái phiếu công không phù hợp thao tác.')
    return dict(count=len(entries))


@frappe.whitelist()
def monthly(company,month):
    _company(company)
    begin=getdate(str(month)+'-01');end=begin.replace(day=calendar.monthrange(begin.year,begin.month)[1])
    people=frappe.get_list('Employee',filters={'company':company},fields=['name','employee_name','department','designation'],order_by='employee_name',limit_page_length=0)
    records=frappe.get_list('Attendance',filters={'company':company,'attendance_date':['between',[begin,end]],'docstatus':['<',2]},fields=['name','employee','attendance_date','status','docstatus','working_hours','actual_overtime_duration','lotus_overtime_hours'],limit_page_length=0)
    rows=[]
    for employee in people:
        entries=[r for r in records if r.employee==employee.name];approved=[r for r in entries if r.docstatus==1]
        days={}
        for entry in entries:days.setdefault(str(getdate(entry.attendance_date).day),[]).append(dict(entry))
        # A person can have multiple non-overlapping shifts. Never count more than one workday per calendar day.
        workdays=sum(min(1,sum(status_days(r.status) for r in approved if getdate(r.attendance_date).day==day)) for day in range(1,end.day+1))
        rows.append(dict(employee=employee.name,employee_name=employee.employee_name,department=employee.department,days=days,workdays=workdays,working_hours=sum(flt(r.working_hours) for r in approved),overtime_hours=sum(flt(r.lotus_overtime_hours) or flt(r.actual_overtime_duration) for r in approved),draft_count=sum(r.docstatus==0 for r in entries)))
    from lotus_farm.hr_period import is_closed
    return dict(rows=rows,days=end.day,month=str(month),company=company,period_closed=is_closed(company,begin),holidays=_month_holidays(company,begin,end))


def _month_holidays(company,begin,end):
    """{day number: 1 weekly off / 0 public holiday} for shading the month sheet."""
    from lotus_farm.hr_period import holiday_map
    found=holiday_map(company,begin,end)
    return {str(day.day):flag for day,flag in found.days.items()} if found else {}


class CrewAttendanceDocument(Document):
    def validate(self):
        check_farm(self);farm=frappe.get_doc('Farm',self.farm);farm.check_permission('read');_company(farm.company)
        team=frappe.get_doc('Work Team',self.work_team);team.check_permission('read')
        if team.farm!=self.farm or not team.active or team.lotus_team_type!='Contractor':frappe.throw('Chọn đội khoán đang hoạt động thuộc nông trường.')
        if self.company and self.company!=farm.company:frappe.throw('Công ty không khớp nông trường.')
        _date(self.posting_date);lock('Company',farm.company)
        before=self.get_doc_before_save()
        if before and any(str(before.get(f) or '')!=str(self.get(f) or '') for f in ('company','farm','work_team','posting_date','work_type')):frappe.throw('Không đổi danh tính phiếu công. Hủy và lập phiếu mới nếu chọn sai ngày/đội.')
        if self.work_type:
            work = frappe.get_doc('Work Type', self.work_type)
            work.check_permission('read')
            if not work.active or not work.allow_piecework:
                frappe.throw('Công việc này chưa cho phép công khoán.')
            self.uom = work.uom
            listed = flt(before.listed_piecework_rate) if before and before.work_type else flt(work.piecework_rate)
            if listed <= 0:
                frappe.throw('Công việc chưa có đơn giá khoán.')
            self.listed_piecework_rate = listed
            if not before and flt(self.unit_rate) == 0 and not self.rate_override_reason:
                self.unit_rate = listed
            if abs(flt(self.unit_rate) - listed) > 0.00001:
                if not str(self.rate_override_reason or '').strip():
                    frappe.throw('Sửa đơn giá khoán phải ghi lý do.')
                require_role('Lotus Farm Manager')
        elif not before and flt(self.completed_qty) > 0:
            frappe.throw('Chọn công việc khoán để lấy đơn vị và đơn giá.')
        if self.work_type and flt(self.completed_qty) > 0 and flt(self.unit_rate) <= 0:
            frappe.throw('Khối lượng khoán đã thực hiện phải có đơn giá dương.')
        others = frappe.get_all('Lotus Crew Attendance',
            filters={'company': farm.company, 'work_team': self.work_team,
                     'posting_date': self.posting_date, 'docstatus': ['<', 2],
                     'name': ['!=', self.name or '']},
            fields=['present','workdays'])
        if others:
            max_people = max([flt(self.present)] + [flt(row.present) for row in others])
            if flt(self.workdays) + sum(flt(row.workdays) for row in others) > max_people + 0.000001:
                frappe.throw('Tổng công của tổ trong ngày vượt số người có mặt. Chia công giữa các việc, không chấm đủ công hai lần.')
        try:values=crew_values(self.headcount,self.present,self.workdays,self.completed_qty,self.unit_rate)
        except (ValueError,TypeError) as exc:frappe.throw(str(exc))
        for field,value in values.items():self.set(field,value)
        if self.completed_qty>0:
            if not self.uom:frappe.throw('Khối lượng khoán cần đơn vị tính.')
            unit=frappe.get_doc('UOM',self.uom);unit.check_permission('read')
            if not unit.enabled:frappe.throw('Đơn vị khoán đã bị tắt.')
        self.company=farm.company;self.currency=frappe.get_cached_value('Company',self.company,'default_currency');self.foreman=self.foreman or team.lotus_foreman
        if not self.foreman:frappe.throw('Đội khoán cần thông tin đầu câu.')
        self.attendance_key=hashlib.sha256((self.company+'|'+self.work_team+'|'+str(getdate(self.posting_date))+('|' + self.work_type if self.work_type else '')).encode()).hexdigest()
        duplicate=frappe.db.get_value(self.doctype,{'attendance_key':self.attendance_key},'name')
        if duplicate and duplicate!=self.name:frappe.throw('Đội đã có phiếu công ngày này. Tải lại phiếu để sửa.')

    def before_cancel(self):
        if not str(self.cancel_reason or '').strip():frappe.throw('Cần lý do hủy phiếu công.')
        self.db_set('attendance_key',None)


@frappe.whitelist()
def crew_day(company,date,farm=None):
    _company(company);date=_date(date)
    filters={'company':company,'posting_date':date,'docstatus':['<',2]}
    if farm:filters['farm']=farm
    rows=frappe.get_list('Lotus Crew Attendance',filters=filters,fields=['name','farm','work_team','foreman','posting_date','work_type','headcount','present','absent','workdays','completed_qty','uom','unit_rate','listed_piecework_rate','rate_override_reason','amount','currency','notes','docstatus','modified'],limit_page_length=0)
    teams=frappe.get_list('Work Team',filters={'active':1,'lotus_team_type':'Contractor',**({'farm':farm} if farm else {})},fields=['name','team_name','farm','lotus_foreman'],limit_page_length=0)
    permitted={r.name for r in frappe.get_list('Farm',filters={'company':company},fields=['name'],limit_page_length=0)}
    return dict(rows=rows,teams=[r for r in teams if r.farm in permitted])


@frappe.whitelist(methods=['POST'])
def save_crew(company,values,client_event_id):
    _company(company);values=frappe.parse_json(values)
    if not isinstance(values,dict):frappe.throw('Phiếu công không hợp lệ.')
    lock('Company',company);key,digest=_request(client_event_id,values)
    retry=frappe.db.get_value('Lotus Crew Attendance',{'client_key':key},['name','payload_hash'],as_dict=True)
    if retry:
        doc=frappe.get_doc('Lotus Crew Attendance',retry.name);doc.check_permission('read')
        if retry.payload_hash!=digest:frappe.throw('Yêu cầu đã lưu với nội dung khác. Tải lại phiếu công.')
        return dict(name=doc.name)
    if values.get('name'):
        doc=frappe.get_doc('Lotus Crew Attendance',values['name']);doc.check_permission('write')
        if doc.company!=company or doc.docstatus!=0 or str(doc.modified)!=str(values.get('modified')):frappe.throw('Phiếu công đã thay đổi. Tải lại trước khi sửa.')
    else:doc=frappe.new_doc('Lotus Crew Attendance')
    for field in ('farm','work_team','work_type','posting_date','headcount','present','workdays','completed_qty','uom','unit_rate','rate_override_reason','notes'):doc.set(field,values.get(field))
    doc.company=company;doc.client_key=key;doc.payload_hash=digest;doc.save()
    return dict(name=doc.name)


@frappe.whitelist(methods=['POST'])
def crew_action(company,name,modified,action,reason=None):
    _company(company);lock('Company',company);lock('Lotus Crew Attendance',name)
    doc=frappe.get_doc('Lotus Crew Attendance',name);doc.check_permission('read')
    if doc.company!=company or str(doc.modified)!=str(modified):frappe.throw('Phiếu công đã thay đổi. Tải lại để kiểm tra.')
    if action not in ('submit','cancel','delete'):frappe.throw('Thao tác không hợp lệ.')
    doc.check_permission(action)
    if action=='submit' and doc.docstatus==0:doc.submit()
    elif action=='cancel' and doc.docstatus==1:
        doc.cancel_reason=str(reason or '').strip()
        if not doc.cancel_reason:frappe.throw('Cần lý do hủy.')
        doc.save();doc.cancel()
    elif action=='delete' and doc.docstatus==0:frappe.delete_doc(doc.doctype,doc.name)
    else:frappe.throw('Trạng thái phiếu không phù hợp thao tác.')
    return dict(name=name)


@frappe.whitelist(methods=['POST'])
def create_employee(company,values):
    _company(company);values=frappe.parse_json(values)
    from lotus_farm.warehouse import _text
    doc=frappe.new_doc('Employee');doc.company=company;doc.first_name=_text(values.get('employee_name'),'Họ tên');doc.gender=values.get('gender');doc.date_of_birth=values.get('date_of_birth');doc.date_of_joining=values.get('date_of_joining');doc.status='Active';doc.department=values.get('department') or None
    if doc.department:
        department=frappe.get_doc('Department',doc.department);department.check_permission('read')
        if department.company!=company:frappe.throw('Bộ phận không thuộc công ty đã chọn.')
    designation=str(values.get('designation') or '').strip()
    if designation:
        if not frappe.db.exists('Designation',designation):frappe.get_doc(dict(doctype='Designation',designation_name=_text(designation,'Chức vụ'))).insert()
        doc.designation=designation
    doc.create_user_automatically=0;doc.create_user_permission=0;doc.insert();return dict(name=doc.name)


@frappe.whitelist(methods=['POST'])
def create_team(company,values):
    _company(company);values=frappe.parse_json(values);farm=frappe.get_doc('Farm',values.get('farm'));farm.check_permission('read')
    if farm.company!=company or not farm.active:frappe.throw('Nông trường không hợp lệ.')
    from lotus_farm.warehouse import _text
    doc=frappe.get_doc(dict(doctype='Work Team',farm=farm.name,team_code=_text(values.get('code'),'Mã đội'),team_name=_text(values.get('name'),'Tên đội'),active=1,lotus_team_type='Contractor',lotus_foreman=_text(values.get('foreman'),'Đầu câu'),lotus_foreman_phone=str(values.get('phone') or '')[:40])).insert()
    return dict(name=doc.name)


@frappe.whitelist(methods=['POST'])
def create_farm(company,code,name):
    require_role('System Manager');_company(company).check_permission('write')
    if not frappe.has_permission('Farm','create'):frappe.throw('Chưa có quyền tạo nông trường.',frappe.PermissionError)
    from lotus_farm.warehouse import _text
    doc=frappe.get_doc(dict(doctype='Farm',farm_code=_text(code,'Mã nông trường'),farm_name=_text(name,'Tên nông trường'),company=company,active=1))
    # Only a new, empty farm can be created here. Existing farm access is never expanded.
    with command(doc,'create_attendance_farm'):doc.insert(ignore_permissions=True)
    if frappe.session.user!='Administrator':frappe.get_doc(dict(doctype='User Permission',user=frappe.session.user,allow='Farm',for_value=doc.name,apply_to_all_doctypes=1)).insert()
    return dict(name=doc.name)


def crew_query(user=None):
    from lotus_farm.controls import query_condition
    return query_condition('Lotus Crew Attendance',user)


@frappe.whitelist()
def crew_monthly(company,month,farm=None):
    _company(company);begin=getdate(str(month)+'-01');end=begin.replace(day=calendar.monthrange(begin.year,begin.month)[1])
    filters={'company':company,'posting_date':['between',[begin,end]],'docstatus':['<',2]}
    if farm:filters['farm']=farm
    records=frappe.get_list('Lotus Crew Attendance',filters=filters,fields=['name','work_team','foreman','posting_date','present','workdays','completed_qty','uom','amount','currency','docstatus'],limit_page_length=0)
    result=[]
    for team_name in sorted({r.work_team for r in records}):
        team=frappe.get_doc('Work Team',team_name);team.check_permission('read');entries=[r for r in records if r.work_team==team_name];approved=[r for r in entries if r.docstatus==1];days={}
        for entry in entries:days.setdefault(str(getdate(entry.posting_date).day),[]).append(dict(entry))
        result.append(dict(team=team.name,team_name=team.team_name,foreman=team.lotus_foreman,days=days,workdays=sum(flt(r.workdays) for r in approved),person_days=sum(cint(r.present) for r in approved),amount=sum(flt(r.amount) for r in approved),currency=frappe.get_cached_value('Company',company,'default_currency'),draft_count=sum(r.docstatus==0 for r in entries)))
    return dict(rows=result,days=end.day,month=str(month),company=company,holidays=_month_holidays(company,begin,end))


@frappe.whitelist(methods=['POST'])
def create_shift(name,start_time,end_time,late_grace=0,early_grace=0,half_day_hours=0,absent_hours=0,company=None):
    from lotus_farm.warehouse import _text
    values=dict(late_entry_grace_period=cint(late_grace),early_exit_grace_period=cint(early_grace),working_hours_threshold_for_half_day=flt(half_day_hours),working_hours_threshold_for_absent=flt(absent_hours))
    if not 0<=values['late_entry_grace_period']<=240 or not 0<=values['early_exit_grace_period']<=240:frappe.throw('Thời gian cho phép đi muộn/về sớm tối đa 240 phút.')
    if not 0<=values['working_hours_threshold_for_absent']<=values['working_hours_threshold_for_half_day'] or values['working_hours_threshold_for_half_day']>24:frappe.throw('Ngưỡng vắng phải nhỏ hơn hoặc bằng ngưỡng nửa ngày (tối đa 24 giờ).')
    holiday_list=frappe.get_cached_value('Company',_company(company).name,'default_holiday_list') if company else None
    # Lotus builds attendance drafts from check-ins itself; HRMS auto attendance would submit them unreviewed.
    doc=frappe.get_doc(dict(doctype='Shift Type',start_time=start_time,end_time=end_time,enable_auto_attendance=0,holiday_list=holiday_list,**values)).insert(set_name=_text(name,'Tên ca'))
    return dict(name=doc.name)


@frappe.whitelist()
def export_month(company,month,kind='staff',farm=None):
    import csv,io
    dt='Attendance' if kind=='staff' else 'Lotus Crew Attendance'
    if not frappe.has_permission(dt,'export'):frappe.throw('Chưa có quyền xuất bảng công.',frappe.PermissionError)
    data=monthly(company,month) if kind=='staff' else crew_monthly(company,month,farm)
    output=io.StringIO();writer=csv.writer(output)
    def safe(value):
        text=str(value or '')
        return "'"+text if text[:1] in ('=','+','-','@','\t','\r') else text
    writer.writerow(['Nhân viên' if kind=='staff' else 'Đội khoán',*range(1,data['days']+1),'Tổng công đã duyệt','Giờ làm' if kind=='staff' else 'Giá trị khoán','Phiếu nháp'])
    labels={'Present':'Có mặt','Absent':'Vắng','Half Day':'Nửa ngày','Work From Home':'Từ xa','On Leave':'Nghỉ phép'}
    for row in data['rows']:
        cells=[]
        for day in range(1,data['days']+1):
            values=row['days'].get(str(day),[])
            cells.append(' / '.join(('Nháp: ' if r['docstatus']==0 else '')+(labels.get(r['status'],r['status']) if kind=='staff' else str(r['workdays'])) for r in values))
        writer.writerow([safe(row['employee_name'] if kind=='staff' else row['team_name']),*cells,row['workdays'],row['working_hours'] if kind=='staff' else row['amount'],row['draft_count']])
    frappe.local.response.filename='bang-cong-'+kind+'-'+str(month)+'.csv';frappe.local.response.filecontent=('\ufeff'+output.getvalue()).encode('utf-8');frappe.local.response.type='download'
