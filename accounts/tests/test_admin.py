from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from accounts.models import AuditLog

User = get_user_model()


class AdminRegistrationTests(TestCase):
    def setUp(self):
        self.request = RequestFactory().get("/admin/")
        self.user_admin = admin.site._registry[User]
        self.audit_admin = admin.site._registry[AuditLog]

    def test_user_model_is_registered_in_django_admin(self):
        self.assertIsNotNone(self.user_admin)

    def test_audit_log_is_registered(self):
        self.assertIsNotNone(self.audit_admin)

    def test_user_admin_includes_app_fields(self):
        all_fields = [
            field for _, options in self.user_admin.fieldsets
            for field in options.get("fields", ())
        ]
        self.assertIn("role", all_fields)
        self.assertIn("student_number", all_fields)
        self.assertIn("department_code", all_fields)

    def test_audit_log_cannot_be_added_manually(self):
        self.assertFalse(self.audit_admin.has_add_permission(self.request))

    def test_audit_log_cannot_be_changed_or_deleted(self):
        self.assertFalse(self.audit_admin.has_change_permission(self.request))
        self.assertFalse(self.audit_admin.has_delete_permission(self.request))
