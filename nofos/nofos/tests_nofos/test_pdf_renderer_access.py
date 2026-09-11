from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse

from nofos.middleware import NofosLoginRequiredMiddleware


class PDFRendererAccessTest(SimpleTestCase):
    """Document the anonymous HTML fetch boundary, not production IP settings."""

    path = "/nofos/00000000-0000-0000-0000-000000000001"
    allowed_ip = "192.0.2.10"

    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = NofosLoginRequiredMiddleware(
            lambda request: HttpResponse("NOFO HTML")
        )

    def fetch(self, forwarded_for=None, secure=True, user=None):
        headers = {}
        if forwarded_for is not None:
            headers["HTTP_X_FORWARDED_FOR"] = forwarded_for
        request = self.factory.get(self.path, secure=secure, **headers)
        request.user = user if user is not None else AnonymousUser()
        with patch(
            "nofos.middleware.config",
            SimpleNamespace(DOCRAPTOR_IPS=self.allowed_ip),
        ):
            return self.middleware(request)

    def test_exact_allowlisted_ip_over_https_reaches_html(self):
        response = self.fetch(self.allowed_ip)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"NOFO HTML")

    def test_missing_unlisted_and_chained_ips_redirect_to_login(self):
        # A proxy chain is not an exact allowlist match, even if it contains one.
        for forwarded_for in (None, "192.0.2.11", "192.0.2.10, 10.0.0.1"):
            with self.subTest(forwarded_for=forwarded_for):
                response = self.fetch(forwarded_for)

                self.assertEqual(response.status_code, 302)
                self.assertEqual(
                    response["Location"], "/users/login/?next=" + self.path
                )

    def test_allowlisted_ip_without_https_redirects_to_login(self):
        response = self.fetch(self.allowed_ip, secure=False)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/users/login/?next=" + self.path)

    def test_authenticated_user_does_not_need_renderer_ip(self):
        user = SimpleNamespace(is_authenticated=True, force_password_reset=False)
        response = self.fetch(user=user)

        self.assertEqual(response.status_code, 200)

    def test_authenticated_password_reset_requirement_is_preserved(self):
        user = SimpleNamespace(is_authenticated=True, force_password_reset=True)
        response = self.fetch(user=user)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"], reverse("users:user_force_password_reset")
        )
