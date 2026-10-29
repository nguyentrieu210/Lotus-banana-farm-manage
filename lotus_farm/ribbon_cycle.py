"""Lotus-222 twelve-colour weekly ribbon cycle; framework-free so it can be unit tested."""
from datetime import date, timedelta


FARM = "LOTUS-222"
START = date(2026, 10, 19)  # ISO Monday of week 43/2026
END = date(2027, 12, 31)
CYCLE = [
    ("DO", "Đỏ"),
    ("TRANG", "Trắng"),
    ("TIM", "Tím"),
    ("CAM", "Cam"),
    ("DEN", "Đen"),
    ("XANH_DUONG", "Xanh dương"),
    ("DO_XANH_LA", "Đỏ - Xanh lá"),
    ("TRANG_XANH_LA", "Trắng - Xanh lá"),
    ("TIM_XANH_LA", "Tím - Xanh lá"),
    ("CAM_XANH_LA", "Cam - Xanh lá"),
    ("DEN_XANH_LA", "Đen - Xanh lá"),
    ("XANH_LA_XANH_DUONG", "Xanh lá - Xanh dương"),
]
COLORS = dict(CYCLE)


def week_color(monday):
    """Colour of the ISO week starting on this Monday (12-week cycle from W43/2026)."""
    return CYCLE[((monday - START).days // 7) % len(CYCLE)]


def periods():
    monday = START
    while monday <= END:
        code, label = week_color(monday)
        iso = monday.isocalendar()
        for half, a, b in ((1, 0, 3), (2, 4, 6)):  # Mon–Thu, Fri–Sun: same colour
            yield {
                "week_year": iso.year, "week_number": iso.week, "week_half": str(half),
                "color_code": code, "color_label": label,
                "valid_from": str(monday + timedelta(days=a)),
                "valid_to": str(monday + timedelta(days=b)),
                "tag_code": f"LOTUS-222:W{iso.year}-{iso.week:02d}-P{half}:{code}",
                "display_name": f"{label} · Tuần {iso.week}/{iso.year}",
            }
        monday += timedelta(days=7)
