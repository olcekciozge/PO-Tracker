from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from accounts.models import AuditLog
from accounts.security import _failed_key, is_login_blocked

User = get_user_model()
PASS = "AnExample-Strong-Password-123"


@override_settings(ACCOUNTS_LOGIN_FAILURE_LIMIT=3, ACCOUNTS_LOGIN_FAILURE_WINDOW=600)
class LoginSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("student", password=PASS, role=User.Role.STUDENT)

    def setUp(self):
        cache.clear()

    def test_correct_login_redirects_home(self):
        response = self.client.post(reverse("accounts:login"), {
            "username": "student", "password": PASS
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("accounts:home"))
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.Action.LOGIN).exists())

    def test_incorrect_password_does_not_log_in(self):
        response = self.client.post(reverse("accounts:login"), {
            "username": "student", "password": "wrong"
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "hatalı")

    def test_repeated_failures_are_rate_limited(self):
        url = reverse("accounts:login")
        for _ in range(3):
            self.assertEqual(self.client.post(url, {
                "username": "student", "password": "invalid"
            }).status_code, 200)
        response = self.client.post(url, {
            "username": "student", "password": PASS
        })
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "600")

    def test_successful_login_clears_failed_attempts(self):
        url = reverse("accounts:login")
        self.client.post(url, {"username": "student", "password": "bad"})
        self.assertEqual(self.client.post(url, {
            "username": "student", "password": PASS
        }).status_code, 302)
        request = RequestFactory().post(reverse("accounts:login"))
        self.assertFalse(is_login_blocked(request, "student"))

    def test_cache_key_does_not_contain_username(self):
        request = self.client.get(reverse("accounts:login")).wsgi_request
        key = _failed_key(request, "SensitiveUserName")
        self.assertNotIn("SensitiveUserName", key)
        self.assertTrue(key.startswith("accounts:login:failed:"))

    def test_unauthenticated_get_to_login_succeeds(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Giriş yap")

    def test_authenticated_get_to_login_redirects(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("accounts:home"))

    def test_external_next_url_not_used(self):
        response = self.client.post(
            reverse("accounts:login") + "?next=https://external.invalid/steal",
            {"username": "student", "password": PASS},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("accounts:home"))
