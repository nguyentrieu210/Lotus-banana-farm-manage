from lotus_farm.daily_operations import WorkResult


class DailyWorkResult(WorkResult):
    def before_submit(self):
        # Field captures are provisional until independently verified and approved.
        # Legacy/import results without a Field Capture preserve their prior contract.
        if self.field_capture:
            import frappe
            from lotus_farm.controls import command_allowed
            if not command_allowed(self, "review_result"):
                frappe.throw("Chỉ được chốt qua quy trình duyệt trên app.")
            if self.review_state != "Approved" or not self.verified_by or not self.reviewed_by:
                frappe.throw("Báo cáo hiện trường phải qua kiểm tra và duyệt trước khi ghi chính thức.")
            if len({self.owner, self.verified_by, self.reviewed_by}) != 3:
                frappe.throw("Người báo, người kiểm tra và người duyệt phải khác nhau.")