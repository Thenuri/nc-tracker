from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """APIIT staff member using the NC Tracker.

    Roles are stored here but never checked directly in views; Phase 3 adds
    permission helper functions that read `request.user`, so real Microsoft
    login can replace the prototype role switcher without other changes.
    """

    class Role(models.TextChoices):
        NC_MANAGER = "nc_manager", "NC Manager"
        HOD = "hod", "Head of Department"
        ACTION_OWNER = "action_owner", "Action Owner"
        MANAGEMENT = "management", "Management"
        STAFF = "staff", "Staff"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STAFF)
    # The delegate has exactly the same rights as the NC Manager (NFR-08);
    # this flag only changes how the person is labelled on screen.
    is_delegate = models.BooleanField(
        "NC Manager delegate",
        default=False,
        help_text="Tick for the named delegate. Role must also be NC Manager.",
    )
    department = models.ForeignKey(
        "core.Department",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="members",
    )

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def role_label(self):
        """The role as shown on screen.

        A department's HoD nominee (FR-09) is shown as "HoD nominee" rather than
        their stored role (usually "Staff"). Being a nominee is set on the
        Department, not here, so it can't drift out of step with the rights.
        """
        is_nominee = getattr(self, "is_nominee", None)  # pre-filled by list queries
        if is_nominee is None:
            is_nominee = self.nominated_departments.exists()
        return "HoD nominee" if is_nominee else self.get_role_display()

    def save(self, *args, **kwargs):
        # FR-41: the NC Manager maintains the lists in the admin, so they need
        # to be able to sign in to it. (Leaving the role does not remove
        # is_staff, because IT admins may have it for other reasons.)
        if self.role == self.Role.NC_MANAGER:
            self.is_staff = True
        super().save(*args, **kwargs)

        from .admin_access import sync_nc_manager_access  # avoids a circular import
        sync_nc_manager_access(self)
