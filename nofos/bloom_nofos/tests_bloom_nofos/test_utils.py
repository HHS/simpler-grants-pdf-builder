from types import SimpleNamespace
from unittest.mock import ANY, call, mock_open, patch

from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from ..utils import generate_docx_download_response, parse_docraptor_ip_addresses


@override_settings(
    ALLOWED_HOSTS=["synthetic.example"],
    GRABZIT_APPLICATION_KEY="synthetic-key",
    GRABZIT_APPLICATION_SECRET="synthetic-secret",
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
    @patch(
        "bloom_nofos.utils.open", new_callable=mock_open, read_data=b"synthetic-docx"
    )
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
        self.assertEqual(response.content, b"synthetic-docx")

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
