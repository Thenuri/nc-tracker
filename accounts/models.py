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
