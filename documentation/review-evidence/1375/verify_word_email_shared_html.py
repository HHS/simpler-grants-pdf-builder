import unittest
from html import escape

from nofos.content_processing import process_document_content


class WordEmailLinkChecks(unittest.TestCase):
    def check_target(self, href, label, expected):
        html = (
            "<h1>Eligibility</h1><h2>Contact</h2>"
            f'<p><a href="{escape(href, quote=True)}">{escape(label)}</a></p>'
        )
        result = process_document_content(html, builder_import=True)
        body = result.sections[0]["subsections"][0]["body"]
        link = body[0].a
        self.assertEqual(link["href"], expected)
        self.assertEqual(link.get_text(), label)

    def test_repair_matching_file_targets(self):
        for href, label in (
            ("file://///server/share/contact@example.test", "contact@example.test"),
            ("file:///C:/contacts/user%2Bteam%40example.test", "user+team@example.test"),
        ):
            with self.subTest(href=href):
                self.check_target(href, label, "mailto:" + label)

    def test_preserve_existing_email_and_web_links(self):
        for href in (
            "mailto:contact@example.test",
            "https://example.test/contact@example.test",
        ):
            with self.subTest(href=href):
                self.check_target(href, "contact@example.test", href)

    def test_preserve_ambiguous_file_targets(self):
        for suffix, label in (
            ("other@example.test", "contact@example.test"),
            ("contact@example.test", "Contact us"),
            ("contact@example.test?download=1", "contact@example.test"),
            ("contact@example.test#bookmark", "contact@example.test"),
            ("contact@example.test.pdf", "contact@example.test"),
        ):
            href = "file://///server/share/" + suffix
            with self.subTest(href=href, label=label):
                self.check_target(href, label, href)


if __name__ == "__main__":
    unittest.main(verbosity=2)
