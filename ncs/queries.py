"""Reusable NC lists for screens: what a person may see, and what needs them.

`visible_ncs` must give the same answer as accounts.permissions.can_view_nc,
just as a database query (tests check they agree).
"""

from django.db.models import Q

from accounts import permissions as perms

from .models import NC

S = NC.Status


def with_related(queryset):
    """Load the linked records the list screens show, in one query."""
    return queryset.select_related(
        "raising_department", "receiving_department", "process", "source", "action_owner"
    )


def visible_ncs(user):
    """Every NC `user` may view (SRS Section 6, FR-30, FR-31)."""
    if perms.can_view_all_ncs(user):
        return with_related(NC.objects.all())
    if not (user and user.is_authenticated):
        return NC.objects.none()
    rule = Q(action_owner=user)
    if user.department_id:
        rule |= Q(receiving_department=user.department_id) | Q(raising_department=user.department_id)
    return with_related(NC.objects.filter(rule))


def my_tasks(user):
    """NCs waiting for THIS person to do something, oldest first."""
    if not (user and user.is_authenticated):
        return NC.objects.none()
    rule = Q(pk__in=[])  # matches nothing; parts are added below
    if perms.is_nc_manager(user):
        rule |= Q(status__in=[S.DISPUTED, S.PENDING_VERIFICATION])
    # Departments this person heads, or acts for as the HoD's nominee (FR-09)
    headed = list(user.headed_departments.values_list("pk", flat=True))
    headed += user.nominated_departments.values_list("pk", flat=True)
    if headed:
        rule |= Q(receiving_department__in=headed, status__in=[S.PENDING_VALIDATION, S.VALID])
    rule |= Q(action_owner=user, status=S.IN_PROGRESS)
    return with_related(NC.objects.filter(rule)).order_by("logged_at")
