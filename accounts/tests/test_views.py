import csv
import io

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from accounts.models import AuditLog

User = get_user_model()
PASS = "AnExample-Strong-Password-123"


class AccountViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = User.objects.create_superuser("root", email="root@example.edu", password=PASS)
        cls.manager = User.objects.create_user(
            "manager", password=PASS, role=User.Role.ADMIN, is_staff=True
        )
        cls.head = User.objects.create_user(
            "head", password=PASS, role=User.Role.HEAD, department_code="CSE"
        )
        cls.student = User.objects.create_user(
            "student", password=PASS, email="student@example.edu",
            role=User.Role.STUDENT, department_code="CSE"
        )
        cls.teacher = User.objects.create_user(
            "teacher", password=PASS, role=User.Role.INSTRUCTOR, department_code="CSE"
        )
        cls.other_student = User.objects.create_user(
            "other", password=PASS, role=User.Role.STUDENT, department_code="BME"
        )

    def login_as(self, user):
        self.client.force_login(user)

    def test_home_requires_login(self):
        response = self.client.get(reverse("accounts:home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_home_displays_role_and_profile(self):
        self.login_as(self.teacher)
        response = self.client.get(reverse("accounts:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Öğretim Elemanı")
        self.assertContains(response, "Profilim")

    def test_student_cannot_view_users(self):
        self.login_as(self.student)
        self.assertEqual(self.client.get(reverse("accounts:user_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("accounts:user_export")).status_code, 403)
        self.assertEqual(self.client.get(reverse("accounts:audit_list")).status_code, 403)

    def test_head_can_list_own_department_only(self):
        self.login_as(self.head)
        response = self.client.get(reverse("accounts:user_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "student")
        self.assertContains(response, "teacher")
        self.assertNotContains(response, "other")

    def test_head_cannot_view_user_from_another_department(self):
        self.login_as(self.head)
        response = self.client.get(reverse("accounts:user_detail", args=[self.other_student.pk]))
        self.assertEqual(response.status_code, 403)

    def test_head_cannot_create_or_edit_users(self):
        self.login_as(self.head)
        self.assertEqual(self.client.get(reverse("accounts:user_create")).status_code, 403)
        self.assertEqual(self.client.get(reverse("accounts:user_edit", args=[self.student.pk])).status_code, 403)
        self.assertEqual(self.client.post(
            reverse("accounts:user_status", args=[self.student.pk]), {"active": "0"}
        ).status_code, 403)

    def test_manager_can_see_full_roster(self):
        self.login_as(self.manager)
        response = self.client.get(reverse("accounts:user_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "other")

    def test_roster_search_role_and_status_filters(self):
        self.login_as(self.root)
        response = self.client.get(reverse("accounts:user_list"), {
            "q": "teach", "role": User.Role.INSTRUCTOR, "status": "active"
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "teacher")
        self.assertNotContains(response, "other")

    def test_manager_create_user(self):
        self.login_as(self.manager)
        response = self.client.post(reverse("accounts:user_create"), {
            "username": "newstudent", "first_name": "Test", "last_name": "User",
            "email": "newstudent@example.edu", "role": User.Role.STUDENT,
            "department_code": "CSE", "student_number": "S111",
            "password1": PASS, "password2": PASS,
        })
        self.assertEqual(response.status_code, 302)
        created = User.objects.get(username="newstudent")
        self.assertTrue(created.check_password(PASS))
        self.assertTrue(AuditLog.objects.filter(
            action=AuditLog.Action.USER_CREATED, target=created
        ).exists())

    def test_manager_cannot_create_admin(self):
        self.login_as(self.manager)
        response = self.client.post(reverse("accounts:user_create"), {
            "username": "badadmin", "first_name": "", "last_name": "",
            "email": "", "role": User.Role.ADMIN,
            "department_code": "", "student_number": "",
            "password1": PASS, "password2": PASS,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="badadmin").exists())

    def test_superuser_can_create_admin(self):
        self.login_as(self.root)
        response = self.client.post(reverse("accounts:user_create"), {
            "username": "newadmin", "first_name": "", "last_name": "",
            "email": "", "role": User.Role.ADMIN,
            "department_code": "", "student_number": "",
            "password1": PASS, "password2": PASS,
        })
        self.assertEqual(response.status_code, 302)
        new_admin = User.objects.get(username="newadmin")
        self.assertTrue(new_admin.is_staff)
        self.assertFalse(new_admin.is_superuser)

    def test_manager_can_edit_student_not_superuser(self):
        self.login_as(self.manager)
        good = self.client.post(reverse("accounts:user_edit", args=[self.student.pk]), {
            "first_name": "Updated", "last_name": "", "email": "student@example.edu",
            "role": User.Role.STUDENT, "student_number": "S998", "department_code": "CSE",
        })
        self.assertEqual(good.status_code, 302)
        self.student.refresh_from_db()
        self.assertEqual(self.student.student_number, "S998")
        self.assertEqual(self.client.get(
            reverse("accounts:user_edit", args=[self.root.pk])
        ).status_code, 403)

    def test_manager_cannot_edit_self(self):
        self.login_as(self.manager)
        response = self.client.get(reverse("accounts:user_edit", args=[self.manager.pk]))
        self.assertEqual(response.status_code, 403)

    def test_status_requires_post(self):
        self.login_as(self.manager)
        response = self.client.get(reverse("accounts:user_status", args=[self.student.pk]))
        self.assertEqual(response.status_code, 405)

    def test_status_rejects_invalid_action(self):
        self.login_as(self.manager)
        response = self.client.post(reverse("accounts:user_status", args=[self.student.pk]), {
            "active": "unexpected"
        })
        self.assertEqual(response.status_code, 400)

    def test_disable_account(self):
        self.login_as(self.manager)
        response = self.client.post(reverse("accounts:user_status", args=[self.student.pk]), {
            "active": "0"
        })
        self.assertEqual(response.status_code, 302)
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_active)

    def test_profile_update_cannot_escalate_role(self):
        self.login_as(self.student)
        response = self.client.post(reverse("accounts:profile"), {
            "first_name": "Updated", "last_name": "", "email": "student@example.edu",
            "role": User.Role.ADMIN, "is_superuser": "1", "department_code": "BME",
        })
        self.assertEqual(response.status_code, 302)
        self.student.refresh_from_db()
        self.assertEqual(self.student.first_name, "Updated")
        self.assertEqual(self.student.role, User.Role.STUDENT)
        self.assertEqual(self.student.department_code, "CSE")
        self.assertFalse(self.student.is_superuser)

    def test_profile_get_for_student(self):
        self.login_as(self.student)
        response = self.client.get(reverse("accounts:profile"))
        self.assertContains(response, "Öğrenci")

    def test_anonymous_profile_redirects(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 302)

    def test_csv_export_is_scoped_to_head_department(self):
        self.login_as(self.head)
        response = self.client.get(reverse("accounts:user_export"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        text = response.content.decode("utf-8-sig")
        self.assertIn("student", text)
        self.assertIn("teacher", text)
        self.assertNotIn("other", text)

    def test_csv_export_filters_by_role(self):
        self.login_as(self.head)
        response = self.client.get(reverse("accounts:user_export"), {"role": User.Role.STUDENT})
        rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][0], "student")

    def test_csv_formula_injection_is_escaped(self):
        target = User.objects.create_user(
            "formula", password=PASS, first_name="=SUM(1+2)", department_code="CSE"
        )
        self.login_as(self.root)
        response = self.client.get(reverse("accounts:user_export"), {"q": "formula"})
        self.assertIn("'=SUM(1+2)", response.content.decode("utf-8-sig"))

    def test_admin_can_view_audit_log(self):
        self.login_as(self.root)
        response = self.client.get(reverse("accounts:audit_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hesap işlem geçmişi")

    def test_pagination_handles_bad_values(self):
        self.login_as(self.root)
        response = self.client.get(reverse("accounts:user_list"), {"page": "not-a-number"})
        self.assertEqual(response.status_code, 200)

    def test_password_change_requires_login(self):
        response = self.client.get(reverse("accounts:password_change"))
        self.assertEqual(response.status_code, 302)

    def test_password_change_logs_and_keeps_session(self):
        self.login_as(self.student)
        changed = self.client.post(reverse("accounts:password_change"), {
            "old_password": PASS,
            "new_password1": "New-Password-12345!",
            "new_password2": "New-Password-12345!",
        })
        self.assertEqual(changed.status_code, 302)
        self.student.refresh_from_db()
        self.assertTrue(self.student.check_password("New-Password-12345!"))
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.PASSWORD_CHANGED).exists())
        self.assertEqual(self.client.get(reverse("accounts:profile")).status_code, 200)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_sends_email_for_active_usable_account(self):
        response = self.client.post(reverse("accounts:password_reset"), {
            "email": "student@example.edu"
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("password/reset/", mail.outbox[0].body)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_does_not_enumerate_unknown_account(self):
        response = self.client.post(reverse("accounts:password_reset"), {
            "email": "notfound@example.edu"
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)

    def test_logout_post_only(self):
        self.login_as(self.student)
        get_response = self.client.get(reverse("accounts:logout"))
        self.assertEqual(get_response.status_code, 405)
        post_response = self.client.post(reverse("accounts:logout"))
        self.assertEqual(post_response.status_code, 302)
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.LOGOUT).exists())

    def test_csrf_is_required_for_status_changes(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.manager)
        response = csrf_client.post(
            reverse("accounts:user_status", args=[self.student.pk]), {"active": "0"}
        )
        self.assertEqual(response.status_code, 403)
        self.student.refresh_from_db()
        self.assertTrue(self.student.is_active)

    def test_csrf_is_required_for_user_creation(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.manager)
        response = csrf_client.post(reverse("accounts:user_create"), {
            "username": "unexpected", "role": User.Role.STUDENT,
            "password1": PASS, "password2": PASS,
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(username="unexpected").exists())

    def test_inactive_user_cannot_login(self):
        self.other_student.is_active = False
        self.other_student.save(update_fields=["is_active"])
        response = self.client.post(reverse("accounts:login"), {
            "username": "other", "password": PASS
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
