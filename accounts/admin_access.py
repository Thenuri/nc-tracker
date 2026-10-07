"""Admin access for the NC Manager, who maintains the lists (FR-41, NFR-09).

Anyone with the NC Manager role (including the delegate, NFR-08) is put in the
"NC Manager" group, which may edit departments, processes, sources and
public holidays, and view NC records in the admin. Nothing else: NCs still
change only through ncs/workflow.py.

This used to be set up by load_sample_data only, so real NC Managers had no
admin access. Now the group is created on every `migrate`, and membership
follows the user's role automatically (see User.save).
"""

from django.contrib.auth.models import Group, Permission

GROUP_NAME = "NC Manager"

PERMISSIONS = [
    f"{action}_{model}"
    for model in ("department", "process", "source")
    for action in ("add", "change", "view")
] + [f"{action}_publicholiday" for action in ("add", "change", "view", "delete")] + [
    "view_nc", "view_evidence", "view_progressnote", "view_targetdatechange", "view_notification",
]


def ensure_nc_manager_group(**kwargs):
    """Create the group and give it its permissions. Safe to run any number of times.

    Connected to post_migrate, which runs once per app; permissions for later
    apps only exist after their turn, so each run sets whatever exists so far.
    """
    group, _ = Group.objects.get_or_create(name=GROUP_NAME)
    group.permissions.set(Permission.objects.filter(codename__in=PERMISSIONS))
    return group


def sync_nc_manager_access(user):
    """Put NC Managers in the group, and take anyone else out of it."""
    group, _ = Group.objects.get_or_create(name=GROUP_NAME)
    if user.role == user.Role.NC_MANAGER:
        user.groups.add(group)
    else:
        user.groups.remove(group)
