from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.urls import reverse

from accounts.permissions import (
    can_assign_role, can_manage_target, can_view_roster, can_view_user,
    has_role, is_platform_admin,
)
from accounts.selectors import role_totals_for, search_users, visible_users_for

User = get_user_model()
PASS = "AnExample-Strong-Password-123"


class PermissionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = User.objects.create_superuser("root", password=PASS)
        cls.manager = User.objects.create_user(
            "manager", password=PASS, role=User.Role.ADMIN, is_staff=True
        )
        cls.fake_manager = User.objects.create_user(
            "fake", password=PASS, role=User.Role.ADMIN, is_staff=False
        )
        cls.head = User.objects.create_user(
            "head", password=PASS, role=User.Role.HEAD, department_code="CSE"
        )
        cls.head_without_department = User.objects.create_user(
            "head2", password=PASS, role=User.Role.HEAD
        )
        cls.teacher = User.objects.create_user(
            "teacher", password=PASS, role=User.Role.INSTRUCTOR, department_code="CSE"
        )
        cls.student = User.objects.create_user(
            "student", password=PASS, role=User.Role.STUDENT, department_code="CSE"
        )
        cls.other_student = User.objects.create_user(
            "other", password=PASS, role=User.Role.STUDENT, department_code="BME"
        )
        cls.inactive = User.objects.create_user(
            "inactive", password=PASS, role=User.Role.HEAD,
            department_code="CSE", is_active=False
        )

    def test_anonymous_has_no_role(self):
        self.assertFalse(has_role(AnonymousUser(), User.Role.STUDENT))
        self.assertFalse(is_platform_admin(AnonymousUser()))

    def test_role_checks_student_and_instructor(self):
        self.assertTrue(has_role(self.student, User.Role.STUDENT))
        self.assertFalse(has_role(self.student, User.Role.INSTRUCTOR))
        self.assertTrue(has_role(self.teacher, User.Role.INSTRUCTOR))

    def test_admin_overrides_role_gate(self):
        self.assertTrue(has_role(self.root, User.Role.STUDENT))
        self.assertTrue(has_role(self.manager, User.Role.HEAD))

    def test_admin_role_without_staff_is_not_manager(self):
        self.assertFalse(is_platform_admin(self.fake_manager))
        self.assertFalse(has_role(self.fake_manager, User.Role.ADMIN))
        self.assertFalse(can_assign_role(self.fake_manager, User.Role.STUDENT))

    def test_inactive_user_cannot_pass_gate(self):
        self.assertFalse(has_role(self.inactive, User.Role.HEAD))
        self.assertFalse(can_view_roster(self.inactive))

    def test_only_superuser_can_assign_admin(self):
        self.assertTrue(can_assign_role(self.root, User.Role.ADMIN))
        self.assertFalse(can_assign_role(self.manager, User.Role.ADMIN))
        self.assertTrue(can_assign_role(self.manager, User.Role.HEAD))
        self.assertFalse(can_assign_role(self.root, "unknown"))

    def test_manager_cannot_manage_itself(self):
        self.assertFalse(can_manage_target(self.manager, self.manager))
        self.assertFalse(can_manage_target(self.root, self.root))

    def test_staff_manager_cannot_modify_admin_or_superuser(self):
        self.assertFalse(can_manage_target(self.manager, self.root))
        self.assertFalse(can_manage_target(self.manager, self.fake_manager))
        self.assertTrue(can_manage_target(self.manager, self.student))

    def test_root_can_modify_other_managers(self):
        self.assertTrue(can_manage_target(self.root, self.manager))

    def test_head_can_view_only_own_department(self):
        self.assertTrue(can_view_user(self.head, self.student))
        self.assertTrue(can_view_user(self.head, self.teacher))
        self.assertFalse(can_view_user(self.head, self.other_student))
        self.assertFalse(can_view_user(self.head, self.manager))

    def test_head_without_department_has_no_roster(self):
        self.assertFalse(can_view_roster(self.head_without_department))
        self.assertEqual(visible_users_for(self.head_without_department).count(), 0)

    def test_students_can_only_view_themselves(self):
        self.assertTrue(can_view_user(self.student, self.student))
        self.assertFalse(can_view_user(self.student, self.teacher))

    def test_head_roster_is_scoped(self):
        visible = set(visible_users_for(self.head).values_list("username", flat=True))
        self.assertEqual(visible, {"student", "teacher"})

    def test_manager_roster_contains_everyone(self):
        self.assertEqual(visible_users_for(self.manager).count(), User.objects.count())

    def test_filtering_search_and_active_status(self):
        items = search_users(visible_users_for(self.root), "stud", User.Role.STUDENT, "active")
        self.assertEqual(list(items.values_list("username", flat=True)), ["student"])

    def test_role_totals_honor_department_scope(self):
        totals = role_totals_for(self.head)
        self.assertEqual(totals[User.Role.STUDENT], 1)
        self.assertEqual(totals[User.Role.INSTRUCTOR], 1)
        self.assertEqual(totals[User.Role.ADMIN], 0)

    def test_unauthenticated_roster_redirects_to_login(self):
        response = self.client.get(reverse("accounts:user_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_student_roster_is_forbidden(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("accounts:user_list"))
        self.assertEqual(response.status_code, 403)
