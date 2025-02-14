import os

import mammoth
from bs4 import BeautifulSoup
from django.test import TestCase
from nofos.utils import style_map_manager


class TestDocxConversion(TestCase):

    def setUp(self):
        # Path to the .docx fixture file
        self.docx_file_path = os.path.join(
            os.path.dirname(__file__), "..", "fixtures", "docx", "lists.docx"
        )

    def test_docx_to_html_conversion(self):
        """Test that the lists in this docx file are correctly converted to HTML lists"""
        with open(self.docx_file_path, "rb") as docx_file:
            doc_to_html_result = mammoth.convert_to_html(
                docx_file, style_map=style_map_manager.get_style_map()
            )

            # Extract the HTML
            html_content = doc_to_html_result.value

            # Parse with BeautifulSoup
            soup = BeautifulSoup(html_content, "html.parser")

            # 7 uls because nested lists create a new ul
            uls = soup.find_all("ul")
            self.assertEqual(len(uls), 11, "Expected 11 <ul> elements in the HTML")

            # 14 <li> elements
            lis = soup.select("li")
            self.assertEqual(len(lis), 20, "There should be exactly 20 list items")

            # 4 <li> elements
            nested_lis = soup.select("ul > li > ul > li")
            self.assertEqual(
                len(nested_lis), 8, "There should be exactly 8 nested list items"
            )

            # Print warnings if any exist in the conversion result
            warnings = doc_to_html_result.messages
            self.assertEqual(len(warnings), 0, f"Unexpected warnings: {warnings}")
