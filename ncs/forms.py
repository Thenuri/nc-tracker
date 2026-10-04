"""Forms for the NC screens.

Forms only collect and tidy input. The rules (who, when, what is required for
a status change) are enforced again in ncs/workflow.py, which is the final say.
"""

from django import forms

from accounts.models import User
from accounts.permissions import can_assign_action_owner
from core.forms import BootstrapFormMixin, DateInput
from core.models import Department, Process, Source

from .models import NC

MAX_UPLOAD_MB = 10


def _check_file_size(upload):
    if upload and upload.size > MAX_UPLOAD_MB * 1024 * 1024:
        raise forms.ValidationError(f"Files must be {MAX_UPLOAD_MB} MB or smaller.")
    return upload


# --- Part A: logging (NC Manager) ---------------------------------------------------

class NCLogForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = NC
        fields = [
            "raising_department", "receiving_department", "process", "process_other",
            "description", "date_identified", "source", "source_other", "identified_by",
            "severity", "attachment",
        ]
        widgets = {
            "date_identified": DateInput(),
            "description": forms.Textarea(attrs={"rows": 4}),
        }
        labels = {
            "raising_department": "Raising department (who found it)",
            "receiving_department": "Receiving department (who must fix it)",
            "identified_by": "Identified by (person)",
            "severity": "Severity (optional)",
            "attachment": "Supporting attachment (optional)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only offer list items the NC Manager has kept active (FR-41).
        self.fields["raising_department"].queryset = Department.objects.filter(is_active=True)
        self.fields["receiving_department"].queryset = Department.objects.filter(is_active=True)
        self.fields["process"].queryset = Process.objects.filter(is_active=True)
        self.fields["source"].queryset = Source.objects.filter(is_active=True)

    def clean_attachment(self):
        return _check_file_size(self.cleaned_data.get("attachment"))

    def clean(self):
        data = super().clean()
        # "Other" needs a short description so the register stays meaningful.
        for choice, detail in (("process", "process_other"), ("source", "source_other")):
            item = data.get(choice)
            if item and item.name.lower() == "other" and not (data.get(detail) or "").strip():
                self.add_error(detail, 'Please describe it, because "Other" was chosen.')
        return data


# --- Action forms on the NC page -------------------------------------------------------

class NCActionForm(BootstrapFormMixin, forms.Form):
    """Base for action forms: knows which NC and which person it is for."""

    def __init__(self, *args, nc, user, **kwargs):
        self.nc = nc
        self.user = user
        super().__init__(*args, **kwargs)


class ValidateForm(NCActionForm):
    """No fields: one click confirms the NC is valid."""


class DisputeForm(NCActionForm):
    reason = forms.CharField(
        label="Why is this NC not valid?", widget=forms.Textarea(attrs={"rows": 3})
    )


class DecideDisputeForm(NCActionForm):
    decision = forms.ChoiceField(
        label="Decision",
        choices=[
            ("overturn", "Overturn – the NC is valid and must be actioned"),
            ("uphold", "Uphold – the NC is not valid"),
        ],
        widget=forms.RadioSelect,
    )
    rationale = forms.CharField(label="Rationale", widget=forms.Textarea(attrs={"rows": 3}))


def _department_members(nc):
    return User.objects.filter(is_active=True, department=nc.receiving_department).order_by("first_name")


class AssignOwnerForm(NCActionForm):
    action_owner = forms.ModelChoiceField(label="Action Owner", queryset=User.objects.none())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["action_owner"].queryset = _department_members(self.nc)
        self.fields["action_owner"].initial = self.nc.action_owner_id


class ActionPlanForm(NCActionForm):
    """The 4 action-planning fields (NFR-02). The owner field only appears for
    the receiving HoD; the target date is fixed here once work has started."""

    root_cause = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))
    corrective_action = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))
    action_owner = forms.ModelChoiceField(label="Action Owner", queryset=User.objects.none())
    target_date = forms.DateField(label="Target completion date", widget=DateInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        nc = self.nc
        self.fields["root_cause"].initial = nc.root_cause
        self.fields["corrective_action"].initial = nc.corrective_action
        self.fields["target_date"].initial = nc.target_date

        if can_assign_action_owner(self.user, nc):
            self.fields["action_owner"].queryset = _department_members(nc)
            self.fields["action_owner"].initial = nc.action_owner_id
        else:
            del self.fields["action_owner"]  # Action Owners don't reassign themselves

        if nc.status == NC.Status.IN_PROGRESS:
            self.fields["target_date"].disabled = True
            self.fields["target_date"].help_text = "Use “Change target date” to move it."


class TargetDateForm(NCActionForm):
    new_date = forms.DateField(label="New target date", widget=DateInput())
    reason = forms.CharField(label="Reason for the change", widget=forms.Textarea(attrs={"rows": 2}))


class ProgressNoteForm(NCActionForm):
    text = forms.CharField(label="Note", widget=forms.Textarea(attrs={"rows": 2}))


class EvidenceForm(NCActionForm):
    description = forms.CharField(label="What does this evidence show?", max_length=300)
    file = forms.FileField(label="File", required=False)
    link = forms.URLField(label="…or a link (e.g. SharePoint)", required=False, assume_scheme="https")

    def clean_file(self):
        return _check_file_size(self.cleaned_data.get("file"))

    def clean(self):
        data = super().clean()
        if not data.get("file") and not data.get("link"):
            raise forms.ValidationError("Attach a file or enter a link.")
        return data


class SubmitForVerificationForm(NCActionForm):
    completion_date = forms.DateField(label="Date action completed", widget=DateInput())


class VerifyForm(NCActionForm):
    outcome = forms.ChoiceField(
        label="Is the corrective action effective?",
        choices=[("effective", "Effective – close the NC"),
                 ("not_effective", "Not effective – send back for more work")],
        widget=forms.RadioSelect,
    )
    comments = forms.CharField(
        label="Comments", required=False, widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Required if not effective. The Action Owner will see these.",
    )

    def clean(self):
        data = super().clean()
        if data.get("outcome") == "not_effective" and not (data.get("comments") or "").strip():
            self.add_error("comments", "Please explain why it is not effective.")
        return data


class ReopenForm(NCActionForm):
    reason = forms.CharField(label="Reason for reopening", widget=forms.Textarea(attrs={"rows": 2}))
