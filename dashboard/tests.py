from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class LandingPageTests(TestCase):
    def test_landing_page_is_public(self):
        response = self.client.get(reverse("dashboard:landing"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/landing.html")
        self.assertContains(response, "PO Tracker")
        self.assertContains(response, reverse("accounts:login"))

    def test_signed_in_user_is_sent_to_home(self):
        user = get_user_model().objects.create_user(username="elif", password="test-pass-123")
        self.client.force_login(user)
        response = self.client.get(reverse("dashboard:landing"))
        self.assertRedirects(response, reverse("accounts:home"), fetch_redirect_response=False)