"""Regression coverage for IMPORT-067 and the Markdown/render boundary."""

import unittest
from io import BytesIO
from zipfile import ZipFile

import mammoth
import markdown
from bs4 import BeautifulSoup

from nofos.content_processing import (
    continue_table_row_numbering,
    process_document_content,
)
from nofos.nofo_markdown import md


def item(start=None):
    attr = f' start="{start}"' if start is not None else ""
    return f"<ol{attr}><li><strong>Item:</strong> Description.</li></ol>"


def row(content, other="Value"):
    return f"<tr><td>{content}</td><td>{other}</td></tr>"


def soup_for(rows):
    return BeautifulSoup("<table>" + "".join(rows) + "</table>", "html.parser")


def starts(soup):
    return [ol.get("start") for ol in soup.select("td:first-child > ol")]


class TableRowNumberingTests(unittest.TestCase):
    def test_eight_rows_survive_shared_import_markdown_and_render(self):
        soup = soup_for(
            ["<tr><th>Activity</th><th>Value</th></tr>"]
            + [row(item()) for _ in range(8)]
        )
        result = process_document_content(
            "<h1>Opportunity</h1><h2>Activities</h2>" + str(soup)
        )
        body = md(str(result.soup))
        self.assertIn("|", body)
        rendered = BeautifulSoup(
            markdown.markdown(body, extensions=["extra"]), "html.parser"
        )
        self.assertEqual(starts(rendered), [str(i) for i in range(1, 9)])
        self.assertEqual(len(rendered.select("td:first-child > ol > li > strong")), 8)
        self.assertEqual(
            [cell.get_text() for cell in rendered.select("td:nth-child(2)")],
            ["Value"] * 8,
        )

    def test_native_word_numbering_across_cells(self):
        # Public synthetic DOCX: one Word numbering instance split over eight cells.
        document = BytesIO()
        namespace = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        numbered = (
            '<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/>'
            '<w:numId w:val="1"/></w:numPr></w:pPr>'
            "<w:r><w:t>Item description</w:t></w:r></w:p>"
        )
        with ZipFile(document, "w") as archive:
            archive.writestr(
                "[Content_Types].xml",
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
            )
            archive.writestr(
                "word/document.xml",
                f'<w:document xmlns:w="{namespace}"><w:body>'
                '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Opportunity</w:t></w:r></w:p>'
                "<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Activity</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>Value</w:t></w:r></w:p></w:tc></w:tr>"
                + (
                    "<w:tr><w:tc>"
                    + numbered
                    + "</w:tc><w:tc><w:p><w:r><w:t>Value</w:t></w:r></w:p></w:tc></w:tr>"
                )
                * 8
                + "</w:tbl></w:body></w:document>",
            )
            archive.writestr(
                "word/styles.xml",
                f'<w:styles xmlns:w="{namespace}"><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style></w:styles>',
            )
            archive.writestr(
                "word/numbering.xml",
                f'<w:numbering xmlns:w="{namespace}"><w:abstractNum w:abstractNumId="1"><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/></w:lvl></w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="1"/></w:num></w:numbering>',
            )
        document.seek(0)
        html = mammoth.convert_to_html(document).value
        self.assertEqual(starts(BeautifulSoup(html, "html.parser")), [None] * 8)
        result = process_document_content(html)
        rendered = BeautifulSoup(
            markdown.markdown(md(str(result.soup)), extensions=["extra"]), "html.parser"
        )
        self.assertEqual(starts(rendered), [str(i) for i in range(1, 9)])

    def test_explicit_starts_anchor_continuation_and_repair_is_idempotent(self):
        soup = soup_for([row(item(4)), row(item()), row(item(1)), row(item())])
        continue_table_row_numbering(soup)
        self.assertEqual(starts(soup), ["4", "5", "1", "2"])
        before = str(soup)
        continue_table_row_numbering(soup)
        self.assertEqual(str(soup), before)

    def test_explicit_independent_lists_remain_independent(self):
        soup = soup_for([row(item(1)) for _ in range(8)])
        continue_table_row_numbering(soup)
        self.assertEqual(starts(soup), ["1"] * 8)

    def test_gap_ends_sequence_and_isolated_list_is_unchanged(self):
        soup = soup_for([row(item()), row(item()), row("Explanation"), row(item())])
        continue_table_row_numbering(soup)
        self.assertEqual(starts(soup), ["1", "2", None])

    def test_tables_and_other_columns_are_independent(self):
        soup = BeautifulSoup(
            str(soup_for([row(item(), item())] * 2)) * 2, "html.parser"
        )
        continue_table_row_numbering(soup)
        self.assertEqual(starts(soup), ["1", "2", "1", "2"])
        self.assertEqual(
            [ol.get("start") for ol in soup.select("td:nth-child(2) > ol")], [None] * 4
        )

    def test_unsupported_shapes_are_unchanged(self):
        for content in (
            "<ol><li>One</li><li>Two</li></ol>",
            "<ol><li>One<ul><li>Child</li></ul></li></ol>",
            "<ol reversed><li>One</li></ol>",
            '<ol type="a"><li>One</li></ol>',
            '<ol><li value="4">One</li></ol>',
            item("bad"),
            "<ol><li></li></ol>",
            item() + "<p>Explanation</p>",
            "<ul><li>Bullet</li></ul>",
        ):
            with self.subTest(content=content):
                soup = soup_for([row(content)] * 2)
                before = str(soup)
                continue_table_row_numbering(soup)
                self.assertEqual(str(soup), before)

    def test_source_word_lists_keep_authoritative_independent_starts(self):
        soup = soup_for(
            [row(item().replace("<ol>", '<ol data-nofo-source-list="true" type="1">'))]
            * 2
        )
        before = str(soup)
        continue_table_row_numbering(soup)
        self.assertEqual(str(soup), before)

    def test_merged_cells_are_unchanged(self):
        for attr in ('rowspan="2"', 'colspan="2"'):
            soup = soup_for(
                [row(item()).replace("<td>", f"<td {attr}>", 1), row(item())]
            )
            before = str(soup)
            continue_table_row_numbering(soup)
            self.assertEqual(str(soup), before)

    def test_header_list_keeps_html_in_markdown(self):
        html = (
            "<table><tr><th>"
            + item()
            + "</th><th>Value</th></tr>"
            + row(item())
            + "</table>"
        )
        rendered = BeautifulSoup(
            markdown.markdown(md(html), extensions=["extra"]), "html.parser"
        )
        self.assertIsNotNone(rendered.select_one("th > ol > li > strong"))
