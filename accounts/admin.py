"""Django admin integration. Web account manager uses stricter workflows."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import AuditLog, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        "username", "display_name", "role", "department_code", "student_number",
        "email", "is_active", "is_staff", "last_login",
    )
    list_display_links = ("username",)
    list_filter = ("role", "department_code", "is_active", "is_staff", "is_superuser")
    search_fields = ("username", "first_name", "last_name", "email", "student_number")
    ordering = ("username",)
    list_per_page = 50
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("PO Tracker kimliği", {"fields": ("role", "student_number", "department_code")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("PO Tracker kimliği", {
            "fields": ("first_name", "last_name", "email", "role", "student_number", "department_code"),
        }),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "actor", "target")
    list_filter = ("action", "created_at")
    search_fields = ("actor__username", "target__username")
    readonly_fields = ("created_at", "actor", "target", "action", "metadata")
    date_hierarchy = "created_at"
    list_select_related = ("actor", "target")
    list_per_page = 50

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
