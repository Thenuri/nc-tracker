"""The ONE way the app sends a notification.

Every notification is saved (for the on-screen panel) AND emailed with
Django's send_mail. In the prototype the console email backend prints the
email in the terminal; switching to the real nctracker@apiit.lk mailbox is a
settings change only (EMAIL_* in .env).
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

from .models import Notification

logger = logging.getLogger(__name__)


def notify(recipient, subject, message, nc=None):
    """Save a Notification for `recipient` and email it to them.

    Returns the Notification, or None if there is nobody to notify
    (e.g. a department with no HoD set yet).
    """
    if recipient is None:
        return None

    if nc is not None:
        # UI-03: every NC email carries a direct link to the NC page.
        message = f"{message}\n\nOpen {nc.nc_id}: {settings.SITE_URL}{nc.get_absolute_url()}"

    notification = Notification.objects.create(
        recipient=recipient, subject=subject, message=message, nc=nc
    )

    if recipient.email:
        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [recipient.email])
        except Exception:
            # A mail server problem must not undo the NC change itself.
            # The notification is still saved and shown on screen.
            logger.exception("Could not email notification %s to %s", notification.pk, recipient.email)

    return notification
