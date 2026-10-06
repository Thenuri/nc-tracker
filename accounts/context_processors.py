from django.conf import settings
from django.db.models import Exists, OuterRef

from core.models import Department

from .views import switchable_users

# Order of the groups in the "Who am I?" list
GROUP_ORDER = ["NC Manager", "Head of Department", "HoD nominee", "Action Owner", "Management", "Staff"]


def role_switcher(request):
    """Give base.html the list of users for the "Who am I?" switcher.

    Empty outside prototype mode, so the switcher simply doesn't render.
    """
    if not settings.PROTOTYPE_MODE:
        return {}
    # is_nominee lets User.role_label skip one database query per person.
    users = switchable_users().annotate(is_nominee=Exists(Department.objects.filter(nominee=OuterRef("pk"))))
    # Sorted by on-screen group so {% regroup %} keeps each group together.
    users = sorted(users, key=lambda u: GROUP_ORDER.index(u.role_label) if u.role_label in GROUP_ORDER else 99)
    return {"switcher_users": users}
