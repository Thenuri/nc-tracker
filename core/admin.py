from django.contrib import admin

from .models import Department, Process, Source


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "hod", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "code"]


@admin.register(Process)
class ProcessAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name"]


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name"]
