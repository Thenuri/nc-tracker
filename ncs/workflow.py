"""THE ONLY place an NC's status changes (SRS Section 3).

Every action here does the same three checks, in this order:
  1. Is this person allowed?         -> raises PermissionDenied   (views: 403)
  2. Is the NC in the right status?  -> raises WorkflowError      (views: show message)
  3. Are the required fields filled? -> raises WorkflowError
Only then does it save the change, record who did it in the history, and
send notifications through notify().

Views must call these functions and never set `nc.status` themselves.
"""

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from accounts import permissions as perms
from accounts.models import User
from notifications.services import notify

from .dates import add_working_days
from .models import NC, Evidence, ProgressNote, TargetDateChange

S = NC.Status


class WorkflowError(Exception):
    """The action isn't possible right now (wrong status or missing information).

    The message is written for the person using the app, so views can show it.
    """


# Every status change the system allows: from -> {to, ...}
# Anything not listed here is blocked, whoever asks.
ALLOWED_TRANSITIONS = {
    S.PENDING_VALIDATION: {S.VALID, S.DISPUTED},
    S.DISPUTED: {S.VALID, S.NOT_VALID},
    S.VALID: {S.IN_PROGRESS},
    S.IN_PROGRESS: {S.PENDING_VERIFICATION},
    S.PENDING_VERIFICATION: {S.CLOSED, S.IN_PROGRESS},
    S.CLOSED: {S.IN_PROGRESS},  # reopen (FR-24)
    S.NOT_VALID: set(),         # final; record stays in the register (FR-15)
}

# Each action on an existing NC: (statuses it is allowed in, who may do it).
# Closed and Not Valid NCs are missing from almost every row, which is what
# keeps them locked; only "reopen" works on a Closed NC.
ACTIONS = {
    "validate": ({S.PENDING_VALIDATION}, perms.can_validate),
    "dispute": ({S.PENDING_VALIDATION}, perms.can_validate),
    "decide_dispute": ({S.DISPUTED}, perms.can_decide_dispute),
    "assign_action_owner": ({S.VALID, S.IN_PROGRESS}, perms.can_assign_action_owner),
    "save_action_plan": ({S.VALID, S.IN_PROGRESS}, perms.can_edit_action_plan),
    "change_target_date": ({S.IN_PROGRESS}, perms.can_edit_action_plan),
    "add_progress_note": ({S.VALID, S.IN_PROGRESS, S.PENDING_VERIFICATION}, perms.can_edit_action_plan),
    "add_evidence": ({S.IN_PROGRESS}, perms.can_edit_action_plan),
    "submit_for_verification": ({S.IN_PROGRESS}, perms.can_edit_action_plan),
    "verify": ({S.PENDING_VERIFICATION}, perms.can_verify),
    "reopen": ({S.CLOSED}, perms.can_reopen),
}


# --- Checking ---------------------------------------------------------------------

def can(action, nc, user):
    """True if `user` may do `action` on `nc` right now. Used to show/hide buttons."""
    statuses, permission = ACTIONS[action]
    return nc.status in statuses and permission(user, nc)


def available_actions(nc, user):
    """All actions `user` can take on `nc` right now (UI: show only these)."""
    return {action for action in ACTIONS if can(action, nc, user)}


def _check(action, nc, user):
    statuses, permission = ACTIONS[action]
    if not permission(user, nc):
        raise PermissionDenied("You are not allowed to do this on this NC.")
    if nc.status not in statuses:
        raise WorkflowError(f"This can't be done while the NC is '{nc.get_status_display()}'.")


def _require(value, message):
    """Required-field check. Blank text counts as missing."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise WorkflowError(message)


def _not_in_future(day, label):
    if day > timezone.localdate():
        raise WorkflowError(f"{label} cannot be in the future.")


def _move(nc, to_status):
    """Change status, but only along a transition listed in ALLOWED_TRANSITIONS."""
    if to_status not in ALLOWED_TRANSITIONS[nc.status]:
        raise WorkflowError(
            f"An NC can't go from '{nc.get_status_display()}' to '{S(to_status).label}'."
        )
    nc.status = to_status


def _save(nc, user, reason):
    """Save with the history showing who did it and why (FR-42)."""
    nc._history_user = user
    nc._change_reason = reason
    nc.save()


# --- Who gets told ----------------------------------------------------------------

def _nc_managers():
    return User.objects.filter(role=User.Role.NC_MANAGER, is_active=True)


def _notify_nc_managers(subject, message, nc):
    for manager in _nc_managers():
        notify(manager, subject, message, nc)


def _notify_receiving_side(subject, message, nc):
    """Receiving HoD plus the Action Owner (if different)."""
    hod = nc.receiving_department.hod
    notify(hod, subject, message, nc)
    if nc.action_owner and nc.action_owner != hod:
        notify(nc.action_owner, subject, message, nc)


# --- Logging (NC Manager) -------------------------------------------------------

@transaction.atomic
def log_nc(user, nc):
    """Save a new NC built from the Part A form (FR-01 – FR-08).

    `nc` is an unsaved NC with the Part A fields filled in.
    """
    if not perms.can_log_nc(user):
        raise PermissionDenied("Only the NC Manager can log NCs.")
    if nc.pk:
        raise WorkflowError("This NC has already been logged.")

    nc.logged_by = user
    try:
        # Required fields, valid dates, dropdown values (FR-05). The ID fields
        # are skipped because save() fills them in.
        nc.full_clean(exclude=["nc_id", "year", "sequence"])
    except ValidationError as error:
        raise WorkflowError("; ".join(error.messages)) from error
    if nc.process.name.lower() == "other":
        _require(nc.process_other, 'Please describe the area / process when "Other" is chosen.')
    if nc.source.name.lower() == "other":
        _require(nc.source_other, 'Please describe the source when "Other" is chosen.')

    today = timezone.localdate()
    nc.validation_deadline = add_working_days(today, settings.NC_VALIDATION_WORKING_DAYS)
    same_department = nc.raising_department_id == nc.receiving_department_id

    if same_department and not settings.NC_SAME_DEPARTMENT_NEEDS_VALIDATION:
        # [TBC] option: same-department NCs skip validation.
        nc.status = S.VALID
        nc.validated_by = user
        nc.validated_at = timezone.now()
        nc.validation_deadline = None
        _save(nc, user, "Logged (same department, validation not required)")
    else:
        nc.status = S.PENDING_VALIDATION
        _save(nc, user, "Logged")

    if nc.status == S.PENDING_VALIDATION:
        next_step = f"Please confirm whether it is valid by {nc.validation_deadline:%d %b %Y}."
    else:
        next_step = "Please record the root cause and corrective action."
    receiving_hod = nc.receiving_department.hod
    notify(
        receiving_hod,
        f"{nc.nc_id}: new NC for {nc.receiving_department}",
        f"An NC has been logged against {nc.receiving_department}.\n\n{nc.description}\n\n{next_step}",
        nc,
    )  # FR-08
    raising_hod = nc.raising_department.hod
    if raising_hod and raising_hod != receiving_hod:
        notify(
            raising_hod,
            f"{nc.nc_id}: your NC has been logged",
            f"The NC your department reported against {nc.receiving_department} "
            f"has been logged as {nc.nc_id}.",
            nc,
        )  # FR-07
    return nc


# --- Validation (receiving HoD) ---------------------------------------------------

@transaction.atomic
def validate(nc, user):
    """Receiving HoD confirms the NC is valid (FR-09)."""
    _check("validate", nc, user)
    _move(nc, S.VALID)
    nc.validated_by = user
    nc.validated_at = timezone.now()
    _save(nc, user, "Validated")
    return nc


@transaction.atomic
def dispute(nc, user, reason):
    """Receiving HoD says the NC is not valid (FR-10, FR-11)."""
    _check("dispute", nc, user)
    _require(reason, "Please give a reason why the NC is not valid.")
    _move(nc, S.DISPUTED)
    nc.validated_by = user
    nc.validated_at = timezone.now()
    nc.dispute_reason = reason.strip()
    _save(nc, user, "Disputed")
    _notify_nc_managers(
        f"{nc.nc_id}: disputed by {nc.receiving_department}",
        f"{user} says this NC is not valid.\n\nReason: {nc.dispute_reason}\n\nPlease decide.",
        nc,
    )
    return nc


@transaction.atomic
def decide_dispute(nc, user, uphold, rationale):
    """NC Manager decides a dispute (FR-12).

    uphold=True  -> the dispute stands, NC becomes Not Valid
    uphold=False -> the dispute is overturned, NC becomes Valid
    """
    _check("decide_dispute", nc, user)
    _require(rationale, "Please give the rationale for your decision.")
    _move(nc, S.NOT_VALID if uphold else S.VALID)
    nc.dispute_decided_by = user
    nc.dispute_decided_at = timezone.now()
    nc.dispute_rationale = rationale.strip()
    _save(nc, user, "Dispute upheld" if uphold else "Dispute overturned")

    outcome = ("upheld – the NC is recorded as Not Valid" if uphold
               else "overturned – the NC is valid and needs an action plan")
    message = f"The dispute on {nc.nc_id} was {outcome}.\n\nRationale: {nc.dispute_rationale}"
    notify(nc.receiving_department.hod, f"{nc.nc_id}: dispute decided", message, nc)
    if nc.raising_department.hod != nc.receiving_department.hod:
        notify(nc.raising_department.hod, f"{nc.nc_id}: dispute decided", message, nc)
    return nc


# --- Action planning (receiving HoD / Action Owner) ------------------------------

@transaction.atomic
def assign_action_owner(nc, user, owner):
    """Receiving HoD picks the person responsible (FR-16)."""
    _check("assign_action_owner", nc, user)
    _require(owner, "Please choose an Action Owner.")
    if not owner.is_active or owner.department_id != nc.receiving_department_id:
        raise WorkflowError(f"The Action Owner must be an active member of {nc.receiving_department}.")
    if nc.action_owner_id == owner.pk:
        return nc  # no change, no duplicate notification

    nc.action_owner = owner
    _save(nc, user, f"Action Owner set to {owner}")
    notify(
        owner,
        f"{nc.nc_id}: you are the Action Owner",
        f"{user} has made you responsible for the corrective action on {nc.nc_id}.\n\n{nc.description}",
        nc,
    )
    return nc


@transaction.atomic
def save_action_plan(nc, user, root_cause, corrective_action, target_date, action_owner=None):
    """Record the 4 action-planning fields (FR-17, NFR-02).

    From Valid, a complete plan moves the NC to In Progress. While In Progress
    the root cause and action text can be updated; the target date can only
    change through change_target_date() so the reason is recorded (FR-20).
    """
    _check("save_action_plan", nc, user)

    # Check everything first, so a rejected plan changes nothing.
    _require(root_cause, "Please enter the root cause.")
    _require(corrective_action, "Please enter the corrective action.")
    _require(action_owner or nc.action_owner, "Please choose an Action Owner.")
    _require(target_date, "Please enter a target completion date.")
    if nc.status == S.IN_PROGRESS and target_date != nc.target_date:
        raise WorkflowError("To change the target date, use 'Change target date' and give a reason.")
    if nc.status == S.VALID and target_date < timezone.localdate():
        raise WorkflowError("The target date cannot be in the past.")

    if action_owner is not None:
        assign_action_owner(nc, user, action_owner)  # has its own checks

    if nc.status == S.IN_PROGRESS:
        nc.root_cause = root_cause.strip()
        nc.corrective_action = corrective_action.strip()
        _save(nc, user, "Action plan updated")
        return nc

    _move(nc, S.IN_PROGRESS)
    nc.root_cause = root_cause.strip()
    nc.corrective_action = corrective_action.strip()
    nc.target_date = target_date
    nc.original_target_date = target_date  # kept even if changed later (FR-20)
    _save(nc, user, "Action plan recorded")
    return nc


@transaction.atomic
def change_target_date(nc, user, new_date, reason):
    """Move the target date, keeping the original and the reason (FR-20)."""
    _check("change_target_date", nc, user)
    _require(new_date, "Please enter the new target date.")
    _require(reason, "Please give a reason for changing the target date.")
    if new_date < timezone.localdate():
        raise WorkflowError("The new target date cannot be in the past.")
    if new_date == nc.target_date:
        raise WorkflowError("The new target date is the same as the current one.")

    TargetDateChange.objects.create(
        nc=nc, old_date=nc.target_date, new_date=new_date, reason=reason.strip(), changed_by=user
    )
    nc.target_date = new_date
    _save(nc, user, "Target date changed")
    return nc


@transaction.atomic
def add_progress_note(nc, user, text):
    """Free-text update on the NC (FR-18)."""
    _check("add_progress_note", nc, user)
    _require(text, "Please enter the note.")
    return ProgressNote.objects.create(nc=nc, author=user, text=text.strip())


@transaction.atomic
def add_evidence(nc, user, description, file=None, link=""):
    """Attach evidence of completion: a file, a link, or both (D3)."""
    _check("add_evidence", nc, user)
    evidence = Evidence(nc=nc, uploaded_by=user, description=description or "", file=file, link=link or "")
    try:
        evidence.full_clean()
    except ValidationError as error:
        raise WorkflowError("; ".join(error.messages)) from error
    evidence.save()
    return evidence


@transaction.atomic
def submit_for_verification(nc, user, completion_date):
    """Action finished; ask the NC Manager to verify (FR-19)."""
    _check("submit_for_verification", nc, user)
    _require(completion_date, "Please enter the date the action was completed.")
    _not_in_future(completion_date, "The completion date")
    if not nc.evidence.exists():
        raise WorkflowError("Please add evidence of completion before sending for verification.")

    _move(nc, S.PENDING_VERIFICATION)
    nc.completion_date = completion_date
    _save(nc, user, "Sent for verification")
    _notify_nc_managers(
        f"{nc.nc_id}: ready for verification",
        f"{nc.receiving_department} has completed the corrective action on {nc.nc_id}. "
        "Please check the evidence and verify.",
        nc,
    )
    return nc


# --- Verification and closure (NC Manager) -----------------------------------------

@transaction.atomic
def verify(nc, user, effective, comments=""):
    """NC Manager checks the action (FR-21 – FR-23).

    effective=True  -> Closed (and locked)
    effective=False -> back to In Progress; comments are required and shown to the owner
    """
    _check("verify", nc, user)
    if not effective:
        _require(comments, "Please explain why the action is not effective.")

    nc.verification_outcome = NC.Outcome.EFFECTIVE if effective else NC.Outcome.NOT_EFFECTIVE
    nc.verification_comments = (comments or "").strip()
    nc.verified_by = user
    nc.verified_at = timezone.now()

    if effective:
        _move(nc, S.CLOSED)
        nc.closed_at = nc.verified_at
        _save(nc, user, "Verified effective and closed")
        _notify_receiving_side(
            f"{nc.nc_id}: closed",
            f"{nc.nc_id} has been verified as effective and is now closed. Thank you.",
            nc,
        )
    else:
        _move(nc, S.IN_PROGRESS)
        _save(nc, user, "Verified not effective – returned for rework")
        _notify_receiving_side(
            f"{nc.nc_id}: more work needed",
            f"The corrective action on {nc.nc_id} was not effective.\n\n"
            f"Comments: {nc.verification_comments}",
            nc,
        )
    return nc


@transaction.atomic
def reopen(nc, user, reason):
    """NC Manager reopens a closed NC (FR-24). The reason goes in the history."""
    _check("reopen", nc, user)
    _require(reason, "Please give a reason for reopening.")
    _move(nc, S.IN_PROGRESS)
    nc.closed_at = None
    _save(nc, user, f"Reopened: {reason.strip()}")
    ProgressNote.objects.create(nc=nc, author=user, text=f"Reopened by NC Manager: {reason.strip()}")
    _notify_receiving_side(
        f"{nc.nc_id}: reopened",
        f"{nc.nc_id} has been reopened.\n\nReason: {reason.strip()}",
        nc,
    )
    return nc
