from django.conf import settings

from .views import switchable_users


def role_switcher(request):
    """Give base.html the list of users for the "Who am I?" switcher.

    Empty outside prototype mode, so the switcher simply doesn't render.
    """
    if not settings.PROTOTYPE_MODE:
        return {}
    return {"switcher_users": switchable_users()}
