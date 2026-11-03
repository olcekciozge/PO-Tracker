from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import AuditLog

User = get_user_model()
PASS = "AnExample-Strong-Password-123"


class UserModelTests(TestCase):
    def test_new_user_is_student_by_default(self):
        user = User.objects.create_user("student1", password=PASS)
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_student)

    def test_superuser_has_admin_role(self):
        user = User.objects.create_superuser("root", password=PASS)
        self.assertEqual(user.role, User.Role.ADMIN)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_superuser_cannot_override_role_on_creation(self):
        user = User.objects.create_superuser(
            "root", password=PASS, role=User.Role.STUDENT
        )
        self.assertEqual(user.role, User.Role.ADMIN)

    def test_student_number_blank_becomes_null(self):
        first = User.objects.create_user("first", password=PASS, student_number="")
        second = User.objects.create_user("second", password=PASS, student_number=" ")
        self.assertIsNone(first.student_number)
        self.assertIsNone(second.student_number)

    def test_student_number_unique_when_populated(self):
        User.objects.create_user("first", password=PASS, student_number="S001")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user("second", password=PASS, student_number="S001")

    def test_email_and_department_normalization(self):
        user = User.objects.create_user(
            "teacher", password=PASS, role=User.Role.INSTRUCTOR,
            department_code=" cse ", email=" TEST@EXAMPLE.EDU "
        )
        self.assertEqual(user.department_code, "CSE")
        self.assertEqual(user.email, "test@example.edu")

    def test_head_needs_department_in_clean(self):
        user = User(username="chair", role=User.Role.HEAD)
        with self.assertRaises(ValidationError) as ctx:
            user.full_clean()
        self.assertIn("department_code", ctx.exception.message_dict)

    def test_instructor_cannot_keep_student_number(self):
        user = User(username="teacher", role=User.Role.INSTRUCTOR, student_number="ABC123")
        with self.assertRaises(ValidationError) as ctx:
            user.full_clean()
        self.assertIn("student_number", ctx.exception.message_dict)

    def test_duplicate_email_is_rejected_case_insensitively(self):
        User.objects.create_user("one", email="first@example.edu", password=PASS)
        second = User(username="two", email="FIRST@example.edu")
        with self.assertRaises(ValidationError) as ctx:
            second.full_clean()
        self.assertIn("email", ctx.exception.message_dict)

    def test_superuser_role_cannot_be_downgraded(self):
        root = User.objects.create_superuser("root", password=PASS)
        root.role = User.Role.STUDENT
        with self.assertRaises(ValidationError):
            root.full_clean()

    def test_display_name_falls_back_to_username(self):
        user = User.objects.create_user("plain", password=PASS)
        self.assertEqual(user.display_name, "plain")
        user.first_name, user.last_name = "Buğra", "Örnek"
        self.assertEqual(user.display_name, "Buğra Örnek")
        self.assertIn("plain", str(user))

    def test_role_properties(self):
        chair = User.objects.create_user("chair", role=User.Role.HEAD, department_code="CSE")
        teacher = User.objects.create_user("teacher", role=User.Role.INSTRUCTOR)
        self.assertTrue(chair.is_department_head)
        self.assertFalse(chair.is_student)
        self.assertTrue(teacher.is_instructor)


class AuditLogTests(TestCase):
    def test_log_keeps_actor_and_target(self):
        manager = User.objects.create_superuser("root", password=PASS)
        target = User.objects.create_user("student", password=PASS)
        event = AuditLog.objects.create(
            actor=manager, target=target, action=AuditLog.Action.USER_UPDATED,
            metadata={"fields": ["department_code"]},
        )
        self.assertEqual(event.actor, manager)
        self.assertEqual(event.target, target)
        self.assertIn("department_code", event.metadata["fields"])

    def test_audit_actor_set_null_after_deletion(self):
        actor = User.objects.create_user("temp", password=PASS)
        event = AuditLog.objects.create(actor=actor, target=actor, action=AuditLog.Action.LOGIN)
        actor.delete()
        event.refresh_from_db()
        self.assertIsNone(event.actor)
        self.assertIsNone(event.target)

    def test_most_recent_event_first(self):
        user = User.objects.create_user("student", password=PASS)
        old = AuditLog.objects.create(actor=user, action=AuditLog.Action.LOGIN)
        new = AuditLog.objects.create(actor=user, action=AuditLog.Action.LOGOUT)
        ids = list(AuditLog.objects.values_list("id", flat=True))
        self.assertEqual(ids[0], new.pk)
        self.assertEqual(ids[1], old.pk)
