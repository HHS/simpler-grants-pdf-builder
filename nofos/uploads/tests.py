from django.test import SimpleTestCase
from .utils import get_display_size


class GetDisplaySizeTests(SimpleTestCase):

    def test_bytes(self):
        self.assertEqual(get_display_size(0), "0 B")
        self.assertEqual(get_display_size(512), "512 B")
        self.assertEqual(get_display_size(1023), "1023 B")

    def test_kilobytes(self):
        self.assertEqual(get_display_size(1024), "1.0 KB")
        self.assertEqual(get_display_size(1536), "1.5 KB")
        self.assertEqual(get_display_size(10 * 1024), "10.0 KB")

    def test_megabytes(self):
        self.assertEqual(get_display_size(1024 * 1024), "1.0 MB")
        self.assertEqual(get_display_size(5 * 1024 * 1024), "5.0 MB")
        self.assertEqual(get_display_size(3145728), "3.0 MB")  # 3 MB
