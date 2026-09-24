"""USWDS government website banner on app pages, not on NOFO documents."""

from constance.test import override_config
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from nofos.models import Nofo

User = get_user_model()

BANNER_TEXT = "An official website of the United States government"


class GovBannerTests(TestCase):
    def assertBannerAboveHeader(self, response, status_code=200):
        self.assertContains(response, BANNER_TEXT, count=1, status_code=status_code)
        self.assertContains(
            response, 'aria-controls="gov-banner-default"', status_code=status_code
        )
        self.assertContains(
            response, "/static/img/us_flag_small.png", status_code=status_code
        )
        html = response.content.decode()
        self.assertLess(html.index('class="usa-banner"'), html.index("usa-header"))

    def test_signed_out_login_page_has_banner(self):
        self.assertBannerAboveHeader(self.client.get(reverse("users:login")))

    def test_readability_page_has_banner_whether_pilot_is_on_or_off(self):
        url = reverse("pdf_readability")
        self.assertBannerAboveHeader(self.client.get(url), status_code=503)
        with override_config(HHS_NOFO_PDF_METRICS_PILOT_ENABLED=True):
            self.assertBannerAboveHeader(self.client.get(url))

    def test_signed_in_pages_have_banner(self):
        User.objects.create_user(
            email="banner-test@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client.login(email="banner-test@example.com", password="testpass123")
        self.assertBannerAboveHeader(self.client.get(reverse("nofos:nofo_index")))
        self.assertBannerAboveHeader(self.client.get(reverse("users:user_view")))

    def test_nofo_document_view_has_no_banner(self):
        User.objects.create_user(
            email="banner-test@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client.login(email="banner-test@example.com", password="testpass123")
        nofo = Nofo.objects.create(
            title="Test NOFO",
            short_name="test-nofo",
            number="NOFO-TEST-001",
            opdiv="TEST",
            group="bloom",
        )
        response = self.client.get(reverse("nofos:nofo_view", kwargs={"pk": nofo.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, BANNER_TEXT)
