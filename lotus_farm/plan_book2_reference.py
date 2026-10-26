"""Book2 26/10/2026 production-plan catalogue; read-only reference.

This table records Excel DM_CONG_VIEC (CV001..CV043), NOT approved ERP Work Types.
An unmatched code, missing productivity, or unknown work anchor must not silently
generate Daily Work Plans, Purchase Orders or payroll entries.
"""
from __future__ import annotations

from lotus_farm import forecast_book2_reference as book2

SOURCE = "Lotus_Lich_Tro_2_Vu_Don_Gia_Nhan_Cong_2026_2028.xlsx"
SHEET = "DM_CONG_VIEC"
# Each line: work code | group | description | reported unit | Book2 timing
DATA = """
CV001|Chăm sóc vườn|Kiểm tra và vận hành tưới|lô|Theo lịch tưới
CV002|Chăm sóc vườn|Kiểm tra, sửa béc tưới|ha|2 lần/tháng
CV003|Chăm sóc vườn|Cắt lá|ha|1 lần/tháng
CV004|Chăm sóc vườn|Làm cỏ gốc, dọn bẹ khô|ha|2 tháng 1 lần
CV005|Chăm sóc vườn|Dọn lá cọ buồng|ha|1 lần/vụ lúc trổ
CV006|Chăm sóc vườn|Cào lá gốc|ha|1 lần/vụ sau chặt dọn
CV007|Chăm sóc vườn|Bón phân hữu cơ|cây|1 lần/vụ sau chặt dọn
CV008|Chăm sóc vườn|Bón lân, vôi|cây|1 lần/vụ sau chặt dọn
CV009|Chăm sóc vườn|Bón phân hóa học|cây|1 lần/tháng
CV010|Chăm sóc vườn|Phun thuốc bằng drone|ha|2 lần/tháng
CV011|Chăm sóc vườn|Xịt cỏ|ha|1 lần/tháng
CV012|Chăm sóc vườn|Xịt bệnh gốc|ha|Theo tình hình bệnh
CV013|Chăm sóc vườn|Phun thân bằng xe cày|ha|Theo tình hình bệnh
CV014|Chăm sóc vườn|Xắn chồi lần 1|cây|Theo vụ
CV015|Chăm sóc vườn|Xắn chồi lần 2|cây|Theo vụ
CV016|Chăm sóc vườn|Cắt, hủy chồi không chọn|ha|Định kỳ, cần xác nhận
CV017|Chăm sóc vườn|Chọn chồi vụ sau|ha|Theo vụ
CV018|Chăm sóc vườn|Chặt cây mẹ lần 1|cây|Sau thu, giữ thân khoảng 2m
CV019|Chăm sóc vườn|Chặt cây mẹ lần 2|cây|Khoảng 2 tháng lịch sau lần 1
CV020|Chăm sóc buồng|Chích búp/bắp|buồng|Trổ +5 ngày; phải thấy bắp
CV021|Chăm sóc buồng|Chống đổ ngã|cây|Chích +5 ngày, cửa sổ +3..+10
CV022|Chăm sóc buồng|Vén lá, tỉa trái|buồng|Chích +7 ngày
CV023|Chăm sóc buồng|Lặt hoa lần 1|buồng|Chích +7 ngày
CV024|Chăm sóc buồng|Phun buồng lần 1|buồng|Chích +7 ngày
CV025|Chăm sóc buồng|Lặt hoa lần 2|buồng|Chích +10 ngày
CV026|Chăm sóc buồng|Phun buồng lần 2|buồng|Chích +10 ngày
CV027|Chăm sóc buồng|Lặt hoa lần 3|buồng|Chích +13 ngày
CV028|Chăm sóc buồng|Phun buồng lần 3|buồng|Chích +13 ngày
CV029|Chăm sóc buồng|Cắt bắp/cắt búp|buồng|Chích +16 ngày (ngày thứ 17)
CV030|Chăm sóc buồng|Cột dây màu|buồng|Chích +16 ngày
CV031|Chăm sóc buồng|Phun buồng lần 4|buồng|Chích +16 ngày
CV032|Chăm sóc buồng|Lót nải, chèn xốp|buồng|Chích +16 ngày
CV033|Chăm sóc buồng|Bao định hình, chống nắng, bao ngoài|buồng|Chích +16 ngày, sau lần phun 4
CV034|Thu hoạch|Đo trái trước thu|buồng|Thu -10 đến -7 ngày
CV035|Thu hoạch|Cắt buồng, vác ra đường lô|buồng|Chích +81 ngày
CV036|Thu hoạch|Vận chuyển buồng về xưởng|buồng|Chích +81 ngày
CV037|Thu hoạch|Thu phụ phẩm thân, lá|cây|Sau thu
CV038|Thu hoạch|Hạ cây, dọn cây sau thu|cây|Sau thu
CV039|Đóng gói|Tiếp nhận, cân và kiểm tra buồng|buồng|Theo ngày thu
CV040|Đóng gói|Xén nải, xử lý và phân loại|buồng|Theo ngày thu
CV041|Đóng gói|Rửa, làm khô, cân|kg|Theo ngày thu
CV042|Đóng gói|Lót xốp, dán thùng, đóng gói|thùng|Theo ngày thu
CV043|Đóng gói|Kiểm tra chất lượng, bảo quản|thùng|Theo ngày thu
""".strip()

PERIODIC = {
    "CV002": {"times_per_month": 2},
    "CV003": {"times_per_month": 1},
    "CV004": {"repeat_months": 2, "requires_start_month": True},
    "CV009": {"times_per_month": 1},
    "CV010": {"times_per_month": 2, "requires_chemical_approval": True},
    "CV011": {"times_per_month": 1},
}
# Event offsets are only informational until the chosen Work Schedule Rule version is approved.
# 'Injection' / 'Harvest' are not supported as direct Work Schedule Rule anchors today.
INJECTION_OFFSETS = {
    "CV021": 5,
    "CV022": 7, "CV023": 7, "CV024": 7,
    "CV025": 10, "CV026": 10,
    "CV027": 13, "CV028": 13,
    "CV029": 16, "CV030": 16, "CV031": 16, "CV032": 16, "CV033": 16,
    "CV035": 81, "CV036": 81,
}
NOT_AUTO_SCHEDULE = frozenset(("CV001", "CV004", "CV006", "CV007", "CV008",
                              "CV012", "CV013", "CV014", "CV015", "CV016",
                              "CV017", "CV018", "CV019", "CV034", "CV037", "CV038"))

def catalogue():
    rows = []
    for line in DATA.splitlines():
        code, group, title, unit, timing = line.split("|")
        rows.append(dict(code=code, group=group, title=title, unit=unit,
                         timing=timing, periodic=PERIODIC.get(code),
                         injection_offset_days=INJECTION_OFFSETS.get(code),
                         requires_manual_anchor=code in NOT_AUTO_SCHEDULE or code in INJECTION_OFFSETS))
    if len(rows) != 43 or len({r["code"] for r in rows}) != 43:
        raise ValueError("Book2 work catalogue must contain 43 distinct codes")
    return rows

def compare(works=None):
    """Annotate the Excel reference using existing Farm permission-filtered Work Types."""
    by_code = {str(w.get("work_code") or "").strip().upper(): w for w in (works or [])
               if w.get("work_code")}
    rows = []
    for row in catalogue():
        match = by_code.get(row["code"])
        rows.append(dict(**row, matched=bool(match),
                         work_type=match.get("name") if match else None,
                         productivity=match.get("productivity_per_workday") if match else None,
                         piecework_rate=match.get("piecework_rate") if match else None,
                         allow_daywork=match.get("allow_daywork") if match else None))
    missing = [r["code"] for r in rows if not r["matched"]]
    no_productivity = [r["code"] for r in rows if r["matched"] and not (
        isinstance(r["productivity"], (int, float)) and r["productivity"] > 0)]
    return {
        "source": SOURCE, "sheet": SHEET,
        "works": rows, "missing_codes": missing,
        "missing_productivity": no_productivity,
        "daywork_rate": 290000, "absence_reserve": 0.10, "workdays_per_week": 6,
        "bunch_allowance_per_day": 20000, "spray_allowance_per_day": 20000,
        "attendance_bonus_month": 300000,
        "flower_shares": [0.17, 0.40, 0.25, 0.18],
        "warning": (
            "Bảng Book2 chỉ để đối chiếu, chưa tạo/duyệt Work Type, Work Schedule Rule "
            "hoặc Material Norm Profile. Công nhật và khoán là hai phương án khác nhau. "
            "Công việc theo chích/thu cần xác minh mốc, công việc định kỳ cần ngày khởi động; "
            "năng suất và phác đồ thuốc chưa duyệt không được dùng đặt mua tự động."
        ),
    }
