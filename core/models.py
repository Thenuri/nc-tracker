"""Controlled lists the NC Manager maintains through the admin (FR-41).

Items are never deleted once used; untick `is_active` instead so old NCs
keep pointing at a valid record and new forms stop offering it.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

ACTIVE_HELP = "Untick to stop offering this for new NCs. Existing NCs keep it. (Use this instead of deleting.)"


class Department(models.Model):
    name = models.CharField("department name", max_length=100, unique=True, help_text="e.g. Finance")
    code = models.CharField("short code", max_length=10, unique=True, help_text="A few capital letters, e.g. FIN")
    # "HoD of department X" is defined here, not on the user (see CLAUDE.md).
    hod = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_departments",
        verbose_name="Head of Department",
        help_text="Validates this department's NCs and chooses the Action Owner. "
                  "Can see all NCs across APIIT (read-only).",
    )
    # FR-09 "receiving HoD (or nominee)": someone who can act in the HoD's
    # place on this department's NCs, e.g. while the HoD is on leave.
    nominee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nominated_departments",
        verbose_name="HoD nominee",
        help_text="Optional. Can validate and act on this department's NCs in place of the HoD.",
    )
    is_active = models.BooleanField("active", default=True, help_text=ACTIVE_HELP)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def clean(self):
        if self.nominee_id and self.nominee_id == self.hod_id:
            raise ValidationError({"nominee": "The nominee must be someone other than the HoD."})
        if self.nominee_id and (not self.pk or self.nominee.department_id != self.pk):
            raise ValidationError({"nominee": "The nominee must be a member of this department."})

    @property
    def heads(self):
        """People who act for this department on its NCs: the HoD and nominee (if set)."""
        return [person for person in (self.hod, self.nominee) if person is not None]


class Process(models.Model):
    """Area / process an NC relates to (SRS A4). "Other" is just a row here."""

    name = models.CharField(max_length=100, unique=True, help_text='e.g. Fee collection. Keep an "Other" item.')
    is_active = models.BooleanField("active", default=True, help_text=ACTIVE_HELP)

    class Meta:
        ordering = ["name"]
        verbose_name = "area / process"
        verbose_name_plural = "areas / processes"

    def __str__(self):
        return self.name


class Source(models.Model):
    """How the NC was identified (SRS A7)."""

    name = models.CharField(max_length=100, unique=True, help_text='e.g. Internal review. Keep an "Other" item.')
    is_active = models.BooleanField("active", default=True, help_text=ACTIVE_HELP)

    class Meta:
        ordering = ["name"]
        verbose_name = "source of identification"
        verbose_name_plural = "sources of identification"

    def __str__(self):
        return self.name
