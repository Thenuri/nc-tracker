from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import NC, Evidence, ProgressNote, TargetDateChange


class ReadOnlyInline(admin.TabularInline):
    """Show related records on the NC page without allowing edits or deletes.

    These records are added through the NC screens (Phase 5), not the admin.
    """

    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class EvidenceInline(ReadOnlyInline):
    model = Evidence
    fields = ["description", "file", "link", "uploaded_by", "uploaded_at"]
    readonly_fields = fields


class ProgressNoteInline(ReadOnlyInline):
    model = ProgressNote
    fields = ["text", "author", "created_at"]
    readonly_fields = fields


class TargetDateChangeInline(ReadOnlyInline):
    model = TargetDateChange
    fields = ["old_date", "new_date", "reason", "changed_by", "changed_at"]
    readonly_fields = fields


@admin.register(NC)
class NCAdmin(SimpleHistoryAdmin):
    list_display = ["nc_id", "status", "raising_department", "receiving_department",
                    "process", "date_identified", "target_date"]
    list_filter = ["status", "receiving_department", "raising_department", "process", "source"]
    search_fields = ["nc_id", "description", "identified_by"]
    readonly_fields = ["nc_id", "status", "original_target_date", "logged_by", "logged_at",
                       "created_at", "updated_at"]
    inlines = [EvidenceInline, ProgressNoteInline, TargetDateChangeInline]

    def save_model(self, request, obj, form, change):
        # A9: "logged by" is the person saving the new NC, not a choice.
        if not change:
            obj.logged_by = request.user
        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        return False  # FR-43: NCs are never deleted

    def get_actions(self, request):
        # Remove the bulk "Delete selected" action as well.
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions
