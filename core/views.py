from django.conf import settings
from django.shortcuts import render

from accounts.models import User
from ncs.models import NC
from ncs.queries import my_tasks


def home(request):
    """Start page: who you are and the NCs waiting for you."""
    context = {}
    if request.user.is_authenticated:
        context = {
            "headed_departments": list(request.user.headed_departments.all()),
            "nominated_departments": list(request.user.nominated_departments.all()),
            "tasks": my_tasks(request.user),
        }
    return render(request, "core/home.html", context)


def help_page(request):
    """One-page guide for HoDs and Action Owners, and how to report an NC (UI-06).

    Open to everyone, signed in or not: departments read it before they ever
    use the app. The numbers come from settings, so the guide always matches
    the rules the app actually applies.
    """
    context = {
        "validation_days": settings.NC_VALIDATION_WORKING_DAYS,
        "reminder_days": settings.NC_REMINDER_DAYS_BEFORE_TARGET,
        "escalation_days": settings.NC_ESCALATION_DAYS_OVERDUE,
        "due_soon_days": NC.DUE_SOON_DAYS,
        "nc_managers": User.objects.filter(role=User.Role.NC_MANAGER, is_active=True)
                                   .order_by("is_delegate", "first_name"),
    }
    return render(request, "core/help.html", context)
