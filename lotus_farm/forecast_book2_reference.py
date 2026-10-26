"""Book2/26-10-2026 forecast parameter reference (read-only).

The Excel workbook is a planning reference, NOT an approved production profile.
No historical approved profile, harvest document or financial plan is rewritten.
"""
from __future__ import annotations

from lotus_farm import cut_forecast_rules as rules

SOURCE_FILE = "Lotus_Lich_Tro_2_Vu_Don_Gia_Nhan_Cong_2026_2028.xlsx"
SOURCE_SHEETS = "TS_DU_TRO; DM_THONG_SO; DM_CONG_VIEC; 07_THONG_SO"

# Only fields supported by the existing 16-field cut-forecast engine belong here.
# These are a proposed NEW version, never a mutation of the saved approved version.
PROFILE_PATCH = {
    "days_to_first_shoot": 180,  # assumption: cut mother 2 -> flowering, NOT sucker selection -> flowering
    "wave_step_days": 30,
    "window_days": 30,
    "representative_day": 14,
    "shoot_to_inject_days": 5,  # provisional; injection must be checked in the field
    "inject_to_budcut_days": 16,  # procedure day 17 counts the injection day as day 1
    "budcut_to_harvest_days": 65,  # provisional; field fruit-measurement may override
    "cut_rate": 0.90,
    "harvest_rate": 0.97,
    "pack_rate": 0.98,
    "kg_per_bunch": 20,  # cycle 2 estimate; engine currently does NOT distinguish cycles
    "sucker_per_tree": 1,  # counted standing trees MUST NOT be multiplied by 0.97 again
    "wave_1_share": 0.17,
    "wave_2_share": 0.40,
    "wave_3_share": 0.25,
    "wave_4_share": 0.18,
}

# Other Excel parameters need independent master-data/schedule integration.
# They are displayed as references, not silently applied to harvest forecasts.
EXTRA = (
    ("sucker_selection_to_flower_months", 6, "tháng", "Kỹ thuật xác nhận", "Tính từ CHỌN CHỒI, không phải từ chặt mẹ lần 2"),
    ("sucker_selection_to_first_harvest_months", 8, "tháng", "Kịch bản", "Khu A chọn chồi 01/11/2026, dự kiến bắt đầu thu 07/2027"),
    ("next_generation_sucker_yield", 0.97, "tỷ lệ", "Giả định", "Chỉ áp khi dự phóng cây mẹ thành chồi vụ kế tiếp"),
    ("apply_next_generation_yield_to_existing_trees", 0, "0/1", "Không áp", "Số cây hiện hữu hoặc kiểm kê đã là đầu vào trực tiếp"),
    ("finished_kg_per_bunch_cycle_1", 19, "kg/buồng đạt", "Tạm chốt", "Không dùng 20kg chung cho vụ 1"),
    ("finished_kg_per_bunch_cycle_2", 20, "kg/buồng đạt", "Tạm chốt", "Giữ phân biệt kg thành phẩm và kg buồng thô"),
    ("finished_kg_per_bunch_cycle_3_plus", 19, "kg/buồng đạt", "Tạm chốt", "Cần loại vụ cây để chọn trọng lượng"),
    ("flower_removal_days_after_injection", (7, 10, 13), "ngày", "Theo quy trình", "Ba lần lặt hoa; quy trình ngày 8/11/14 tương ứng +7/+10/+13"),
    ("flower_spray_rounds", 4, "lần/buồng", "Theo quy trình", "Định mức NC20 cũ có thể mới tính 3 lần; tránh nhân đôi gói việc"),
    ("fruit_measure_days_before_harvest", (10, 7), "ngày", "Áp dụng Book2", "Cửa sổ thu-10 đến thu-7; đo thực tế rồi mới chốt ngày cắt"),
    ("support_after_injection_window", (3, 10), "ngày", "Theo quy trình", "Chống đổ có cửa sổ +3 tới +10, Book2 ưu tiên mục tiêu +5"),
    ("sacks_per_container", 1320, "thùng/cont 40ft", "Tham chiếu", "Chỉ tính khi có kế hoạch đóng gói"),
    ("finished_kg_per_carton", 13, "kg/thùng", "Tham chiếu", "Không cộng với kg thành phẩm/buồng"),
    ("workdays_per_week", 6, "ngày", "Giả định kế hoạch", "Không thay cho ngày công chấm thực tế"),
    ("absence_reserve", 0.10, "tỷ lệ", "Giả định", "Chỉ dùng định biên dự phòng"),
    ("basic_day_wage_vnd", 290000, "VND/ngày", "Theo bảng giá", "Không tự cộng đơn giá khoán vào công nhật"),
    ("bunch_care_allowance_vnd", 20000, "VND/ngày", "Theo bảng giá", "Chỉ áp khi đủ điều kiện"),
    ("irrigation_nozzle_check_per_month", 2, "lần/tháng", "Áp dụng Book2", "Khác bảng kế hoạch cũ 3 lần/tháng"),
    ("leaf_cutting_per_month", 1, "lần/tháng", "Áp dụng Book2", "Khác bảng kế hoạch cũ 3 lần/tháng"),
    ("root_weeding_repeat_months", 2, "tháng/lần", "Áp dụng Book2", "Cần xác nhận ngày khởi động của từng lô"),
    ("chemical_fertilizing_per_month", 1, "lần/tháng", "Áp dụng Book2", "Chưa phải phác đồ vật tư"),
    ("drone_spraying_per_month", 2, "lần/tháng", "Áp dụng Book2", "Liều lượng/phác đồ phải có duyệt kỹ thuật"),
    ("second_mother_cut_after_first_months", 2, "tháng", "Áp dụng Book2", "Tháng lịch; không ép thành 60 ngày"),
)


def reference(current_profile=None):
    """Safe UI payload, including differences against an already approved profile."""
    params, errors = rules.validate_profile(PROFILE_PATCH)
    if errors:
        raise ValueError("Invalid Book2 reference: " + "; ".join(errors))
    current_profile = current_profile or {}
    comparisons = []
    for field, label, _kind, _default in rules.PARAMS:
        old = current_profile.get(field)
        new = params[field]
        changed = old is not None and abs(float(old) - float(new)) > 1e-9
        comparisons.append(dict(field=field, label=label, approved=old,
                                excel=new, changed=changed))
    return {
        "source_file": SOURCE_FILE,
        "source_sheets": SOURCE_SHEETS,
        "profile_patch": params,
        "comparisons": comparisons,
        "different_count": sum(int(x["changed"]) for x in comparisons),
        "extras": [
            dict(code=key, value=list(value) if isinstance(value, tuple) else value,
                 unit=unit, status=status, note=note)
            for key, value, unit, status, note in EXTRA
        ],
        "warning": (
            "Excel 26/10 là nguồn tham chiếu, không phải dữ liệu đã nghiệm thu. "
            "180 ngày chặt mẹ 2→trổ, 5 ngày trổ→chích và hệ số 0,97 chồi đều cần kiểm chứng. "
            "Nạp các giá trị này chỉ vào form NHÁP; bấm lưu mới tạo phiên bản thông số được duyệt. "
            "Số 19/20/19 kg theo vụ và lịch 2 thế hệ cần nâng cấp mô hình theo lô/vụ trước khi tự áp."
        ),
    }
