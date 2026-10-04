"""On-screen notifications panel – the prototype's stand-in inbox."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Notification

SHOW_LATEST = 100


@login_required
def notification_list(request):
    notifications = request.user.notifications.select_related("nc")[:SHOW_LATEST]
    return render(request, "notifications/list.html", {"notifications": notifications})


@login_required
@require_POST
def open_notification(request, pk):
    """Mark as read, then go to the NC it is about (or back to the list)."""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at"])
    return redirect(notification.nc or "notifications:list")


@login_required
@require_POST
def mark_all_read(request):
    request.user.notifications.filter(read_at__isnull=True).update(read_at=timezone.now())
    return redirect("notifications:list")
