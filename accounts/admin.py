from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Django's standard user screens plus our NC Tracker fields."""

    list_display = ["username", "first_name", "last_name", "role_column", "is_delegate", "department"]
    list_filter = ["role", "is_delegate", "department", "is_active"]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("NC Tracker", {"fields": ["role", "is_delegate", "department"]}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("NC Tracker", {"fields": ["first_name", "last_name", "email", "role", "is_delegate", "department"]}),
    )

    @admin.display(description="Role", ordering="role")
    def role_column(self, user):
        # Shows "HoD nominee" for department nominees (FR-09), as elsewhere on screen.
        return user.role_label
