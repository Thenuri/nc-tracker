from django.shortcuts import render

from accounts import permissions as perms
from ncs.queries import my_tasks


def home(request):
    """Start page: who you are and the NCs waiting for you."""
    context = {}
    if request.user.is_authenticated:
        context = {
            "headed_departments": list(request.user.headed_departments.all()),
            "nominated_departments": list(request.user.nominated_departments.all()),
            "tasks": my_tasks(request.user),
            "can_log": perms.can_log_nc(request.user),
        }
    return render(request, "core/home.html", context)
