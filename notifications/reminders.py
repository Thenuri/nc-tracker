"""Automatic reminders and escalations (FR-14, FR-26, FR-27, FR-28).

Run once a day by `python manage.py send_reminders`. Each reminder is sent
once per NC and deadline (tracked in ReminderLog). If a target date is moved,
the reminders start again for the new date.
"""

from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.models import User
from ncs.models import NC

from .models import ReminderLog
from .services import notify

S = NC.Status


def _once(key):
    """True the first time a key is seen, False afterwards."""
    try:
        with transaction.atomic():
            ReminderLog.objects.create(key=key)
        return True
    except IntegrityError:
        return False


def _managers():
    return list(User.objects.filter(role=User.Role.NC_MANAGER, is_active=True))


def _send(recipients, subject, message, nc=None):
    sent = 0
    for person in {p for p in recipients if p is not None}:
        notify(person, subject, message, nc)
        sent += 1
    return sent


def validation_reminders(today):
    """FR-14: remind the receiving HoD on the last day; alert the NC Manager if missed."""
    sent = 0
    for nc in NC.objects.filter(status=S.PENDING_VALIDATION, validation_deadline__isnull=False) \
            .select_related("receiving_department__hod", "receiving_department__nominee"):
        heads = nc.receiving_department.heads  # HoD and nominee (FR-09)
        if nc.validation_deadline == today and _once(f"{nc.pk}:validation_due:{nc.validation_deadline}"):
            sent += _send(heads, f"{nc.nc_id}: please validate today",
                          f"Please confirm today whether {nc.nc_id} is valid.\n\n{nc.description}", nc)
        if nc.validation_deadline < today and _once(f"{nc.pk}:validation_missed:{nc.validation_deadline}"):
            sent += _send(heads + _managers(), f"{nc.nc_id}: validation deadline missed",
                          f"{nc.nc_id} was due for validation by {nc.receiving_department} on "
                          f"{nc.validation_deadline:%d %b %Y} and has not been validated.", nc)
    return sent


def target_reminders(today):
    """FR-26, FR-27: before the target date, when overdue, and escalation."""
    sent = 0
    soon = today + timedelta(days=settings.NC_REMINDER_DAYS_BEFORE_TARGET)
    escalate_after = settings.NC_ESCALATION_DAYS_OVERDUE

    for nc in NC.objects.filter(status__in=NC.ACTION_STATUSES, target_date__isnull=False) \
            .select_related("receiving_department__hod", "receiving_department__nominee", "action_owner"):
        target = nc.target_date
        hod = nc.receiving_department.hod
        heads = nc.receiving_department.heads
        owner = nc.action_owner or hod  # no owner yet: the HoD is responsible

        if today <= target <= soon and _once(f"{nc.pk}:target_soon:{target}"):
            sent += _send([owner], f"{nc.nc_id}: target date {target:%d %b %Y}",
                          f"Reminder: the corrective action for {nc.nc_id} is due on {target:%d %b %Y}.", nc)

        days_over = (today - target).days
        if days_over >= 1 and _once(f"{nc.pk}:overdue:{target}"):
            sent += _send(heads + [owner], f"{nc.nc_id}: overdue",
                          f"{nc.nc_id} passed its target date ({target:%d %b %Y}). "
                          "Please complete it or change the target date with a reason.", nc)

        if days_over >= escalate_after and _once(f"{nc.pk}:escalated:{target}"):
            sent += _send(_managers(), f"{nc.nc_id}: {days_over} days overdue",
                          f"{nc.nc_id} ({nc.receiving_department}) is {days_over} days past its "
                          f"target date of {target:%d %b %Y}.", nc)
    return sent


def weekly_digest(today, force=False):
    """FR-28: Monday summary of open and overdue NCs for the NC Manager."""
    year, week, weekday = today.isocalendar()
    if not (force or weekday == 1) or not _once(f"digest:{year}-W{week:02d}"):
        return 0
    open_ncs = NC.objects.open()
    overdue = list(open_ncs.overdue().select_related("receiving_department").order_by("target_date"))
    lines = [f"Open NCs: {open_ncs.count()}",
             f"Pending validation: {open_ncs.filter(status=S.PENDING_VALIDATION).count()}",
             f"Disputed: {open_ncs.filter(status=S.DISPUTED).count()}",
             f"Pending verification: {open_ncs.filter(status=S.PENDING_VERIFICATION).count()}",
             f"Overdue: {len(overdue)}", ""]
    lines += [f"- {nc.nc_id} ({nc.receiving_department}), {nc.days_overdue} days overdue" for nc in overdue]
    lines.append(f"\nRegister: {settings.SITE_URL}/register/?status=open")
    return _send(_managers(), f"Weekly NC digest – week {week}", "\n".join(lines))


def run_all(today=None, force_digest=False):
    today = today or timezone.localdate()
    return {
        "validation": validation_reminders(today),
        "target": target_reminders(today),
        "digest": weekly_digest(today, force=force_digest),
    }
