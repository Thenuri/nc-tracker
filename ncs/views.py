"""NC screens: log an NC, the NC page, and the actions on it.

Views stay thin: they check the person may see the NC, collect a form, and
hand over to ncs/workflow.py. They never set `status` themselves.
"""

import os
from dataclasses import dataclass
from typing import Callable

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts import permissions as perms

from . import forms
from . import workflow as wf
from .models import NC, Evidence


@dataclass
class Panel:
    """One "What you can do" box on the NC page."""

    action: str             # name in workflow.ACTIONS
    form_class: type
    title: str
    button: str
    handler: Callable       # (nc, user, cleaned_data) -> calls the workflow
    success: str            # message shown afterwards
    style: str = "primary"  # Bootstrap button colour
    intro: str = ""
    # For boxes that can be filled in again (e.g. the action plan): once done,
    # the form is folded away behind an "Edit" button so people can see it was saved.
    saved: Callable | None = None   # (nc) -> short "already done" text, or "" if not done yet
    edit_button: str = ""           # opens the folded form
    update_button: str = ""         # submit button text when editing


# Shown in this order, and only those the person can do right now (UI-02).
PANELS = [
    Panel("validate", forms.ValidateForm, "Confirm this NC is valid", "Yes, it is valid",
          lambda nc, u, d: wf.validate(nc, u),
          "Marked as valid. Next: assign an Action Owner or record the action plan.",
          style="success", intro="Confirm the NC applies to your department."),
    Panel("dispute", forms.DisputeForm, "Not valid? Dispute it", "Mark as not valid",
          lambda nc, u, d: wf.dispute(nc, u, d["reason"]),
          "Marked as not valid. The NC Manager has been told and will decide.",
          style="outline-danger"),
    Panel("decide_dispute", forms.DecideDisputeForm, "Decide the dispute", "Record decision",
          lambda nc, u, d: wf.decide_dispute(nc, u, d["decision"] == "uphold", d["rationale"]),
          "Decision recorded and both departments told."),
    Panel("save_action_plan", forms.ActionPlanForm, "Action plan", "Save action plan",
          lambda nc, u, d: wf.save_action_plan(nc, u, d["root_cause"], d["corrective_action"],
                                               d["target_date"], action_owner=d.get("action_owner")),
          "Action plan saved.",
          saved=lambda nc: "Action plan saved." if nc.root_cause and nc.corrective_action and nc.target_date else "",
          edit_button="Edit action plan", update_button="Update action plan"),
    Panel("assign_action_owner", forms.AssignOwnerForm, "Assign Action Owner", "Assign",
          lambda nc, u, d: wf.assign_action_owner(nc, u, d["action_owner"]),
          "Action Owner assigned and notified.", style="outline-primary",
          intro="The Action Owner can then fill in the action plan.",
          saved=lambda nc: f"Assigned to {nc.action_owner}." if nc.action_owner_id else "",
          edit_button="Change Action Owner", update_button="Assign"),
    Panel("add_evidence", forms.EvidenceForm, "Add evidence", "Add evidence",
          lambda nc, u, d: wf.add_evidence(nc, u, d["description"], file=d.get("file"), link=d.get("link")),
          "Evidence added.", style="outline-primary"),
    Panel("submit_for_verification", forms.SubmitForVerificationForm, "Action completed?",
          "Send for verification",
          lambda nc, u, d: wf.submit_for_verification(nc, u, d["completion_date"]),
          "Sent to the NC Manager for verification.", style="success",
          intro="Add evidence first. The NC Manager will then check it."),
    Panel("verify", forms.VerifyForm, "Verify the corrective action", "Record verification",
          lambda nc, u, d: wf.verify(nc, u, d["outcome"] == "effective", d["comments"]),
          "Verification recorded."),
    Panel("change_target_date", forms.TargetDateForm, "Change target date", "Change date",
          lambda nc, u, d: wf.change_target_date(nc, u, d["new_date"], d["reason"]),
          "Target date changed. The original date is kept.", style="outline-secondary"),
    Panel("add_progress_note", forms.ProgressNoteForm, "Add a progress note", "Add note",
          lambda nc, u, d: wf.add_progress_note(nc, u, d["text"]),
          "Note added.", style="outline-secondary"),
    Panel("reopen", forms.ReopenForm, "Reopen this NC", "Reopen",
          lambda nc, u, d: wf.reopen(nc, u, d["reason"]),
          "NC reopened and the receiving department told.", style="outline-danger"),
]
PANELS_BY_ACTION = {panel.action: panel for panel in PANELS}


def get_visible_nc(request, nc_id):
    """The NC, or 404 if it doesn't exist, or 403 if this person may not see it."""
    nc = get_object_or_404(
        NC.objects.select_related(
            "raising_department__hod", "receiving_department__hod", "process", "source",
            "action_owner", "logged_by", "validated_by", "dispute_decided_by", "verified_by",
        ),
        nc_id=nc_id,
    )
    if not perms.can_view_nc(request.user, nc):
        raise PermissionDenied
    return nc


def render_detail(request, nc, bound_forms=None):
    """Draw the NC page. `bound_forms` holds a submitted form that had errors."""
    bound_forms = bound_forms or {}
    panels = []
    for panel in PANELS:
        if wf.can(panel.action, nc, request.user):
            form = bound_forms.get(panel.action) or panel.form_class(nc=nc, user=request.user)
            # Keep the form open if it was just submitted with errors.
            saved_text = panel.saved(nc) if panel.saved and panel.action not in bound_forms else ""
            panels.append((panel, form, saved_text))

    context = {
        "nc": nc,
        "panels": panels,
        "evidence": nc.evidence.select_related("uploaded_by"),
        "notes": nc.progress_notes.select_related("author"),
        "date_changes": nc.target_date_changes.select_related("changed_by"),
        "history": nc.history.select_related("history_user").order_by("-history_date"),
    }
    return render(request, "ncs/nc_detail.html", context, status=400 if bound_forms else 200)


@login_required
def nc_detail(request, nc_id):
    return render_detail(request, get_visible_nc(request, nc_id))


@login_required
def nc_print(request, nc_id):
    """Printable record from logging to closure, for auditors (FR-37)."""
    nc = get_visible_nc(request, nc_id)
    context = {
        "nc": nc,
        "evidence": nc.evidence.select_related("uploaded_by"),
        "notes": nc.progress_notes.select_related("author"),
        "date_changes": nc.target_date_changes.select_related("changed_by"),
        "history": nc.history.select_related("history_user").order_by("history_date"),
        "printed_at": timezone.now(),
    }
    return render(request, "ncs/nc_print.html", context)


@login_required
@require_POST
def nc_action(request, nc_id, action):
    panel = PANELS_BY_ACTION.get(action)
    if panel is None:
        raise Http404
    nc = get_visible_nc(request, nc_id)

    statuses, permission = wf.ACTIONS[action]
    if not permission(request.user, nc):
        raise PermissionDenied
    if nc.status not in statuses:
        # e.g. someone else acted first in another tab
        messages.warning(request, f"That is no longer possible: the NC is now '{nc.get_status_display()}'.")
        return redirect(nc)

    form = panel.form_class(request.POST, request.FILES, nc=nc, user=request.user)
    if form.is_valid():
        try:
            panel.handler(nc, request.user, form.cleaned_data)
        except wf.WorkflowError as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, panel.success)
            return redirect(nc)

    nc.refresh_from_db()  # undo any half-applied changes on the in-memory object
    return render_detail(request, nc, {action: form})


@login_required
def log_nc(request):
    """NC Manager's single entry form for Part A (FR-01, FR-02, UI-01)."""
    if not perms.can_log_nc(request.user):
        raise PermissionDenied
    form = forms.NCLogForm(request.POST or None, request.FILES or None,
                           initial={"date_identified": timezone.localdate()})
    if request.method == "POST" and form.is_valid():
        try:
            nc = wf.log_nc(request.user, form.save(commit=False))
        except wf.WorkflowError as error:
            form.add_error(None, str(error))
        else:
            messages.success(request, f"{nc.nc_id} logged. The receiving HoD has been notified.")
            return redirect(nc)
    return render(request, "ncs/nc_log.html", {"form": form})


# --- Files: only served to people allowed to see the NC -------------------------

def _file_response(field):
    if not field:
        raise Http404
    return FileResponse(field.open("rb"), as_attachment=True, filename=os.path.basename(field.name))


@login_required
def download_attachment(request, nc_id):
    return _file_response(get_visible_nc(request, nc_id).attachment)


@login_required
def download_evidence(request, pk):
    evidence = get_object_or_404(Evidence.objects.select_related("nc"), pk=pk)
    if not perms.can_view_nc(request.user, evidence.nc):
        raise PermissionDenied
    return _file_response(evidence.file)
