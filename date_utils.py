"""Calendar dates from Flet's UTC-normalized datetime transport."""
from datetime import date, datetime


def calendar_date(value: date | datetime | None) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime) and value.tzinfo is not None:
        # DatePicker selects local midnight; the transport sends that instant in UTC.
        value = value.astimezone()
    return value.strftime("%Y-%m-%d")


def open_calendar(page, picker, value: str | None) -> None:
    try:
        picker.value = date.fromisoformat(value or "")
    except ValueError:
        picker.value = date.today()
    page.show_dialog(picker)
