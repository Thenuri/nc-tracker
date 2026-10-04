"""Date helpers for NC deadlines."""

from datetime import timedelta


def add_working_days(start, days):
    """Return the date `days` working days (Mon–Fri) after `start`.

    Public holidays are not counted yet; that list is [TBC] with APIIT.
    """
    current = start
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:  # 0=Mon … 4=Fri
            added += 1
    return current
