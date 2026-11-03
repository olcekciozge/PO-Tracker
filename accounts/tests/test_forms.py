from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.forms import AccountCreateForm, AccountUpdateForm, ProfileForm, UserSearchForm

User = get_user_model()
PASS = "AnExample-Strong-Password-123"


def creation_data(**changes):
    data = {
        "username": "newstudent", "first_name": "Aylin", "last_name": "Test",
        "email": "aylin@example.edu", "role": User.Role.STUDENT,
        "student_number": "S2025001", "department_code": "CSE",
        "password1": PASS, "password2": PASS,
    }
    data.update(changes)
    return data


class AccountFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = User.objects.create_superuser("root", password=PASS)
        cls.manager = User.objects.create_user(
            "manager", password=PASS, role=User.Role.ADMIN, is_staff=True
        )
        cls.existing = User.objects.create_user(
            "already", password=PASS, email="existing@example.edu"
        )

    def test_create_form_valid_for_student(self):
        form = AccountCreateForm(creation_data(), actor=self.manager)
        self.assertTrue(form.is_valid(), form.errors)

    def test_create_form_requires_password_confirmation(self):
        form = AccountCreateForm(creation_data(password2="WrongPassword"), actor=self.manager)
        self.assertFalse(form.is_valid())

    def test_create_form_rejects_admin_by_non_superuser(self):
        form = AccountCreateForm(creation_data(role=User.Role.ADMIN, student_number=""), actor=self.manager)
        self.assertFalse(form.is_valid())
        self.assertIn("role", form.errors)

    def test_create_form_root_can_create_admin(self):
        form = AccountCreateForm(creation_data(role=User.Role.ADMIN, student_number=""), actor=self.root)
        self.assertTrue(form.is_valid(), form.errors)

    def test_create_form_rejects_duplicate_email_case_insensitive(self):
        form = AccountCreateForm(creation_data(email="EXISTING@EXAMPLE.EDU"), actor=self.manager)
        self.assertIn("email", form.errors)

    def test_create_form_rejects_duplicate_username_case_insensitive(self):
        form = AccountCreateForm(creation_data(username="ALREADY"), actor=self.manager)
        self.assertIn("username", form.errors)

    def test_head_needs_department(self):
        form = AccountCreateForm(
            creation_data(role=User.Role.HEAD, student_number="", department_code=""),
            actor=self.manager,
        )
        self.assertIn("department_code", form.errors)

    def test_teacher_cannot_have_student_number(self):
        form = AccountCreateForm(creation_data(role=User.Role.INSTRUCTOR), actor=self.manager)
        self.assertIn("student_number", form.errors)

    def test_student_number_is_optional(self):
        form = AccountCreateForm(creation_data(student_number=""), actor=self.manager)
        self.assertTrue(form.is_valid(), form.errors)

    def test_update_form_exposes_no_privileged_flags(self):
        form = AccountUpdateForm(instance=self.existing, actor=self.manager)
        self.assertNotIn("is_staff", form.fields)
        self.assertNotIn("is_superuser", form.fields)
        self.assertNotIn("password", form.fields)

    def test_profile_cannot_edit_role_or_department(self):
        form = ProfileForm(instance=self.existing)
        self.assertEqual(set(form.fields), {"first_name", "last_name", "email"})

    def test_profile_email_must_be_unique(self):
        user = User.objects.create_user("third", password=PASS, email="third@example.edu")
        form = ProfileForm({
            "first_name": "Z", "last_name": "T", "email": "EXISTING@example.edu"
        }, instance=user)
        self.assertIn("email", form.errors)

    def test_user_search_invalid_role_is_rejected(self):
        form = UserSearchForm({"q": "x", "role": "hacker", "status": "active"})
        self.assertFalse(form.is_valid())

    def test_user_search_empty_filters_valid(self):
        self.assertTrue(UserSearchForm({}).is_valid())
