from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["created_at", "recipient", "subject", "nc", "read_at"]
    list_filter = ["read_at"]
    search_fields = ["subject", "message", "recipient__username"]
