from datetime import date

from django.test import TestCase

from ..exports import get_filename


class GetFilenameTest(TestCase):

    def test_both_dates_with_group(self):
        """
        When both start_date and end_date are provided and group is not empty,
        the filename should include both dates.
        """
        base_filename = "nb_export"
        group = "hrsa"
        start_date = date(2025, 4, 1)
        end_date = date(2025, 4, 30)
        expected = "nb_export_hrsa_2025-04-01_2025-04-30.csv"
        result = get_filename(base_filename, group, start_date, end_date)
        self.assertEqual(result, expected)

    def test_only_start_date_without_group(self):
        """
        When only start_date is provided and group is empty or None,
        the filename should include the provided date and use "user" as the group.
        """
        base_filename = "nb_export"
        group = None  # or group = ""
        start_date = date(2025, 4, 1)
        end_date = None
        expected = "nb_export_user_2025-04-01.csv"
        result = get_filename(base_filename, group, start_date, end_date)
        self.assertEqual(result, expected)

    def test_only_end_date_with_group(self):
        """
        When only end_date is provided and a group is specified,
        the filename should include the provided date.
        """
        base_filename = "nb_export"
        group = "acf"
        start_date = None
        end_date = date(2025, 5, 1)
        expected = "nb_export_acf_2025-05-01.csv"
        result = get_filename(base_filename, group, start_date, end_date)
        self.assertEqual(result, expected)

    def test_no_dates_without_group(self):
        """
        When neither start_date nor end_date is provided and group is empty,
        the filename should default to "user".
        """
        base_filename = "nb_export"
        group = ""
        start_date = None
        end_date = None
        expected = "nb_export_user.csv"
        result = get_filename(base_filename, group, start_date, end_date)
        self.assertEqual(result, expected)

    def test_no_dates_with_group(self):
        """
        When neither start_date nor end_date is provided and a group is specified,
        the filename should use that group.
        """
        base_filename = "nb_export"
        group = "staging"
        start_date = None
        end_date = None
        expected = "nb_export_staging.csv"
        result = get_filename(base_filename, group, start_date, end_date)
        self.assertEqual(result, expected)
