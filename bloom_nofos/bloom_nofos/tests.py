from django.test import TestCase
from django.urls import reverse

from .utils import parse_docraptor_ip_addresses


class TextView(TestCase):
    def test_robots(self):
        response = self.client.get(reverse("robots_file"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get("Content-type"), "text/plain")
        self.assertContains(response, "User-Agent: *\nDisallow: /")


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
