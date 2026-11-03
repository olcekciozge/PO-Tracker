from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from accounts.forms import AccountCreateForm, AccountUpdateForm, ProfileForm
from accounts.models import AuditLog
from accounts.services import (
    create_account, log_event, set_account_active, update_account, update_own_profile,
)

User = get_user_model()
PASS = "AnExample-Strong-Password-123"


class AccountServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = User.objects.create_superuser("root", password=PASS)
        cls.manager = User.objects.create_user(
            "manager", password=PASS, role=User.Role.ADMIN, is_staff=True
        )
        cls.student = User.objects.create_user(
            "student", password=PASS, role=User.Role.STUDENT,
            student_number="S102", department_code="CSE"
        )
        cls.teacher = User.objects.create_user(
            "teacher", password=PASS, role=User.Role.INSTRUCTOR, department_code="CSE"
        )

    def create_form(self, **overrides):
        data = {
            "username": "newuser", "first_name": "Yeni", "last_name": "Öğrenci",
            "email": "new@example.edu", "role": User.Role.STUDENT,
            "student_number": "S999", "department_code": "CSE",
            "password1": PASS, "password2": PASS,
        }
        data.update(overrides)
        return AccountCreateForm(data, actor=self.manager)

    def test_create_account_hashes_password_and_audits(self):
        form = self.create_form()
        self.assertTrue(form.is_valid(), form.errors)
        new = create_account(actor=self.manager, form=form)
        self.assertTrue(new.check_password(PASS))
        self.assertFalse(new.is_staff)
        event = AuditLog.objects.get(action=AuditLog.Action.USER_CREATED)
        self.assertEqual(event.actor, self.manager)
        self.assertEqual(event.target, new)
        self.assertEqual(event.metadata["role"], User.Role.STUDENT)

    def test_create_account_cannot_be_called_by_student(self):
        form = self.create_form()
        with self.assertRaises(PermissionDenied):
            create_account(actor=self.student, form=form)
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_staff_admin_cannot_create_another_admin(self):
        form = self.create_form(role=User.Role.ADMIN, student_number="")
        self.assertFalse(form.is_valid())
        with self.assertRaises(Exception):
            create_account(actor=self.manager, form=form)

    def test_update_changes_role_and_logs_fields(self):
        data = {
            "first_name": "Düzenlendi", "last_name": "Kullanıcı",
            "email": "student@example.edu", "role": User.Role.INSTRUCTOR,
            "student_number": "", "department_code": "CSE",
        }
        form = AccountUpdateForm(data, instance=self.student, actor=self.manager)
        self.assertTrue(form.is_valid(), form.errors)
        result = update_account(actor=self.manager, target=self.student, form=form)
        self.assertEqual(result.role, User.Role.INSTRUCTOR)
        self.assertIsNone(result.student_number)
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.USER_UPDATED).exists())

    def test_update_rejects_self_management(self):
        data = {
            "first_name": "Boss", "last_name": "", "email": "",
            "role": User.Role.ADMIN, "student_number": "", "department_code": "",
        }
        form = AccountUpdateForm(data, instance=self.manager, actor=self.manager)
        with self.assertRaises(PermissionDenied):
            update_account(actor=self.manager, target=self.manager, form=form)

    def test_non_superuser_cannot_promote_admin(self):
        data = {
            "first_name": "Y", "last_name": "", "email": "",
            "role": User.Role.ADMIN, "student_number": "", "department_code": "",
        }
        form = AccountUpdateForm(data, instance=self.teacher, actor=self.manager)
        self.assertFalse(form.is_valid())

    def test_deactivate_and_reactivate_audit(self):
        set_account_active(actor=self.manager, target=self.student, active=False)
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_active)
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.USER_DEACTIVATED).exists())
        set_account_active(actor=self.manager, target=self.student, active=True)
        self.student.refresh_from_db()
        self.assertTrue(self.student.is_active)
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.USER_ACTIVATED).exists())

    def test_status_noop_does_not_create_audit(self):
        set_account_active(actor=self.manager, target=self.student, active=True)
        self.assertFalse(AuditLog.objects.filter(action=AuditLog.Action.USER_ACTIVATED).exists())

    def test_cannot_disable_own_account(self):
        with self.assertRaises(PermissionDenied):
            set_account_active(actor=self.manager, target=self.manager, active=False)

    def test_cannot_disable_last_superuser(self):
        with self.assertRaises(PermissionDenied):
            set_account_active(actor=self.manager, target=self.root, active=False)
        self.root.refresh_from_db()
        self.assertTrue(self.root.is_active)

    def test_another_root_can_disable_one_of_two_superusers(self):
        second = User.objects.create_superuser("root2", password=PASS)
        self.assertTrue(self.root.is_active)
        result = set_account_active(actor=second, target=self.root, active=False)
        self.assertFalse(result.is_active)

    def test_profile_update_limited_to_self(self):
        form = ProfileForm({
            "first_name": "Updated", "last_name": "Student", "email": "newstudent@example.edu"
        }, instance=self.student)
        self.assertTrue(form.is_valid(), form.errors)
        updated = update_own_profile(actor=self.student, form=form)
        self.assertEqual(updated.role, User.Role.STUDENT)
        self.assertEqual(updated.first_name, "Updated")
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.PROFILE_UPDATED).exists())

    def test_profile_update_of_someone_else_is_forbidden(self):
        form = ProfileForm({
            "first_name": "Other", "last_name": "", "email": ""
        }, instance=self.teacher)
        with self.assertRaises(PermissionDenied):
            update_own_profile(actor=self.student, form=form)

    def test_manual_audit_uses_empty_metadata_by_default(self):
        event = log_event(actor=self.root, target=self.student, action=AuditLog.Action.USER_UPDATED)
        self.assertEqual(event.metadata, {})
