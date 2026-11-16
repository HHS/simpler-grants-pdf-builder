import unittest

from nofos.content_processing import process_document_content


class ApplicantNotes(unittest.TestCase):
    def parse(self, snippet):
        return process_document_content(
            "<h1>Eligibility</h1><h2>Who may apply</h2>" + snippet, builder_import=True
        ).soup

    def test_prefix_and_inline_markup(self):
        for prefix in ("PLEASE NOTE:", "Note –", "N.B."):
            with self.subTest(prefix=prefix):
                paragraph = self.parse(
                    f'<p>{prefix} Keep <em>this</em> <a href="/guide">link</a>.</p>'
                ).p
                self.assertEqual(paragraph.strong.get_text(), "Note:")
                self.assertEqual(paragraph.em.get_text(), "this")
                self.assertEqual(paragraph.a["href"], "/guide")
                self.assertEqual(
                    paragraph.get_text(" ", strip=True), "Note: Keep this link ."
                )

    def test_table_cell(self):
        soup = self.parse("<table><tr><td><p>N.B. Table note.</p></td></tr></table>")
        self.assertEqual(soup.select_one("td p strong").get_text(), "Note:")
        self.assertIn("Table note.", soup.td.get_text())

    def test_nonmatches(self):
        soup = self.parse(
            "<p>Note that this is ordinary.</p><p>An embedded PLEASE NOTE: stays.</p>"
        )
        self.assertEqual(
            [p.get_text() for p in soup.find_all("p")],
            ["Note that this is ordinary.", "An embedded PLEASE NOTE: stays."],
        )
        self.assertIsNone(soup.strong)

    def test_normalized_label_reaches_parsed_subsection(self):
        result = process_document_content(
            "<h1>Eligibility</h1><h2>Who may apply</h2><p>N.B. Keep this.</p>",
            builder_import=True,
        )
        body = result.sections[0]["subsections"][0]["body"]
        self.assertIn("<strong>Note:</strong>", str(body))
        self.assertIn("Keep this.", str(body))


if __name__ == "__main__":
    unittest.main(verbosity=2)
