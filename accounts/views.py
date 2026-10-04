"""PROTOTYPE STAND-IN: "Who am I?" role switcher.

Logs you in as any sample user with one click, so the workflow can be
demonstrated without passwords. It uses Django's normal login(), so the rest
of the app just sees `request.user` – exactly what Microsoft Entra ID login
will provide later. Delete this file (and its URL) when real login arrives.
"""

from django.conf import settings
from django.contrib.auth import login
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import User


def switchable_users():
    """Sample users the switcher offers. Superusers are never offered."""
    return (
        User.objects.filter(is_active=True, is_superuser=False)
        .select_related("department")
        .order_by("role", "department__name", "first_name")
    )


@require_POST
def switch_user(request):
    if not settings.PROTOTYPE_MODE:
        raise Http404  # the switcher does not exist outside prototype mode

    user = get_object_or_404(switchable_users(), pk=request.POST.get("user_id"))
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")

    # Return to the page the person was on, if it is on this site.
    next_url = request.POST.get("next", "/")
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = "/"
    return redirect(next_url)
