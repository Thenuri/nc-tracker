"""Register filters (FR-32). Used by the register screen AND the exports, so an
export always contains exactly the rows the person is looking at (FR-36)."""

from django import forms
from django.db.models import Q

from accounts.models import User
from core.forms import BootstrapFormMixin, DateInput
from core.models import Department, Process, Source
from ncs.models import NC


class RegisterFilterForm(BootstrapFormMixin, forms.Form):
    q = forms.CharField(label="Search", required=False,
                        widget=forms.TextInput(attrs={"placeholder": "NC ID or words"}))
    status = forms.ChoiceField(label="Status", required=False,
                               choices=[("", "Any status"), ("open", "All open")] + NC.Status.choices)
    overdue = forms.ChoiceField(label="Overdue", required=False,
                                choices=[("", "Any"), ("yes", "Overdue only"), ("no", "Not overdue")])
    receiving_department = forms.ModelChoiceField(label="Receiving dept", required=False,
                                                  queryset=Department.objects.all(), empty_label="Any")
    raising_department = forms.ModelChoiceField(label="Raising dept", required=False,
                                                queryset=Department.objects.all(), empty_label="Any")
    process = forms.ModelChoiceField(label="Area / process", required=False,
                                     queryset=Process.objects.all(), empty_label="Any")
    source = forms.ModelChoiceField(label="Source", required=False,
                                    queryset=Source.objects.all(), empty_label="Any")
    action_owner = forms.ModelChoiceField(label="Action Owner", required=False, empty_label="Any",
                                          queryset=User.objects.filter(ncs_owned__isnull=False).distinct())
    date_from = forms.DateField(label="Identified from", required=False, widget=DateInput())
    date_to = forms.DateField(label="Identified to", required=False, widget=DateInput())


def apply_filters(queryset, form):
    """Narrow `queryset` using a validated RegisterFilterForm."""
    if not form.is_valid():
        return queryset
    data = form.cleaned_data

    if data["q"]:
        words = data["q"].strip()
        queryset = queryset.filter(Q(nc_id__icontains=words) | Q(description__icontains=words))
    if data["status"] == "open":
        queryset = queryset.open()
    elif data["status"]:
        queryset = queryset.filter(status=data["status"])
    if data["overdue"] == "yes":
        queryset = queryset.overdue()
    elif data["overdue"] == "no":
        queryset = queryset.exclude(pk__in=NC.objects.overdue().values("pk"))
    for field in ("receiving_department", "raising_department", "process", "source", "action_owner"):
        if data[field]:
            queryset = queryset.filter(**{field: data[field]})
    if data["date_from"]:
        queryset = queryset.filter(date_identified__gte=data["date_from"])
    if data["date_to"]:
        queryset = queryset.filter(date_identified__lte=data["date_to"])
    return queryset
