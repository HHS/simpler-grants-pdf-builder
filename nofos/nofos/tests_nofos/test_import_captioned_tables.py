"""Caption fidelity through the real import and configured rendering paths."""

from unittest.mock import patch

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from markdownify import MarkdownConverter
from martor.templatetags.martortags import safe_markdown

from nofos.models import Nofo
from nofos.nofo_markdown import NofoMarkdownConverter, md


class CaptionConverterTests(SimpleTestCase):
    def test_caption_does_not_change_header_or_body_rows(self):
        for cells in (
            "<th>Program</th><th>Amount</th>",
            "<td>Program</td><td>Amount</td>",
        ):
            for rows in (
                f"<tr>{cells}</tr><tr><td>Training</td><td>0</td></tr>",
                f"<tbody><tr>{cells}</tr><tr><td>Training</td><td>0</td></tr></tbody>",
                f"<thead><tr>{cells}</tr></thead><tbody><tr><td>Training</td><td>0</td></tr></tbody>",
            ):
                with self.subTest(rows=rows):
                    plain = md(f"<table>{rows}</table>")
                    captioned = md(f"<table><caption>Awards</caption>{rows}</table>")
                    self.assertEqual(captioned.strip(), "Awards\n\n" + plain.strip())
                    self.assertIsNotNone(
                        BeautifulSoup(safe_markdown(captioned), "html.parser").table
                    )

    def test_caption_formatting_and_links_survive(self):
        result = md(
            '<table><caption><strong>Awards</strong> <a href="https://example.com/awards">details</a></caption><tr><th>Program</th><th>Amount</th></tr><tr><td>Training</td><td>0</td></tr></table>'
        )
        rendered = BeautifulSoup(safe_markdown(result), "html.parser")
        self.assertEqual(rendered.strong.get_text(), "Awards")
        self.assertEqual(rendered.a["href"], "https://example.com/awards")
        self.assertIsNotNone(rendered.table)

    def test_first_row_detection_restores_source_caption(self):
        soup = BeautifulSoup(
            "<table><caption>Awards</caption><tr><th>Program</th></tr></table>",
            "html.parser",
        )
        before = str(soup)
        NofoMarkdownConverter().convert_tr(soup.tr, " Program |", set())
        self.assertEqual(str(soup), before)

    def test_caption_is_restored_when_row_conversion_fails(self):
        soup = BeautifulSoup(
            "<table><caption>Awards</caption><tr><th>Program</th></tr></table>",
            "html.parser",
        )
        before = str(soup)
        with patch.object(
            MarkdownConverter, "convert_tr", side_effect=RuntimeError("test failure")
        ):
            with self.assertRaises(RuntimeError):
                NofoMarkdownConverter().convert_tr(soup.tr, " Program |", set())
        self.assertEqual(str(soup), before)

    def test_merged_cells_keep_existing_html_fallback(self):
        result = md(
            '<table><caption>Awards</caption><tr><th colspan="2">Program</th></tr><tr><td>Training</td><td>0</td></tr></table>'
        )
        self.assertIn('<th colspan="2">', result)
        self.assertIn("<caption>", result)
        rendered = BeautifulSoup(safe_markdown(result), "html.parser")
        self.assertIsNotNone(rendered.table)
        self.assertIn("Awards", rendered.get_text())


@override_settings(DEBUG=False)
class CaptionImportTests(TestCase):
    prefix = "<p>Opdiv: CDC</p><p>Opportunity number: SYNTHETIC-CAPTION</p><p>Opportunity title: Synthetic caption test</p><h1>Opportunity</h1><h2>Funding</h2>"

    def setUp(self):
        user = get_user_model().objects.create_user(
            email="caption-test@example.com",
            password="local-test-only",
            group="bloom",
            force_password_reset=False,
        )
        self.client.force_login(user)

    def import_body(self, table):
        response = self.client.post(
            reverse("nofos:nofo_import"),
            {
                "nofo-import": SimpleUploadedFile(
                    "caption-test.html",
                    (self.prefix + table).encode(),
                    content_type="text/html",
                )
            },
        )
        self.assertEqual(response.status_code, 302)
        document = Nofo.objects.latest("created")
        body = document.sections.get().subsections.get().body
        return body, BeautifulSoup(safe_markdown(body), "html.parser")

    def test_captioned_and_uncaptioned_direct_and_wrapped_tables(self):
        for wrapper in (False, True):
            for caption in (False, True):
                for header in ("td", "th"):
                    with self.subTest(wrapper=wrapper, caption=caption, header=header):
                        table = (
                            "<table>"
                            + ("<caption>Awards</caption>" if caption else "")
                            + f"<tr><{header}>Program</{header}><{header}>Amount</{header}></tr><tr><td>Training</td><td>0</td></tr></table>"
                        )
                        if wrapper:
                            table = f'<figure class="table">{table}</figure>'
                        body, rendered = self.import_body(table)
                        self.assertIn("| --- | --- |", body)
                        self.assertIsNotNone(rendered.table)
                        self.assertEqual(
                            [
                                cell.get_text(strip=True)
                                for cell in rendered.table.find_all("td")
                            ][-2:],
                            ["Training", "0"],
                        )
                        if caption:
                            self.assertEqual(rendered.get_text().count("Awards"), 1)
                        # Wrapped tables deliberately bypass Builder's direct-
                        # table inference; this fix must not change that policy.
                        expected_header = (
                            ["", ""]
                            if wrapper and header == "td"
                            else ["Program", "Amount"]
                        )
                        self.assertEqual(
                            [
                                cell.get_text(strip=True)
                                for cell in rendered.table.find_all("th")
                            ],
                            expected_header,
                        )

    def test_one_cell_table_remains_a_callout(self):
        response = self.client.post(
            reverse("nofos:nofo_import"),
            {
                "nofo-import": SimpleUploadedFile(
                    "callout-test.html",
                    (
                        self.prefix
                        + "<table><tr><td><h3>Key facts</h3><p>Read this information.</p></td></tr></table>"
                    ).encode(),
                    content_type="text/html",
                )
            },
        )
        self.assertEqual(response.status_code, 302)
        document = Nofo.objects.latest("created")
        callout = document.sections.get().subsections.get(callout_box=True)
        self.assertEqual(callout.name, "Key facts")
        self.assertIn("Read this information.", callout.body)
