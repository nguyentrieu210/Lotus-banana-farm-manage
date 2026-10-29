"""Keep native HRMS validation, while allowing evidence dated inside a former employee's employment."""
import frappe
from frappe.utils import getdate
from hrms.hr.doctype.attendance.attendance import Attendance
from hrms.hr.doctype.employee_checkin.employee_checkin import EmployeeCheckin
from lotus_farm.timekeeping_rules import employed_on


def _historical(doc, day):
    person=frappe.get_doc('Employee',doc.employee)
    person.check_permission('read')
    if person.status!='Left':return False
    if not employed_on(person,getdate(day)):
        frappe.throw('Ngày công/lượt chấm nằm ngoài thời gian làm việc của nhân viên.')
    return True


class HistoricalAttendance(Attendance):
    def validate(self):
        if not _historical(self,self.attendance_date):return super().validate()
        # HRMS 16.50 Attendance.validate, with only its current-status check replaced above.
        from erpnext.controllers.status_updater import validate_status
        validate_status(self.status,['Present','Absent','On Leave','Half Day','Work From Home'])
        self.validate_attendance_date()
        self.validate_duplicate_record()
        self.validate_overlapping_shift_attendance()
        self.validate_employee_status()
        self.check_leave_record()


class HistoricalEmployeeCheckin(EmployeeCheckin):
    def validate(self):
        if not _historical(self,self.time):return super().validate()
        self.validate_duplicate_log()
        self.validate_time_change()
        self.fetch_shift()
        self.set_geolocation()
        self.validate_distance_from_shift_location()
