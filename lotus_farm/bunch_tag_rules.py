"""Small, framework-free date rules for farm ribbon-color periods."""
import hashlib
from datetime import date, datetime


def day(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def overlaps(start, end, other_start, other_end):
    """Inclusive intervals; an omitted end means an open-ended legacy record."""
    return day(start) <= (day(other_end) if other_end else date.max) and (
        day(other_start) if other_start else date.min
    ) <= day(end)


def manual_tag_code(farm, start, color_code):
    """Stable, compact identifier; do not use farm display text as a key."""
    digest = hashlib.sha256(str(farm).encode("utf-8")).hexdigest()[:12]
    return "MAN-" + digest + "-" + day(start).strftime("%Y%m%d") + "-" + str(color_code)
