"""ERPNext/HRMS business added INTO the existing Lotus modules (Kho, Mua hàng, Tài chính – Kế toán, Nhân sự), sized for
the farm company. Each module gets a few extra sidebar entries ("sections"); a section opens inside that module with one
tab per document list or report. Only what the Lotus screens do not already cover is listed here (no duplicates of
Nhập/Xuất/Kiểm kê, Đề nghị mua/Đơn mua, Hồ sơ nhân viên/Chấm công/Bảng lương, Thu/Chi…).

Every tab is still checked against the installed DocType/Report and the user's permissions at request time; a tab the
user may not open is left out, and a section with no tab left is not shown.
Not included on purpose: manufacturing, CRM, projects, support, subcontracting, country-specific (India/US) reports.
"""

D, R = 'doctype', 'report'

# module (Lotus navigation key) -> sections: dict(id, label, icon, setup, tabs=[(kind, name, label)])
SECTIONS = {
    'stock': [
        dict(id='batches', label='Lô & hạn dùng', icon='calendar', tabs=[(D, 'Batch', 'Lô hàng'), (R, 'Batch Item Expiry Status', 'Hạn dùng theo lô')]),
        dict(id='landed-costs', label='Chi phí sau nhập', icon='receive', tabs=[(D, 'Landed Cost Voucher', 'Chi phí phát sinh sau nhập')]),
        # nav=False: not a sidebar entry; the Kho "Báo cáo nhập – xuất – tồn" screen offers these in its report picker.
        dict(id='reports', label='Báo cáo kho', icon='chart', nav=False, tabs=[
            (R, 'Stock Projected Qty', 'Tồn dự kiến'), (R, 'Stock Ageing', 'Tuổi tồn kho'), (R, 'Itemwise Recommended Reorder Level', 'Mức đặt hàng lại đề xuất'),
            (R, 'Item Shortage Report', 'Vật tư thiếu'), (R, 'Batch-Wise Balance History', 'Tồn theo lô'), (R, 'Batch Item Expiry Status', 'Hạn dùng theo lô')]),
    ],
}

# Next modules, to be built into Mua hàng / Tài chính / Nhân sự screens the same way as Kho (not offered yet).
PLANNED = {
    'buying': [
        dict(id='rfq', label='Yêu cầu báo giá', icon='send', tabs=[(D, 'Request for Quotation', 'Yêu cầu báo giá'), (D, 'Supplier Quotation', 'Báo giá nhà cung cấp (ERP)')]),
        dict(id='buying-reports', label='Báo cáo mua hàng ERP', icon='chart', tabs=[
            (R, 'Purchase Register', 'Sổ mua hàng'), (R, 'Item-wise Purchase Register', 'Sổ mua theo mặt hàng'),
            (R, 'Procurement Tracker', 'Theo dõi mua hàng'), (R, 'Billed Items To Be Received', 'Đã có hóa đơn chưa nhận hàng'),
            (R, 'Purchase Analytics', 'Phân tích mua hàng'), (R, 'Supplier Ledger Summary', 'Tổng hợp sổ nhà cung cấp')]),
        dict(id='buying-setup', label='Danh mục mua hàng khác', icon='database', setup=True, tabs=[
            (D, 'Supplier Group', 'Nhóm nhà cung cấp'), (D, 'Purchase Taxes and Charges Template', 'Mẫu thuế mua hàng'), (D, 'Payment Terms Template', 'Điều khoản thanh toán')]),
    ],
    'finance': [
        dict(id='sales-docs', label='Chứng từ bán hàng', icon='receive', tabs=[
            (D, 'Sales Invoice', 'Hóa đơn bán hàng'), (D, 'Sales Order', 'Đơn bán hàng'), (D, 'Delivery Note', 'Phiếu giao hàng'),
            (D, 'Quotation', 'Báo giá'), (D, 'Customer', 'Khách hàng')]),
        dict(id='entries', label='Bút toán & khóa sổ', icon='document', tabs=[
            (D, 'Journal Entry', 'Bút toán'), (D, 'Payment Entry', 'Phiếu thu / chi (ERP)'), (D, 'Period Closing Voucher', 'Khóa sổ cuối kỳ')]),
        dict(id='asset-ops', label='Nghiệp vụ tài sản', icon='package', tabs=[
            (D, 'Asset Movement', 'Điều chuyển tài sản'), (D, 'Asset Repair', 'Sửa chữa tài sản'), (D, 'Asset Value Adjustment', 'Đánh giá lại'),
            (D, 'Asset Capitalization', 'Ghi tăng tài sản'), (R, 'Fixed Asset Register', 'Sổ tài sản cố định'), (R, 'Asset Depreciation Ledger', 'Sổ khấu hao')]),
        dict(id='erp-reports', label='Báo cáo ERP', icon='chart', tabs=[
            (R, 'General Ledger', 'Sổ cái'), (R, 'Trial Balance', 'Cân đối số phát sinh'), (R, 'Accounts Receivable', 'Phải thu chi tiết'),
            (R, 'Accounts Payable', 'Phải trả chi tiết'), (R, 'Sales Register', 'Sổ bán hàng'), (R, 'Gross Profit', 'Lãi gộp'),
            (R, 'Stock Balance', 'Tồn kho theo giá trị'), (R, 'Warehouse wise Item Balance Age and Value', 'Tồn theo kho, tuổi và giá trị'),
            (R, 'Asset Depreciations and Balances', 'Khấu hao và giá trị còn lại'), (R, 'Cash Flow', 'Lưu chuyển tiền tệ (ERPNext)')]),
        dict(id='finance-setup', label='Danh mục kế toán', icon='database', setup=True, tabs=[
            (D, 'Account', 'Hệ thống tài khoản'), (D, 'Cost Center', 'Trung tâm chi phí'), (D, 'Mode of Payment', 'Hình thức thanh toán'),
            (D, 'Bank', 'Ngân hàng'), (D, 'Fiscal Year', 'Năm tài chính'), (D, 'Accounting Period', 'Kỳ kế toán'), (D, 'Currency Exchange', 'Tỷ giá'),
            (D, 'Customer Group', 'Nhóm khách hàng'), (D, 'Price List', 'Bảng giá'), (D, 'Item Price', 'Giá theo bảng giá'),
            (D, 'Sales Taxes and Charges Template', 'Mẫu thuế bán hàng'), (D, 'Asset Category', 'Nhóm tài sản'), (D, 'Location', 'Địa điểm tài sản')]),
    ],
    'hr': [
        dict(id='leave', label='Nghỉ phép', icon='calendar', tabs=[
            (D, 'Leave Application', 'Đơn xin nghỉ'), (D, 'Leave Allocation', 'Cấp ngày phép'), (D, 'Compensatory Leave Request', 'Nghỉ bù'),
            (R, 'Employee Leave Balance', 'Số ngày phép còn lại'), (R, 'Leave Ledger', 'Sổ ngày phép'),
            (D, 'Leave Type', 'Loại nghỉ'), (D, 'Leave Policy', 'Chính sách phép'), (D, 'Leave Policy Assignment', 'Áp chính sách phép')]),
        dict(id='movements', label='Biến động nhân sự', icon='transfer', tabs=[
            (D, 'Employee Transfer', 'Điều chuyển'), (D, 'Employee Promotion', 'Thăng chức / đổi chức danh'), (D, 'Shift Request', 'Đề nghị đổi ca'),
            (D, 'Job Opening', 'Vị trí tuyển dụng')]),
        dict(id='pay-changes', label='Thưởng & khấu trừ', icon='wallet', tabs=[
            (D, 'Additional Salary', 'Thưởng / phạt / khấu trừ'), (D, 'Employee Incentive', 'Khen thưởng'), (D, 'Employee Advance', 'Tạm ứng'),
            (D, 'Expense Claim', 'Thanh toán chi phí / hoàn ứng')]),
        dict(id='hr-reports', label='Báo cáo nhân sự', icon='chart', tabs=[
            (R, 'Salary Register', 'Sổ lương'), (R, 'Employee Advance Summary', 'Tổng hợp tạm ứng'), (R, 'Employee Analytics', 'Phân tích nhân sự'),
            (R, 'Employee Birthday', 'Sinh nhật nhân viên'), (R, 'Employee Exits', 'Nhân viên nghỉ việc')]),
        dict(id='payroll-setup', label='Thiết lập lương', icon='sliders', setup=True, tabs=[
            (D, 'Salary Component', 'Thành phần lương'), (D, 'Salary Structure', 'Cấu trúc lương'), (D, 'Salary Structure Assignment', 'Gán cấu trúc lương'),
            (D, 'Payroll Period', 'Kỳ tính lương'), (D, 'Expense Claim Type', 'Loại chi phí'), (D, 'Employee Grade', 'Ngạch / bậc'),
            (D, 'Employment Type', 'Loại hợp đồng / lao động'), (D, 'Branch', 'Chi nhánh')]),
    ],
}
