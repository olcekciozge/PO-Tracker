from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .selectors import student_po_profile

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

    def test_signed_in_instructor_is_sent_to_home(self):
        user = User.objects.create_user(username="hoca", password="test-pass-123", role=User.Role.INSTRUCTOR)
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