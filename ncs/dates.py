"""Date helpers for NC deadlines."""

from datetime import timedelta


def add_working_days(start, days, holidays=None):
    """Return the date `days` working days after `start` (FR-14).

    Working days are Monday to Friday, skipping the public holidays the NC
    Manager has entered (core.PublicHoliday). Pass `holidays` (a set of dates)
    to skip the database lookup, e.g. in tests.
    """
    if holidays is None:
        from core.models import PublicHoliday  # here, so this module stays importable on its own

        # Generous window: enough room even if several holidays fall in a row.
        holidays = set(PublicHoliday.objects.filter(date__gt=start, date__lte=start + timedelta(days=days * 2 + 60))
                       .values_list("date", flat=True))
    current = start
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5 and current not in holidays:  # 0=Mon … 4=Fri
            added += 1
    return current
