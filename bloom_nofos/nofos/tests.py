from django.test import TestCase

from .utils import match_view_url


class MatchUrlTests(TestCase):
    def test_match_valid_urls(self):
        """
        Test the match_url function with valid URLs.
        """
        self.assertTrue(match_view_url("/nofos/123"))
        self.assertTrue(match_view_url("/nofos/1"))
        self.assertTrue(match_view_url("/nofos/0"))

    def test_match_invalid_urls(self):
        """
        Test the match_url function with invalid URLs.
        """
        self.assertFalse(match_view_url("/nofos"))
        self.assertFalse(match_view_url("/nofos/"))
        self.assertFalse(match_view_url("/nofos/abc"))
        self.assertFalse(match_view_url("/nofos/123/456"))
        self.assertFalse(match_view_url("/nofos/1/2"))
