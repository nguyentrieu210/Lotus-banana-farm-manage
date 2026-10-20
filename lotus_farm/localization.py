"""Vietnamese display labels. Document identifiers and stored links are unchanged."""
import frappe

ROLE_LABELS = {
    "Lotus Work Journal Clerk": "Nhân viên nhập nhật ký công việc",
    "System Manager": "Quản trị hệ thống",
    "HR Manager": "Quản lý nhân sự",
    "HR User": "Nhân viên nhân sự",
    "Stock Manager": "Quản lý kho",
    "Stock User": "Nhân viên kho",
    "Purchase Manager": "Quản lý mua hàng",
    "Purchase User": "Nhân viên mua hàng",
    "Lotus Farm Manager": "Quản lý vườn",
    "Lotus Sales Planner": "Lập kế hoạch bán hàng",
    "Lotus QC Manager": "Quản lý chất lượng",
    "Lotus Packing Supervisor": "Giám sát đóng gói",
    "Lotus Integration User": "Tích hợp dữ liệu",
    "Lotus Auditor": "Kiểm tra và đối soát",
    "Lotus Stock Reviewer": "Kiểm duyệt kho",
    "Lotus Price Approver": "Duyệt đơn giá",
    "Lotus Team Leader": "Tổ trưởng hiện trường",
    "Lotus Field Supervisor": "Giám sát hiện trường",
    "Lotus Purchasing Buyer": "Nhân viên thu mua Lotus",
    "Lotus Warehouse Requester": "Người đề nghị xuất kho Lotus",
    "Lotus Purchase Approver": "Người duyệt mua hàng Lotus",
    "Lotus Warehouse Manager": "Quản lý kho Lotus",
    "Lotus Warehouse Receiver": "Nhân viên nhận hàng Lotus",
    "Lotus Purchase Requester": "Người đề nghị mua hàng Lotus",
    "Lotus Warehouse Operator": "Nhân viên nghiệp vụ kho Lotus",
    "Lotus Crew Leader": "Tổ trưởng chấm công",
    "Employee Self Service": "Nhân viên tự phục vụ",
    "Leave Approver": "Người duyệt nghỉ phép",
    "Interviewer": "Người phỏng vấn",
    "Expense Approver": "Người duyệt chi phí",
    "Analytics": "Phân tích dữ liệu",
    "Supplier": "Nhà cung cấp",
    "Customer": "Khách hàng",
    "Academics User": "Nhân viên đào tạo",
    "Fleet Manager": "Quản lý đội xe",
    "Fulfillment User": "Nhân viên xử lý đơn hàng",
    "Support Team": "Nhóm hỗ trợ",
    "Item Manager": "Quản lý vật tư và hàng hóa",
    "Projects Manager": "Quản lý dự án",
    "Projects User": "Nhân viên dự án",
    "Delivery Manager": "Quản lý giao hàng",
    "Auditor": "Kiểm toán viên",
    "Employee": "Nhân viên",
    "Quality Manager": "Quản lý chất lượng",
    "Delivery User": "Nhân viên giao hàng",
    "Manufacturing Manager": "Quản lý sản xuất",
    "Manufacturing User": "Nhân viên sản xuất",
    "Purchase Master Manager": "Quản lý danh mục mua hàng",
    "Sales Master Manager": "Quản lý danh mục bán hàng",
    "Maintenance Manager": "Quản lý bảo trì",
    "Maintenance User": "Nhân viên bảo trì",
    "Accounts User": "Nhân viên kế toán",
    "Sales User": "Nhân viên bán hàng",
    "Knowledge Base Contributor": "Người đóng góp kho kiến thức",
    "Knowledge Base Editor": "Biên tập kho kiến thức",
    "Newsletter Manager": "Quản lý bản tin",
    "Marketing Manager": "Quản lý tiếp thị",
    "Translator": "Biên dịch viên",
    "Prepared Report User": "Người dùng báo cáo tạo sẵn",
    "Accounts Manager": "Quản lý kế toán",
    "Sales Manager": "Quản lý bán hàng",
    "Inbox User": "Người dùng hộp thư",
    "Script Manager": "Quản lý mã lệnh",
    "Report Manager": "Quản lý báo cáo",
    "Workspace Manager": "Quản lý không gian làm việc",
    "Dashboard Manager": "Quản lý bảng tổng quan",
    "Website Manager": "Quản lý website",
    "Administrator": "Quản trị viên gốc",
    "Desk User": "Người dùng giao diện quản trị",
    "All": "Tất cả người dùng",
    "Guest": "Khách vãng lai"
}

CATALOG_LABELS = {
    "Genderqueer": "Đa dạng giới",
    "Non-Conforming": "Không theo chuẩn giới",
    "Prefer not to say": "Không muốn nêu",
    "Transgender": "Chuyển giới",
    "Accountant": "Kế toán",
    "Administrative Assistant": "Trợ lý hành chính",
    "Administrative Officer": "Chuyên viên hành chính",
    "Analyst": "Chuyên viên phân tích",
    "Associate": "Chuyên viên",
    "Business Analyst": "Chuyên viên phân tích nghiệp vụ",
    "Business Development Manager": "Quản lý phát triển kinh doanh",
    "Chief Executive Officer": "Tổng giám đốc",
    "Chief Financial Officer": "Giám đốc tài chính",
    "Chief Operating Officer": "Giám đốc vận hành",
    "Chief Technology Officer": "Giám đốc công nghệ",
    "Consultant": "Chuyên viên tư vấn",
    "Customer Service Representative": "Nhân viên chăm sóc khách hàng",
    "Designer": "Nhân viên thiết kế",
    "Engineer": "Kỹ sư",
    "Executive Assistant": "Trợ lý ban giám đốc",
    "Finance Manager": "Quản lý tài chính",
    "Head of Marketing and Sales": "Trưởng bộ phận tiếp thị và bán hàng",
    "HR Manager": "Quản lý nhân sự",
    "Manager": "Quản lý",
    "Managing Director": "Giám đốc điều hành",
    "Marketing Manager": "Quản lý tiếp thị",
    "Marketing Specialist": "Chuyên viên tiếp thị",
    "President": "Chủ tịch",
    "Product Manager": "Quản lý sản phẩm",
    "Project Manager": "Quản lý dự án",
    "Researcher": "Nghiên cứu viên",
    "Sales Representative": "Nhân viên kinh doanh",
    "Secretary": "Thư ký",
    "Software Developer": "Lập trình viên",
    "Vice President": "Phó chủ tịch",
    "Accounts": "Kế toán",
    "Customer Service": "Chăm sóc khách hàng",
    "Dispatch": "Điều vận",
    "Human Resources": "Nhân sự",
    "Legal": "Pháp chế",
    "Management": "Quản lý",
    "Marketing": "Tiếp thị",
    "Operations": "Vận hành",
    "Production": "Sản xuất",
    "Purchase": "Mua hàng",
    "Quality Management": "Quản lý chất lượng",
    "Research & Development": "Nghiên cứu và phát triển",
    "Sales": "Kinh doanh",
    "All Departments": "Tất cả phòng ban"
}

def catalog_label(value):
    if not value:
        return value
    # Department identifiers may carry a company abbreviation.
    base, separator, suffix = value.rpartition(' - ')
    if separator and base in CATALOG_LABELS:
        return CATALOG_LABELS[base] + separator + suffix
    return CATALOG_LABELS.get(value, frappe._(value, lang='vi'))


def install_translations():
    from frappe.custom.doctype.property_setter.property_setter import make_property_setter
    for dt, field in [('Department', 'department_name'), ('Designation', 'designation_name')]:
        make_property_setter(dt, None, 'translated_doctype', 1, 'Check', for_doctype=True)
        make_property_setter(dt, field, 'translatable', 1, 'Check')
    # Department names include the company abbreviation. Keep all linked identifiers intact.
    for dt in ('Department', 'Designation'):
        for name in frappe.get_all(dt, pluck='name', limit_page_length=0):
            translated = catalog_label(name)
            if translated != name and not frappe.db.exists('Translation', {'language': 'vi', 'source_text': name}):
                frappe.get_doc(dict(doctype='Translation', language='vi', source_text=name,
                                    translated_text=translated)).insert(ignore_permissions=True)
    from frappe.translate import clear_cache
    clear_cache()
