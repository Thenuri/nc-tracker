from django.conf import settings

from accounts import permissions as perms


def prototype_mode(request):
    """Expose PROTOTYPE_MODE to every template so base.html can show the banner.

    Templates only ever see this flag; they never read .env themselves.
    """
    return {"PROTOTYPE_MODE": settings.PROTOTYPE_MODE}


def navigation(request):
    """Which navbar links to show. Uses the permission helpers, never raw roles."""
    user = getattr(request, "user", None)
    if not (user and user.is_authenticated):
        return {"nav": {}}
    return {
        "nav": {
            "can_log": perms.can_log_nc(user),
            "unread": user.notifications.filter(read_at__isnull=True).count(),
        }
    }
