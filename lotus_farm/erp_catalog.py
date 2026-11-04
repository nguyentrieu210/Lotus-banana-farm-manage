"""ERP coverage sized for the farm company (SME): which ERPNext/HRMS documents and reports Lotus opens in its own screens.

Every entry is still checked against the installed DocType/Report and the user's permissions at request time;
an entry the user may not read is left out instead of shown disabled. Lotus' own screens (Kho, Mua hàng, Nhân sự,
Chấm công, Tài chính) stay the main way in; this catalogue covers the rest of each business area beside them.
Not included on purpose: manufacturing, CRM, projects, support, subcontracting and country-specific (India/US) reports.
"""

# (kind, name, Vietnamese label). kind: 'doctype' | 'report'.
D, R = 'doctype', 'report'

MODULES = [
    dict(id='ban-hang', label='Bán hàng', lotus=None, groups=[
        dict(label='Chứng từ', items=[(D, 'Quotation', 'Báo giá'), (D, 'Sales Order', 'Đơn bán hàng'), (D, 'Delivery Note', 'Phiếu giao hàng'),
                                      (D, 'Sales Invoice', 'Hóa đơn bán hàng')]),
        dict(label='Danh mục', items=[(D, 'Customer', 'Khách hàng'), (D, 'Customer Group', 'Nhóm khách hàng'), (D, 'Price List', 'Bảng giá'),
                                      (D, 'Item Price', 'Giá bán / giá mua theo bảng giá'), (D, 'Sales Taxes and Charges Template', 'Mẫu thuế bán hàng'),
                                      (D, 'Payment Terms Template', 'Điều khoản thanh toán')]),
        dict(label='Báo cáo', items=[(R, 'Sales Register', 'Sổ bán hàng'), (R, 'Item-wise Sales Register', 'Sổ bán hàng theo mặt hàng'),
                                     (R, 'Accounts Receivable', 'Công nợ phải thu'), (R, 'Accounts Receivable Summary', 'Tổng hợp công nợ phải thu'),
                                     (R, 'Delivered Items To Be Billed', 'Đã giao chưa xuất hóa đơn'), (R, 'Gross Profit', 'Lãi gộp'),
                                     (R, 'Sales Analytics', 'Phân tích bán hàng'), (R, 'Customer Ledger Summary', 'Tổng hợp sổ khách hàng')]),
    ]),
    dict(id='mua-hang', label='Mua hàng', lotus='/lotus/mua-hang', groups=[
        dict(label='Chứng từ', items=[(D, 'Material Request', 'Đề nghị mua / cấp vật tư'), (D, 'Request for Quotation', 'Yêu cầu báo giá'),
                                      (D, 'Supplier Quotation', 'Báo giá nhà cung cấp'), (D, 'Purchase Order', 'Đơn mua hàng'),
                                      (D, 'Purchase Receipt', 'Phiếu nhận hàng'), (D, 'Purchase Invoice', 'Hóa đơn mua hàng')]),
        dict(label='Danh mục', items=[(D, 'Supplier', 'Nhà cung cấp'), (D, 'Supplier Group', 'Nhóm nhà cung cấp'),
                                      (D, 'Purchase Taxes and Charges Template', 'Mẫu thuế mua hàng')]),
        dict(label='Báo cáo', items=[(R, 'Purchase Register', 'Sổ mua hàng'), (R, 'Item-wise Purchase Register', 'Sổ mua hàng theo mặt hàng'),
                                     (R, 'Accounts Payable', 'Công nợ phải trả'), (R, 'Accounts Payable Summary', 'Tổng hợp công nợ phải trả'),
                                     (R, 'Procurement Tracker', 'Theo dõi mua hàng'), (R, 'Billed Items To Be Received', 'Đã có hóa đơn chưa nhận hàng'),
                                     (R, 'Purchase Analytics', 'Phân tích mua hàng'), (R, 'Supplier Ledger Summary', 'Tổng hợp sổ nhà cung cấp')]),
    ]),
    dict(id='kho', label='Kho', lotus='/lotus/kho', groups=[
        dict(label='Chứng từ', items=[(D, 'Stock Entry', 'Phiếu kho (mọi loại)'), (D, 'Stock Reconciliation', 'Kiểm kê / tồn đầu kỳ'),
                                      (D, 'Landed Cost Voucher', 'Chi phí phát sinh sau nhập'), (D, 'Pick List', 'Phiếu soạn hàng')]),
        dict(label='Danh mục', items=[(D, 'Item', 'Vật tư / hàng hóa'), (D, 'Item Group', 'Nhóm vật tư'), (D, 'Warehouse', 'Kho'),
                                      (D, 'UOM', 'Đơn vị tính'), (D, 'Batch', 'Lô hàng / hạn dùng'), (D, 'Brand', 'Nhãn hiệu')]),
        dict(label='Báo cáo', items=[(R, 'Stock Balance', 'Tồn kho (số lượng & giá trị)'), (R, 'Stock Ledger', 'Sổ chi tiết vật tư'),
                                     (R, 'Stock Ageing', 'Tuổi tồn kho'), (R, 'Stock Projected Qty', 'Tồn dự kiến'),
                                     (R, 'Batch-Wise Balance History', 'Tồn theo lô'), (R, 'Batch Item Expiry Status', 'Hạn dùng theo lô'),
                                     (R, 'Itemwise Recommended Reorder Level', 'Mức đặt hàng lại đề xuất'), (R, 'Item Shortage Report', 'Vật tư thiếu'),
                                     (R, 'Warehouse wise Item Balance Age and Value', 'Tồn theo kho, tuổi và giá trị')]),
    ]),
    dict(id='ke-toan', label='Kế toán', lotus='/lotus/tai-chinh', groups=[
        dict(label='Chứng từ', items=[(D, 'Journal Entry', 'Bút toán'), (D, 'Payment Entry', 'Phiếu thu / chi'),
                                      (D, 'Bank Transaction', 'Giao dịch ngân hàng'), (D, 'Period Closing Voucher', 'Khóa sổ cuối kỳ')]),
        dict(label='Danh mục', items=[(D, 'Account', 'Hệ thống tài khoản'), (D, 'Cost Center', 'Trung tâm chi phí'), (D, 'Bank Account', 'Tài khoản ngân hàng'),
                                      (D, 'Bank', 'Ngân hàng'), (D, 'Mode of Payment', 'Hình thức thanh toán'), (D, 'Fiscal Year', 'Năm tài chính'),
                                      (D, 'Accounting Period', 'Kỳ kế toán'), (D, 'Budget', 'Ngân sách'), (D, 'Currency Exchange', 'Tỷ giá')]),
        dict(label='Báo cáo', items=[(R, 'General Ledger', 'Sổ cái'), (R, 'Trial Balance', 'Bảng cân đối số phát sinh'), (R, 'Balance Sheet', 'Bảng cân đối kế toán'),
                                     (R, 'Profit and Loss Statement', 'Kết quả kinh doanh'), (R, 'Cash Flow', 'Lưu chuyển tiền tệ'),
                                     (R, 'Accounts Receivable', 'Công nợ phải thu'), (R, 'Accounts Payable', 'Công nợ phải trả'),
                                     (R, 'Bank Reconciliation Statement', 'Đối chiếu ngân hàng'),
                                     (R, 'Payment Ledger', 'Sổ thanh toán')]),
    ]),
    dict(id='tai-san', label='Tài sản', lotus=None, groups=[
        dict(label='Chứng từ', items=[(D, 'Asset', 'Tài sản cố định'), (D, 'Asset Movement', 'Điều chuyển tài sản'), (D, 'Asset Repair', 'Sửa chữa tài sản'),
                                      (D, 'Asset Value Adjustment', 'Đánh giá lại tài sản'), (D, 'Asset Capitalization', 'Ghi tăng tài sản')]),
        dict(label='Danh mục', items=[(D, 'Asset Category', 'Nhóm tài sản'), (D, 'Location', 'Địa điểm đặt tài sản')]),
        dict(label='Báo cáo', items=[(R, 'Fixed Asset Register', 'Sổ tài sản cố định'), (R, 'Asset Depreciation Ledger', 'Sổ khấu hao'),
                                     (R, 'Asset Depreciations and Balances', 'Khấu hao và giá trị còn lại')]),
    ]),
    dict(id='nhan-su', label='Nhân sự', lotus='/lotus/nhan-su', groups=[
        dict(label='Biến động nhân sự', items=[(D, 'Employee Onboarding', 'Tiếp nhận nhân viên'), (D, 'Employee Transfer', 'Điều chuyển'),
                                               (D, 'Employee Promotion', 'Thăng chức / đổi chức danh'), (D, 'Employee Separation', 'Nghỉ việc'),
                                               (D, 'Job Opening', 'Vị trí tuyển dụng'), (D, 'Job Applicant', 'Ứng viên (HRMS)')]),
        dict(label='Danh mục', items=[(D, 'Employee', 'Nhân viên'), (D, 'Department', 'Bộ phận'), (D, 'Designation', 'Chức danh'),
                                      (D, 'Employee Grade', 'Ngạch / bậc'), (D, 'Employment Type', 'Loại hợp đồng / lao động'), (D, 'Branch', 'Chi nhánh')]),
        dict(label='Báo cáo', items=[(R, 'Employee Analytics', 'Phân tích nhân sự'), (R, 'Employee Birthday', 'Sinh nhật nhân viên'),
                                     (R, 'Employee Exits', 'Nhân viên nghỉ việc')]),
    ]),
    dict(id='nghi-phep', label='Nghỉ phép & chấm công', lotus='/lotus/cham-cong', groups=[
        dict(label='Nghỉ phép', items=[(D, 'Leave Application', 'Đơn xin nghỉ'), (D, 'Leave Allocation', 'Cấp ngày phép'), (D, 'Leave Type', 'Loại nghỉ'),
                                       (D, 'Leave Policy', 'Chính sách phép'), (D, 'Leave Policy Assignment', 'Áp chính sách phép'),
                                       (D, 'Compensatory Leave Request', 'Nghỉ bù'), (D, 'Holiday List', 'Lịch ngày lễ')]),
        dict(label='Chấm công & ca', items=[(D, 'Attendance', 'Chấm công'), (D, 'Attendance Request', 'Giải trình chấm công'), (D, 'Employee Checkin', 'Lượt chấm'),
                                            (D, 'Shift Type', 'Loại ca'), (D, 'Shift Assignment', 'Phân ca'), (D, 'Shift Request', 'Đề nghị đổi ca')]),
        dict(label='Báo cáo', items=[(R, 'Employee Leave Balance', 'Số ngày phép còn lại'), (R, 'Employee Leave Balance Summary', 'Tổng hợp ngày phép'),
                                     (R, 'Leave Ledger', 'Sổ ngày phép'), (R, 'Monthly Attendance Sheet', 'Bảng chấm công tháng'),
                                     (R, 'Employees working on a holiday', 'Làm việc ngày lễ')]),
    ]),
    dict(id='luong', label='Lương', lotus='/lotus/nhan-su?hr_view=payroll', groups=[
        dict(label='Chứng từ', items=[(D, 'Payroll Entry', 'Bảng lương kỳ'), (D, 'Salary Slip', 'Phiếu lương'), (D, 'Additional Salary', 'Thưởng / phạt / khấu trừ'),
                                      (D, 'Employee Incentive', 'Khen thưởng'), (D, 'Employee Advance', 'Tạm ứng nhân viên'), (D, 'Expense Claim', 'Thanh toán chi phí / hoàn ứng')]),
        dict(label='Thiết lập', items=[(D, 'Salary Component', 'Thành phần lương'), (D, 'Salary Structure', 'Cấu trúc lương'),
                                       (D, 'Salary Structure Assignment', 'Gán cấu trúc lương'), (D, 'Payroll Period', 'Kỳ tính lương'),
                                       (D, 'Expense Claim Type', 'Loại chi phí')]),
        dict(label='Báo cáo', items=[(R, 'Salary Register', 'Sổ lương'), (R, 'Employee Advance Summary', 'Tổng hợp tạm ứng')]),
    ]),
]
