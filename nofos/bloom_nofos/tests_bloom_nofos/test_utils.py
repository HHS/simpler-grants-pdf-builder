import io
import zipfile
from types import SimpleNamespace
from unittest.mock import ANY, call, mock_open, patch

from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from ..utils import (
    generate_docx_download_response,
    is_grabzit_word_export_enabled,
    is_valid_docx,
    parse_docraptor_ip_addresses,
)


def make_docx(document_text="Synthetic document content"):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>',
        )
        archive.writestr(
            "word/document.xml",
            '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>{}</w:t></w:r></w:p></w:body></w:document>'.format(
                document_text
            ),
        )
    return output.getvalue()


VALID_DOCX = make_docx()


@override_settings(
    ALLOWED_HOSTS=["synthetic.example"],
    GRABZIT_APPLICATION_KEY="synthetic-key",
    GRABZIT_APPLICATION_SECRET="synthetic-secret",
    GRABZIT_WORD_EXPORT_ALLOWED_HOSTS=("synthetic.example",),
)
class DocxTransportTests(SimpleTestCase):
    def setUp(self):
        # Exercise the provider path without querying Constance's database backend.
        config_patch = patch(
            "constance.config",
            SimpleNamespace(PANDOC_WORD_EXPORT_ENABLED=False),
        )
        config_patch.start()
        self.addCleanup(config_patch.stop)
        self.request = RequestFactory().get("/", HTTP_HOST="synthetic.example")
        self.request.COOKIES = {
            "sessionid": "synthetic-session",
            "csrftoken": "synthetic-csrf",
        }

    def export(self):
        return generate_docx_download_response(
            request=self.request,
            export_url="https://synthetic.example/export",
            target_element="#download_target",
            filename_base="synthetic",
            tmp_name="synthetic",
        )

    @patch("bloom_nofos.utils.os.remove")
    @patch("bloom_nofos.utils.open", new_callable=mock_open, read_data=VALID_DOCX)
    @patch("bloom_nofos.utils.GrabzItClient.GrabzItClient")
    def test_tls_is_enabled_before_all_provider_operations(
        self, client_class, file_open, remove
    ):
        response = self.export()

        client_class.assert_called_once_with("synthetic-key", "synthetic-secret")
        self.assertEqual(
            client_class.return_value.method_calls,
            [
                call.UseSSL(True),
                call.SetCookie("sessionid", "synthetic.example", "synthetic-session"),
                call.SetCookie("csrftoken", "synthetic.example", "synthetic-csrf"),
                call.URLToDOCX("https://synthetic.example/export", ANY),
                call.SaveTo("/tmp/synthetic.docx"),
            ],
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, VALID_DOCX)

    @override_settings(GRABZIT_WORD_EXPORT_ALLOWED_HOSTS=("nofos.simpler.grants.gov",))
    @patch("bloom_nofos.utils.GrabzItClient.GrabzItClient")
    def test_unconfigured_host_is_blocked_before_provider_use(self, client_class):
        response = self.export()

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.content,
            b"Word export is not available in this environment.",
        )
        client_class.assert_not_called()

    @override_settings(GRABZIT_APPLICATION_KEY="")
    @patch("bloom_nofos.utils.GrabzItClient.GrabzItClient")
    def test_missing_credentials_are_blocked_before_provider_use(self, client_class):
        response = self.export()

        self.assertEqual(response.status_code, 503)
        client_class.assert_not_called()

    @patch("bloom_nofos.word_export.pandoc_download_response")
    @patch("bloom_nofos.utils.GrabzItClient.GrabzItClient")
    def test_local_export_never_calls_configured_vendor(self, client_class, local):
        with patch(
            "constance.config", SimpleNamespace(PANDOC_WORD_EXPORT_ENABLED=True)
        ):
            response = self.export()

        self.assertIs(response, local.return_value)
        local.assert_called_once_with(
            self.request,
            "https://synthetic.example/export",
            "#download_target",
            "synthetic",
        )
        client_class.assert_not_called()

    @patch("bloom_nofos.utils.os.remove")
    @patch("bloom_nofos.utils.open", new_callable=mock_open, read_data=b"")
    @patch("bloom_nofos.utils.GrabzItClient.GrabzItClient")
    def test_blank_provider_result_returns_error(self, client_class, file_open, remove):
        response = self.export()

        self.assertEqual(response.status_code, 502)
        self.assertEqual(
            response.content,
            b"Word export could not be completed. Please try again later.",
        )

    @patch("bloom_nofos.utils.os.remove")
    @patch("bloom_nofos.utils.open", new_callable=mock_open, read_data=make_docx(""))
    @patch("bloom_nofos.utils.GrabzItClient.GrabzItClient")
    def test_structurally_valid_but_empty_docx_returns_error(
        self, client_class, file_open, remove
    ):
        response = self.export()

        self.assertEqual(response.status_code, 502)

    @patch("bloom_nofos.utils.os.remove")
    @patch("bloom_nofos.utils.open", new_callable=mock_open, read_data=b"not-a-docx")
    @patch("bloom_nofos.utils.GrabzItClient.GrabzItClient")
    def test_malformed_provider_result_returns_error(
        self, client_class, file_open, remove
    ):
        response = self.export()

        self.assertEqual(response.status_code, 502)

    @patch("bloom_nofos.utils.os.remove")
    @patch("bloom_nofos.utils.GrabzItClient.GrabzItClient")
    def test_provider_failure_returns_error_and_cleans_up(self, client_class, remove):
        client_class.return_value.SaveTo.side_effect = RuntimeError(
            "synthetic provider failure"
        )

        response = self.export()

        self.assertEqual(response.status_code, 502)
        remove.assert_called_once_with("/tmp/synthetic.docx")

    def test_real_sdk_selects_https_before_first_cookie_request(self):
        class StopBeforeNetwork(Exception):
            pass

        # Intercept construction, before either connection can perform network I/O.
        with (
            patch(
                "GrabzIt.GrabzItClient.httpClient.HTTPConnection",
                side_effect=StopBeforeNetwork,
            ) as http,
            patch(
                "GrabzIt.GrabzItClient.httpClient.HTTPSConnection",
                side_effect=StopBeforeNetwork,
            ) as https,
        ):
            with self.assertRaises(StopBeforeNetwork):
                self.export()

        http.assert_not_called()
        https.assert_called_once_with("api.grabz.it", 443)


@override_settings(
    GRABZIT_APPLICATION_KEY="synthetic-key",
    GRABZIT_APPLICATION_SECRET="synthetic-secret",
    GRABZIT_WORD_EXPORT_ALLOWED_HOSTS=("nofos.simpler.grants.gov",),
)
class DocxSafeguardTests(SimpleTestCase):
    def test_export_is_enabled_only_for_exact_allowed_host(self):
        self.assertTrue(is_grabzit_word_export_enabled("nofos.simpler.grants.gov"))
        self.assertTrue(is_grabzit_word_export_enabled("NOFOS.SIMPLER.GRANTS.GOV."))
        self.assertFalse(is_grabzit_word_export_enabled("nofos.dev.simpler.grants.gov"))
        self.assertFalse(
            is_grabzit_word_export_enabled("nofos.simpler.grants.gov.attacker.example")
        )

    def test_docx_validation_requires_package_and_meaningful_text(self):
        self.assertTrue(is_valid_docx(VALID_DOCX))
        self.assertFalse(is_valid_docx(b""))
        self.assertFalse(is_valid_docx(b"not-a-docx"))
        self.assertFalse(is_valid_docx(make_docx("   ")))


class ParseDocraptorIPAddressesTests(TestCase):
    """Tests for the parse_docraptor_ip_addresses function."""

    def test_comma_separated_ips(self):
        input_string = "18.233.48.178,18.235.199.18,23.20.110.13"
        expected_output = ["18.233.48.178", "18.235.199.18", "23.20.110.13"]
        self.assertEqual(parse_docraptor_ip_addresses(input_string), expected_output)

    def test_space_separated_ips(self):
        input_string = "18.233.48.178 18.235.199.18 23.20.110.13"
        expected_output = ["18.233.48.178", "18.235.199.18", "23.20.110.13"]
        self.assertEqual(parse_docraptor_ip_addresses(input_string), expected_output)

    def test_newline_separated_ips(self):
        input_string = "18.233.48.178\n18.235.199.18\n23.20.110.13"
        expected_output = ["18.233.48.178", "18.235.199.18", "23.20.110.13"]
        self.assertEqual(parse_docraptor_ip_addresses(input_string), expected_output)

    def test_mixed_separators(self):
        input_string = "18.233.48.178, \n18.235.199.18, \n23.20.110.13"
        expected_output = ["18.233.48.178", "18.235.199.18", "23.20.110.13"]
        self.assertEqual(parse_docraptor_ip_addresses(input_string), expected_output)

    def test_extra_spaces_and_commas(self):
        input_string = " 18.233.48.178 ,  18.235.199.18 ,  23.20.110.13  "
        expected_output = ["18.233.48.178", "18.235.199.18", "23.20.110.13"]
        self.assertEqual(parse_docraptor_ip_addresses(input_string), expected_output)

    def test_empty_input(self):
        input_string = ""
        expected_output = []
        self.assertEqual(parse_docraptor_ip_addresses(input_string), expected_output)

    def test_only_separators(self):
        input_string = "  ,  \n  ,  "
        expected_output = []
        self.assertEqual(parse_docraptor_ip_addresses(input_string), expected_output)
