"""Who may do what – the single place role rules live (SRS Section 6).

Always call these with `request.user`. They never look at the prototype role
switcher, so when Microsoft login replaces it nothing here changes.

These answer "is this person the right ROLE for this action on this NC?".
Whether the NC is in the right STATUS for the action is checked separately
by ncs/workflow.py (Phase 4).
"""

from core.models import Department


def _active(user):
    return user is not None and user.is_authenticated and user.is_active


# --- Who is this person? ------------------------------------------------------

def is_nc_manager(user):
    """NC Manager or delegate – identical rights (NFR-08)."""
    return _active(user) and user.role == user.Role.NC_MANAGER


def is_management(user):
    return _active(user) and user.role == user.Role.MANAGEMENT


def is_hod(user):
    """Head of ANY department. Department.hod is the source of truth."""
    return _active(user) and Department.objects.filter(hod=user).exists()


def is_receiving_hod(user, nc):
    """Head of the department this NC is raised against."""
    return _active(user) and nc.receiving_department.hod_id == user.pk


def is_action_owner(user, nc):
    return _active(user) and nc.action_owner_id == user.pk


# --- Viewing --------------------------------------------------------------------

def can_view_all_ncs(user):
    """Whole register: NC Manager, Management (FR-31) and every HoD (FR-30)."""
    return is_nc_manager(user) or is_management(user) or is_hod(user)


def can_view_nc(user, nc):
    if can_view_all_ncs(user) or is_action_owner(user, nc):
        return True
    # Other staff see their own department's NCs, whether their department
    # received the NC or raised it (raising dept may view, not change).
    return _active(user) and user.department_id in (
        nc.receiving_department_id,
        nc.raising_department_id,
    )


# --- Acting on an NC ----------------------------------------------------------------

def can_log_nc(user):
    """FR-01: only the NC Manager (and delegate) can create NCs."""
    return is_nc_manager(user)


def can_validate(user, nc):
    """FR-09, FR-13: only the receiving HoD validates or disputes."""
    return is_receiving_hod(user, nc)


def can_assign_action_owner(user, nc):
    """FR-16: the receiving HoD picks the Action Owner."""
    return is_receiving_hod(user, nc)


def can_edit_action_plan(user, nc):
    """FR-17, FR-18, FR-40: root cause, action, dates, evidence, notes.

    Receiving HoD or the assigned Action Owner. The raising department and
    other HoDs can look but not change.
    """
    return is_receiving_hod(user, nc) or is_action_owner(user, nc)


def can_decide_dispute(user, nc):
    """FR-12."""
    return is_nc_manager(user)


def can_verify(user, nc):
    """FR-21: verify and close."""
    return is_nc_manager(user)


def can_reopen(user, nc):
    """FR-24."""
    return is_nc_manager(user)
