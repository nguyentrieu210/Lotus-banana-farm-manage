"""Rules independent from Frappe, shared by the Lotus HR intake endpoints."""
import re

STAGES = {
    "New": {"Screening", "Rejected"},
    "Screening": {"Interview", "Offered", "Rejected", "Hold"},
    "Interview": {"Offered", "Rejected", "Hold"},
    "Offered": {"Hired", "Rejected", "Hold"},
    "Hold": {"Screening", "Interview", "Rejected"},
    "Rejected": {"Screening"},
    "Hired": set(),
}
WORKER_CATEGORIES = ("Permanent", "Fixed-term", "Seasonal", "Probation")
PAYMENT_BASES = ("Monthly", "Daywork", "Piecework", "Mixed")

def normalize_cccd(value):
    """Normalize spaces and dashes, but do not accept partial or fabricated identifiers."""
    raw = re.sub(r"[\s-]", "", str(value or ""))
    if not re.fullmatch(r"[0-9]{12}", raw):
        raise ValueError("CCCD phải gồm đúng 12 chữ số.")
    return raw

def normalized_phone(value):
    raw = re.sub(r"[\s().-]", "", str(value or ""))
    if not re.fullmatch(r"\+?[0-9]{9,15}", raw):
        raise ValueError("Số điện thoại cần từ 9 đến 15 chữ số.")
    return raw

def transition_allowed(old, new):
    return old == new or new in STAGES.get(old, set())

def onboarding_gaps(employee):
    """Minimum data for basic intake; supporting documents can follow later."""
    needed = {
        "employee_name": "Họ tên",
        "gender": "Giới tính",
        "date_of_birth": "Ngày sinh",
        "date_of_joining": "Ngày vào làm",
        "cell_number": "Số điện thoại",
        "designation": "Chức danh",
        "lotus_worker_category": "Loại nhân sự",
        "lotus_payment_basis": "Hình thức tính công/lương",
    }
    return [label for field, label in needed.items() if not employee.get(field)]


def dossier_gaps(employee):
    """Supplementary documents, independent from basic intake approval."""
    needed = {
        "lotus_cccd_hash": "CCCD",
        "lotus_id_issue_on": "Ngày cấp CCCD",
        "lotus_id_issue_at": "Nơi cấp CCCD",
        "current_address": "Địa chỉ hiện tại",
        "lotus_emergency_name": "Người liên hệ khẩn cấp",
        "lotus_emergency_phone": "Điện thoại khẩn cấp",
    }
    return [label for field, label in needed.items() if not employee.get(field)]
