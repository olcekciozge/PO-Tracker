from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .selectors import instructor_courses, student_po_profile

User = get_user_model()


class LandingPageTests(TestCase):
    def test_landing_page_is_public(self):
        response = self.client.get(reverse("dashboard:landing"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/landing.html")
        self.assertContains(response, "PO Tracker")
        self.assertContains(response, reverse("accounts:login"))

    def test_signed_in_student_is_sent_to_profile(self):
        user = User.objects.create_user(username="ogrenci", password="test-pass-123")
        self.client.force_login(user)
        response = self.client.get(reverse("dashboard:landing"))
        self.assertRedirects(response, reverse("dashboard:student_profile"), fetch_redirect_response=False)

    def test_signed_in_instructor_is_sent_to_courses(self):
        user = User.objects.create_user(username="hoca", password="test-pass-123", role=User.Role.INSTRUCTOR)
        self.client.force_login(user)
        response = self.client.get(reverse("dashboard:landing"))
        self.assertRedirects(response, reverse("dashboard:instructor_courses"), fetch_redirect_response=False)

    def test_signed_in_head_is_sent_to_home(self):
        user = User.objects.create_user(
            username="baskan", password="test-pass-123", role=User.Role.HEAD, department_code="CSE"
        )
        self.client.force_login(user)
        response = self.client.get(reverse("dashboard:landing"))
        self.assertRedirects(response, reverse("accounts:home"), fetch_redirect_response=False)


class StudentProfileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def test_scores_match_the_worked_example(self):
        profile = student_po_profile(User.objects.get(username="elif"))
        scores = {item["po"].code: item["score"] for item in profile["pos"]}
        self.assertAlmostEqual(scores["PO1"], 85.0, places=1)
        self.assertAlmostEqual(scores["PO2"], 82.9, places=1)
        self.assertIsNone(scores["PO3"])

    def test_student_sees_their_profile(self):
        self.client.force_login(User.objects.get(username="elif"))
        response = self.client.get(reverse("dashboard:student_profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "85,0")
        self.assertContains(response, "82,9")

    def test_other_roles_cannot_open_student_profile(self):
        self.client.force_login(User.objects.get(username="demo.hoca"))
        response = self.client.get(reverse("dashboard:student_profile"))
        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_sent_to_login(self):
        response = self.client.get(reverse("dashboard:student_profile"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)


class InstructorCoursesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def test_course_card_counts_and_checklist(self):
        cards = instructor_courses(User.objects.get(username="demo.hoca"))
        self.assertEqual(len(cards), 1)
        card = cards[0]
        self.assertEqual(card["course"].student_count, 2)
        self.assertEqual(card["course"].assessment_count, 4)
        self.assertEqual(card["course"].lo_count, 4)
        self.assertEqual((card["graded"], card["expected"]), (4, 8))
        # Demo dersinde ağırlıklar %100 ve LO'lar tanımlı, ama bağlantılar eksik
        self.assertEqual([check["ok"] for check in card["checks"]], [True, True, False, False])
        self.assertFalse(card["setup_ok"])

    def test_instructor_sees_their_courses(self):
        self.client.force_login(User.objects.get(username="demo.hoca"))
        response = self.client.get(reverse("dashboard:instructor_courses"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CSE 311")
        self.assertContains(response, "Kurulum eksik")

    def test_students_cannot_open_instructor_courses(self):
        self.client.force_login(User.objects.get(username="elif"))
        response = self.client.get(reverse("dashboard:instructor_courses"))
        self.assertEqual(response.status_code, 403)

class PublicPagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def test_public_pages_open_without_login(self):
        for name in ["how_it_works", "roles", "program_outcomes", "about"]:
            with self.subTest(page=name):
                response = self.client.get(reverse(f"dashboard:{name}"))
                self.assertEqual(response.status_code, 200)

    def test_program_outcomes_page_lists_outcomes_from_database(self):
        response = self.client.get(reverse("dashboard:program_outcomes"))
        self.assertContains(response, "PO1")
        self.assertContains(response, "Matematik, fen ve mühendislik bilgisi")

    def test_how_it_works_shows_the_worked_example(self):
        response = self.client.get(reverse("dashboard:how_it_works"))
        self.assertContains(response, "85,0")