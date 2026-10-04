from django.conf import settings
from django.db import models


class Notification(models.Model):
    """A message to one user, shown in the on-screen panel.

    Created only by notify() in notifications/services.py (Phase 4), which
    also sends the email, so switching to real Outlook email is settings-only.
    """

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    subject = models.CharField(max_length=200)
    message = models.TextField()
    nc = models.ForeignKey(
        "ncs.NC", on_delete=models.PROTECT, null=True, blank=True, related_name="notifications"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"To {self.recipient}: {self.subject}"

    @property
    def is_read(self):
        return self.read_at is not None
