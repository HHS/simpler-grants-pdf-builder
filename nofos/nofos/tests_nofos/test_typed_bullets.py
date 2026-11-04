import unittest

import markdown
from bs4 import BeautifulSoup

from nofos.content_processing import process_document_content, process_nofo_html
from nofos.nofo_markdown import md
from nofos.typed_bullets import repair_typed_bullets


class TypedBulletTests(unittest.TestCase):
    def test_adap_round_trip(self):
        lines = [
            "• Why a waiting list is necessary.",
            "• Waiting list criteria.",
            "• The estimated length of time they might remain on the waiting list.",
            "• Options for getting their medications in the meantime, including:",
            "o Recommendations or requirements for clients to work with a case manager.",
            'o <strong>Patient Assistance Programs (PAPs)</strong> applications and <a href="https://example.org">help applying</a>.',
            "o Other available options, such as the RWHAP Part A Local Pharmacy Assistance Program (LPAP).",
            "o Continuous assistance applying and re-applying for other programs, as needed.",
        ]
        for body in (
            "".join(f"<p>&#x20;{line}</p>" for line in lines),
            "<p>Clients on waiting lists should be given information about:<br>"
            + "<br>".join(lines)
            + "</p>",
        ):
            with self.subTest(body=body):
                soup = BeautifulSoup(body, "html.parser")
                soup, _ = process_nofo_html(soup, "h1")
                rendered = BeautifulSoup(
                    markdown.markdown(md(str(soup)), extensions=["extra"]),
                    "html.parser",
                )
                root_items = rendered.ul.find_all("li", recursive=False)
                self.assertEqual(len(root_items), 4)
                self.assertEqual(
                    len(root_items[-1].ul.find_all("li", recursive=False)), 4
                )
                self.assertEqual(rendered.a["href"], "https://example.org")
                self.assertEqual(
                    rendered.strong.text, "Patient Assistance Programs (PAPs)"
                )
                saved = str(soup)
                repair_typed_bullets(soup)
                self.assertEqual(str(soup), saved)

    def test_ambiguous_content_is_unchanged(self):
        for html in (
            "<p>• One isolated bullet</p>",
            "<p>o Ordinary text</p><p>o More ordinary text</p>",
            "<p>• First</p><h2>Boundary</h2><p>• Second</p>",
            "<ul><li>• First</li><li>• Second</li></ul>",
            "<table><tr><td><p>• First</p><p>• Second</p></td></tr></table>",
            '<p id="note">• First</p><p>• Second</p>',
            "<pre><p>• First</p><p>• Second</p></pre>",
            "<p>Not bullets<br>o Something</p>",
        ):
            with self.subTest(html=html):
                soup = BeautifulSoup(html, "html.parser")
                original = str(soup)
                repair_typed_bullets(soup)
                self.assertEqual(str(soup), original)

    def test_o_requires_colon_parent(self):
        soup = BeautifulSoup(
            "<p>• First</p><p>• Second</p><p>o Ordinary prose</p>", "html.parser"
        )
        repair_typed_bullets(soup)
        self.assertEqual(len(soup.ul.find_all("li")), 2)
        self.assertEqual(soup.p.text, "o Ordinary prose")

    def test_returns_to_root_with_inline_marker(self):
        soup = BeautifulSoup(
            "<p><strong>•</strong> First:</p><p>o Child</p><p>• Second:</p><p>o Another child</p><p>• Third</p>",
            "html.parser",
        )
        repair_typed_bullets(soup)
        self.assertEqual(len(soup.ul.find_all("li", recursive=False)), 3)
        self.assertEqual(len(soup.find_all("ul")), 3)
        self.assertNotIn("•", soup.text)

    def test_shared_import_entry_point(self):
        result = process_document_content(
            "<h1>Program</h1><h2>Waiting lists</h2><p>• Fair criteria</p><p>• Public input</p>"
        )
        self.assertIsNotNone(result.soup.find("ul"))

    def test_unrelated_line_breaks_are_preserved(self):
        soup = BeautifulSoup(
            "<p>Intro<br><em>Continued intro</em></p><p>• First</p><p>• Second</p><p>Closing<br>Continued closing</p>",
            "html.parser",
        )
        before = [str(p) for p in soup.find_all("p")][::3]
        repair_typed_bullets(soup)
        self.assertEqual([str(p) for p in soup.find_all("p")], before)

    def test_blank_paragraph_ends_group(self):
        soup = BeautifulSoup("<p>• First</p><p></p><p>• Second</p>", "html.parser")
        before = str(soup)
        repair_typed_bullets(soup)
        self.assertEqual(str(soup), before)

    def test_synthetic_word_import(self):
        from nofos.tests_nofos.test_word_lists import convert, docx, paragraph

        source = docx(
            "".join(
                paragraph(text, num=None)
                for text in (
                    "• Fair criteria",
                    "• Medication options:",
                    "o Case manager",
                    "o PAP applications",
                )
            )
        )
        # Ordinary paragraphs intentionally have no native Word numbering.
        soup, _ = convert(source)
        repair_typed_bullets(soup)
        self.assertEqual(len(soup.ul.find_all("li", recursive=False)), 2)
        self.assertEqual(len(soup.ul.find("ul").find_all("li")), 2)
