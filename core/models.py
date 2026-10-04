"""Controlled lists the NC Manager maintains through the admin (FR-41).

Items are never deleted once used; untick `is_active` instead so old NCs
keep pointing at a valid record and new forms stop offering it.
"""

from django.conf import settings
from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True, help_text="Short code, e.g. FIN")
    # "HoD of department X" is defined here, not on the user (see CLAUDE.md).
    hod = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_departments",
        verbose_name="Head of Department",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Process(models.Model):
    """Area / process an NC relates to (SRS A4). "Other" is just a row here."""

    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "area / process"
        verbose_name_plural = "areas / processes"

    def __str__(self):
        return self.name


class Source(models.Model):
    """How the NC was identified (SRS A7)."""

    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "source of identification"
        verbose_name_plural = "sources of identification"

    def __str__(self):
        return self.name
