"""Small, framework-free date rules for farm ribbon-color periods."""
import hashlib
from datetime import date, datetime

# Once a line of the sổ lô uses a colour, these stay as they were (Bunch Tag.validate).
LOCKED = ("farm", "tag_code", "color_code", "color_label", "period_basis", "valid_from", "valid_to", "week_year", "week_number",
          "week_half", "source_kind")
DATES, WHOLE_NUMBERS = ("valid_from", "valid_to"), ("week_year", "week_number")


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


def stored(field, value):
    """A value as the database keeps it. Bunch Tag.validate runs before Frappe casts the fields, and the Danh mục form and
    Desk send a date as text, may send a number as text, and an empty value as "" (an empty whole number is kept as 0)."""
    if field in WHOLE_NUMBERS:
        try:
            return int(float(value or 0))
        except (TypeError, ValueError):
            return value
    if value is None or value == "":
        return None
    if field in DATES:
        try:
            return day(value)
        except ValueError:
            return value
    return value


def locked_changes(before, after):
    """The locked fields whose stored value differs between the saved tag and the one being saved."""
    return [field for field in LOCKED if stored(field, before.get(field)) != stored(field, after.get(field))]
