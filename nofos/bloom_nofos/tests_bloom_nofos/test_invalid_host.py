"""Invalid hosts must remain rejected without breaking error-page rendering."""

from unittest.mock import patch

from bloom_nofos.context_processors import template_context
from bloom_nofos.views import server_error
from django.test import Client, RequestFactory, SimpleTestCase, override_settings


@override_settings(
    DEBUG=False,
    ALLOWED_HOSTS=["builder.example"],
    GRABZIT_WORD_EXPORT_ALLOWED_HOSTS=["builder.example", "invalid.example"],
    GRABZIT_APPLICATION_KEY="synthetic-key",
    GRABZIT_APPLICATION_SECRET="synthetic-secret",
)
class InvalidHostTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        banner = patch(
            "bloom_nofos.context_processors.get_changelog_banner", return_value=None
        )
        banner.start()
        self.addCleanup(banner.stop)

    def test_invalid_hosts_receive_400_through_real_middleware(self):
        client = Client(raise_request_exception=False)
        for host in ("invalid.example", "bad host", "192.0.2.1"):
            for path in ("/", "/favicon.ico", "/filefuns.php"):
                with self.subTest(host=host, path=path):
                    response = client.get(path, HTTP_HOST=host)
                    self.assertEqual(response.status_code, 400)

    def test_invalid_host_disables_export_without_consulting_provider_settings(self):
        request = self.factory.get("/", HTTP_HOST="invalid.example")
        with patch(
            "bloom_nofos.context_processors.is_grabzit_word_export_enabled"
        ) as enabled:
            self.assertFalse(template_context(request)["GRABZIT_WORD_EXPORT_ENABLED"])
        enabled.assert_not_called()

    def test_valid_host_keeps_export_available(self):
        request = self.factory.get("/", HTTP_HOST="builder.example")
        self.assertTrue(template_context(request)["GRABZIT_WORD_EXPORT_ENABLED"])

    def test_missing_request_disables_export(self):
        self.assertFalse(template_context(None)["GRABZIT_WORD_EXPORT_ENABLED"])

    def test_server_error_can_render_with_invalid_host(self):
        request = self.factory.get("/", HTTP_HOST="invalid.example")
        response = server_error(request)
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"500", response.content)
