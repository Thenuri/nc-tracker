"""Admin screens for the lists the NC Manager maintains (FR-41, NFR-09)."""

from django.contrib import admin
from django.db.models import Count, Q

from accounts.models import User

from .models import Department, Process, Source

# Same rule as NC.objects.open(): Closed and Not Valid NCs are not open (FR-15).
NOT_OPEN = ["CLOSED", "NOT_VALID"]


class ListItemAdmin(admin.ModelAdmin):
    """Shared behaviour for every list: search, active filter, never delete.

    Deleting an item that NCs point to would break those NCs, so items are
    switched off with "Active" instead (see core/models.py).
    """

    search_fields = ["name"]
    list_filter = ["is_active"]
    empty_value_display = "— not set —"

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Department)
class DepartmentAdmin(ListItemAdmin):
    list_display = ["name", "code", "hod", "nominee", "open_ncs", "received_ncs", "is_active"]
    search_fields = ["name", "code"]
    fieldsets = [
        ("Department", {"fields": ["name", "code", "is_active"]}),
        ("Who acts for this department", {
            "fields": ["hod", "nominee"],
            "description": "NCs raised against this department go to these people for "
                           "validation and action. Set a nominee so NCs keep moving when "
                           "the HoD is away.",
        }),
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("hod", "nominee").annotate(
            received=Count("ncs_received", distinct=True),
            open=Count("ncs_received", filter=~Q(ncs_received__status__in=NOT_OPEN), distinct=True),
        )

    @admin.display(description="Open NCs", ordering="open")
    def open_ncs(self, dept):
        return dept.open

    @admin.display(description="NCs received", ordering="received")
    def received_ncs(self, dept):
        return dept.received

    def get_form(self, request, obj=None, **kwargs):
        request._department_being_edited = obj  # used just below
        return super().get_form(request, obj, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Only offer people who make sense, sorted by name, instead of every login.
        people = User.objects.filter(is_active=True, is_superuser=False).order_by("first_name", "last_name")
        if db_field.name == "hod":
            kwargs["queryset"] = people
        elif db_field.name == "nominee":
            dept = getattr(request, "_department_being_edited", None)
            # The nominee must belong to the department (checked again in Department.clean).
            kwargs["queryset"] = people.filter(department=dept) if dept else people.none()
            kwargs["help_text"] = ("Optional. Must be a member of this department. Can validate and act "
                                   "on its NCs in place of the HoD."
                                   if dept else "Save the department first, then choose a nominee.")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class UsedInNCsMixin:
    """Adds a "Used in NCs" column so the NC Manager sees which items matter."""

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(used=Count("nc"))

    @admin.display(description="Used in NCs", ordering="used")
    def used_in_ncs(self, item):
        return item.used


@admin.register(Process)
class ProcessAdmin(UsedInNCsMixin, ListItemAdmin):
    list_display = ["name", "used_in_ncs", "is_active"]


@admin.register(Source)
class SourceAdmin(UsedInNCsMixin, ListItemAdmin):
    list_display = ["name", "used_in_ncs", "is_active"]
