from django.test import SimpleTestCase

from nofos.readability_format import format_metric_number


class FormatMetricNumberTests(SimpleTestCase):
    def test_matches_panel_intl_number_format(self):
        # Expected strings come from Node's
        # Intl.NumberFormat("en-US", {maximumFractionDigits: 2}).format(value).
        cases = {
            10: "10",
            10.5: "10.5",
            13.32: "13.32",
            13.4950495: "13.5",
            13.495: "13.5",
            2.675: "2.68",
            0.125: "0.13",
            1.005: "1.01",
            1234.5: "1,234.5",
            1234567.891: "1,234,567.89",
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(format_metric_number(value), expected)
