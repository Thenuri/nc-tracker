"""Numbers for the dashboard (FR-33, FR-34, FR-35).

Everything is calculated from the NCs the person may see, so an Action Owner
gets a department view and HoDs/Management get the whole institution.
"""

from datetime import date

from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.utils import timezone

from ncs.models import NC

S = NC.Status

# Closure ageing buckets: (label, smallest days, largest days or None)
AGEING_BUCKETS = [("0–30 days", 0, 30), ("31–60 days", 31, 60), ("61–90 days", 61, 90), ("Over 90 days", 91, None)]


def status_counts(ncs):
    """FR-33 tiles. 'Open' excludes Closed and Not Valid (FR-15)."""
    by_status = dict(ncs.values_list("status").annotate(n=Count("pk")))
    return {
        "total": sum(by_status.values()),
        "open": ncs.open().count(),
        "overdue": ncs.overdue().count(),
        "pending_validation": by_status.get(S.PENDING_VALIDATION, 0),
        "disputed": by_status.get(S.DISPUTED, 0),
        "valid": by_status.get(S.VALID, 0),
        "in_progress": by_status.get(S.IN_PROGRESS, 0),
        "pending_verification": by_status.get(S.PENDING_VERIFICATION, 0),
        "closed": by_status.get(S.CLOSED, 0),
        "not_valid": by_status.get(S.NOT_VALID, 0),
    }


def count_by(ncs, field):
    """FR-34: [(name, count), ...] largest first. Not Valid NCs are left out."""
    rows = (ncs.exclude(status=S.NOT_VALID).values_list(f"{field}__name")
            .annotate(n=Count("pk")).order_by("-n", f"{field}__name"))
    return [(name, n) for name, n in rows]


def _months_back(today, count):
    """First day of each of the last `count` months, oldest first."""
    months = []
    year, month = today.year, today.month
    for _ in range(count):
        months.append(date(year, month, 1))
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return list(reversed(months))


def monthly_trend(ncs, months=12):
    """FR-35: NCs raised vs closed per month for the last `months` months."""
    month_starts = _months_back(timezone.localdate(), months)

    def per_month(field):
        rows = (ncs.filter(**{f"{field}__date__gte": month_starts[0]})
                .annotate(month=TruncMonth(field)).values_list("month").annotate(n=Count("pk")))
        return {timezone.localdate(m) if hasattr(m, "hour") else m: n for m, n in rows}

    raised, closed = per_month("logged_at"), per_month("closed_at")
    return {
        "labels": [m.strftime("%b %Y") for m in month_starts],
        "raised": [raised.get(m, 0) for m in month_starts],
        "closed": [closed.get(m, 0) for m in month_starts],
    }


def closure_stats(ncs):
    """FR-35: average days to close and how long closed NCs took (ageing)."""
    dates = ncs.filter(status=S.CLOSED, closed_at__isnull=False).values_list("logged_at", "closed_at")
    durations = [(timezone.localdate(closed) - timezone.localdate(logged)).days for logged, closed in dates]
    ageing = []
    for label, low, high in AGEING_BUCKETS:
        ageing.append((label, sum(1 for d in durations if d >= low and (high is None or d <= high))))
    average = round(sum(durations) / len(durations)) if durations else None
    return {"average_days": average, "ageing": ageing, "closed_count": len(durations)}


def build_dashboard(ncs):
    return {
        "counts": status_counts(ncs),
        "by_receiving": count_by(ncs, "receiving_department"),
        "by_raising": count_by(ncs, "raising_department"),
        "by_process": count_by(ncs, "process"),
        "by_source": count_by(ncs, "source"),
        "trend": monthly_trend(ncs),
        "closure": closure_stats(ncs),
    }
