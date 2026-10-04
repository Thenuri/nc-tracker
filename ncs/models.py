"""Non-conformity (NC) and the records attached to it.

Field groups follow SRS Section 4 (Parts A–D). Status changes are NOT made
here: `status` is not editable and only ncs/workflow.py (Phase 4) changes it.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Max
from django.utils import timezone
from simple_history.models import HistoricalRecords


def not_in_future(value):
    """FR-05: date identified cannot be a future date."""
    if value > timezone.localdate():
        raise ValidationError("This date cannot be in the future.")


class NCQuerySet(models.QuerySet):
    def delete(self):
        # FR-43: blocks bulk deletes such as NC.objects.all().delete()
        raise PermissionError("NCs cannot be deleted. Record invalid NCs as Not Valid instead (FR-43).")


class NC(models.Model):
    class Status(models.TextChoices):
        PENDING_VALIDATION = "PENDING_VALIDATION", "Pending validation"
        VALID = "VALID", "Valid"
        DISPUTED = "DISPUTED", "Disputed"
        NOT_VALID = "NOT_VALID", "Not valid"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        PENDING_VERIFICATION = "PENDING_VERIFICATION", "Pending verification"
        CLOSED = "CLOSED", "Closed"

    class Severity(models.TextChoices):
        MINOR = "MINOR", "Minor"
        MAJOR = "MAJOR", "Major"

    class Outcome(models.TextChoices):
        EFFECTIVE = "EFFECTIVE", "Effective"
        NOT_EFFECTIVE = "NOT_EFFECTIVE", "Not effective"

    # --- NC ID (A1, FR-03) ---------------------------------------------------
    # Stored as year + sequence so numbering is reliable past 999 a year;
    # nc_id is the display form "NC-2026-001".
    nc_id = models.CharField("NC ID", max_length=20, unique=True, editable=False)
    year = models.PositiveSmallIntegerField(editable=False)
    sequence = models.PositiveIntegerField(editable=False)

    # --- Part A: Logging (NC Manager) ---------------------------------------
    raising_department = models.ForeignKey(
        "core.Department", on_delete=models.PROTECT, related_name="ncs_raised"
    )
    receiving_department = models.ForeignKey(
        "core.Department", on_delete=models.PROTECT, related_name="ncs_received"
    )
    process = models.ForeignKey(
        "core.Process", on_delete=models.PROTECT, verbose_name="area / process"
    )
    process_other = models.CharField(
        "other area / process", max_length=200, blank=True, help_text='Only if "Other" is chosen'
    )
    description = models.TextField(
        "description of the non-conformity",
        help_text="What happened and which requirement was not met",
    )
    date_identified = models.DateField(validators=[not_in_future])
    source = models.ForeignKey(
        "core.Source", on_delete=models.PROTECT, verbose_name="source of identification"
    )
    source_other = models.CharField(
        "other source", max_length=200, blank=True, help_text='Only if "Other" is chosen'
    )
    identified_by = models.CharField(
        max_length=200, help_text="Person in the raising department who found it"
    )
    logged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ncs_logged"
    )
    logged_at = models.DateTimeField(auto_now_add=True)
    attachment = models.FileField(
        "supporting attachment", upload_to="nc_attachments/%Y/", blank=True
    )
    severity = models.CharField(max_length=10, choices=Severity.choices, blank=True)

    # --- Status ---------------------------------------------------------------
    status = models.CharField(
        max_length=25,
        choices=Status.choices,
        default=Status.PENDING_VALIDATION,
        editable=False,  # only ncs/workflow.py may change this
    )
    validation_deadline = models.DateField(null=True, blank=True)

    # --- Part B: Validation (receiving HoD) ------------------------------------
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="+",
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    dispute_reason = models.TextField("reason not valid", blank=True)

    # --- D8: Dispute decision (NC Manager) ------------------------------------
    dispute_decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="+",
    )
    dispute_decided_at = models.DateTimeField(null=True, blank=True)
    dispute_rationale = models.TextField("dispute decision rationale", blank=True)

    # --- Part C: Action planning (max 4 fields, NFR-02) -----------------------
    root_cause = models.TextField(blank=True)
    corrective_action = models.TextField(blank=True)
    action_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="ncs_owned",
    )
    target_date = models.DateField("target completion date", null=True, blank=True)
    # FR-20: the first target date is kept even if it is changed later.
    original_target_date = models.DateField(null=True, blank=True, editable=False)

    # --- Part D: Completion and verification ----------------------------------
    completion_date = models.DateField("date action completed", null=True, blank=True)
    verification_outcome = models.CharField(max_length=15, choices=Outcome.choices, blank=True)
    verification_comments = models.TextField(blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="+",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField("closure date", null=True, blank=True)

    # --- System fields ----------------------------------------------------------
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()  # FR-42: who changed what, when

    objects = NCQuerySet.as_manager()

    class Meta:
        verbose_name = "NC"
        verbose_name_plural = "NCs"
        ordering = ["-year", "-sequence"]
        constraints = [
            models.UniqueConstraint(fields=["year", "sequence"], name="unique_nc_number_per_year"),
        ]

    def __str__(self):
        return self.nc_id or "New NC"

    def save(self, *args, **kwargs):
        if not self.pk:
            self._assign_nc_id()
        super().save(*args, **kwargs)

    def _assign_nc_id(self):
        """Next number for this year; numbering restarts at 001 each January."""
        self.year = timezone.localdate().year
        last = NC.objects.filter(year=self.year).aggregate(m=Max("sequence"))["m"] or 0
        self.sequence = last + 1
        self.nc_id = f"NC-{self.year}-{self.sequence:03d}"

    def delete(self, *args, **kwargs):
        raise PermissionError("NCs cannot be deleted. Record invalid NCs as Not Valid instead (FR-43).")

    @property
    def days_open(self):
        """Days from logging until closure (or until today if still open)."""
        end = self.closed_at or timezone.now()
        return (timezone.localdate(end) - timezone.localdate(self.logged_at)).days


class Evidence(models.Model):
    """Evidence of completion (D3): a file, a link, or both, with a description."""

    nc = models.ForeignKey(NC, on_delete=models.PROTECT, related_name="evidence")
    file = models.FileField(upload_to="evidence/%Y/", blank=True)
    link = models.URLField(max_length=500, blank=True)
    description = models.CharField(max_length=300)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "evidence"
        ordering = ["uploaded_at"]

    def __str__(self):
        return f"{self.nc} – {self.description}"

    def clean(self):
        if not self.file and not self.link:
            raise ValidationError("Attach a file or enter a link.")


class ProgressNote(models.Model):
    """Free-text updates by the receiving department (FR-18)."""

    nc = models.ForeignKey(NC, on_delete=models.PROTECT, related_name="progress_notes")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.nc} – note by {self.author}"


class TargetDateChange(models.Model):
    """Every change to an NC's target date, with the reason (FR-20)."""

    nc = models.ForeignKey(NC, on_delete=models.PROTECT, related_name="target_date_changes")
    old_date = models.DateField()
    new_date = models.DateField()
    reason = models.TextField()
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["changed_at"]

    def __str__(self):
        return f"{self.nc}: {self.old_date} → {self.new_date}"
