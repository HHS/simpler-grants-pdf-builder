"""Defensive repair of reported HTML; not a reproduction of the original DOCX import."""

from unittest import TestCase

import markdown
from bs4 import BeautifulSoup

from nofos.content_processing import process_document_content, process_nofo_html
from nofos.endnotes import inline_native_note_return_links
from nofos.nofo_markdown import md


class NativeNoteReturnLinkTests(TestCase):
    def test_moves_matching_link_and_preserves_citation_and_link_attributes(self):
        for kind in ("endnote", "footnote"):
            with self.subTest(kind=kind):
                soup = BeautifulSoup(
                    f'<ol><li id="{kind}-2"><p>First paragraph.</p>'
                    "<p>Second <em>citation</em> "
                    '<a href="https://example.org/source">source</a>.</p>'
                    f'<p> \n<a href="#{kind}-ref-2" aria-label="Return" '
                    'class="backlink">↑</a> \n</p></li></ol>',
                    "html.parser",
                )
                note = soup.find("li")
                original_paragraphs = note.find_all("p")[:2]
                original_link = note.find_all("a")[-1]
                original_citation = str(original_paragraphs[-1])
                self.assertEqual(inline_native_note_return_links(soup), 1)
                self.assertEqual(note.find_all("p"), original_paragraphs)
                self.assertIs(original_link.parent, original_paragraphs[-1])
                self.assertEqual(original_link["aria-label"], "Return")
                self.assertEqual(original_link["class"], ["backlink"])
                self.assertEqual(
                    str(original_paragraphs[-1]),
                    original_citation.replace("</p>", f" {original_link}</p>"),
                )
                repaired = str(soup)
                self.assertEqual(inline_native_note_return_links(soup), 0)
                self.assertEqual(str(soup), repaired)

    def test_leaves_near_matches_unchanged(self):
        cases = {
            "explanation": '<p>Explanation <a href="#endnote-ref-2">↑</a></p>',
            "image": '<p><img src="figure.png"><a href="#endnote-ref-2">↑</a></p>',
            "nested_image": '<p><a href="#endnote-ref-2"><img src="x">↑</a></p>',
            "break": '<p><br><a href="#endnote-ref-2">↑</a></p>',
            "empty_element": '<p><span></span><a href="#endnote-ref-2">↑</a></p>',
            "comment": '<p><!--keep--><a href="#endnote-ref-2">↑</a></p>',
            "link_comment": '<p><a href="#endnote-ref-2">↑<!--keep--></a></p>',
            "two_links": '<p><a href="#endnote-ref-2">↑</a><a href="#other">more</a></p>',
            "wrong_note": '<p><a href="#endnote-ref-3">↑</a></p>',
            "wrong_type": '<p><a href="#footnote-ref-2">↑</a></p>',
            "other_label": '<p><a href="#endnote-ref-2">Return</a></p>',
            "target_id": '<p id="bookmark"><a href="#endnote-ref-2">↑</a></p>',
            "paragraph_class": '<p class="keep"><a href="#endnote-ref-2">↑</a></p>',
            "formatted_link": '<p><a href="#endnote-ref-2"><em>↑</em></a></p>',
            "following_content": '<p><a href="#endnote-ref-2">↑</a></p><p>More.</p>',
        }
        for name, tail in cases.items():
            with self.subTest(name=name):
                soup = BeautifulSoup(
                    f'<ol><li id="endnote-2"><p>Citation.</p>{tail}</li></ol>',
                    "html.parser",
                )
                before = str(soup)
                self.assertEqual(inline_native_note_return_links(soup), 0)
                self.assertEqual(str(soup), before)

    def test_requires_native_numeric_id_and_adjacent_text_paragraph(self):
        for note_id, citation, suffix, wrapper in (
            ("endnote-manual-2", "<p>Citation.</p>", "", "div"),
            ("endnote-ref-2", "<p>Citation.</p>", "", "div"),
            ("endnote-custom", "<p>Citation.</p>", "", "div"),
            (None, "<p>Citation.</p>", "", "div"),
            ("endnote-2", "", "", "div"),
            ("endnote-2", "<p> </p>", "", "div"),
            ("endnote-2", "<div>Citation.</div>", "", "div"),
            ("endnote-2", "<p>Citation.</p>Extra", "", "div"),
            ("endnote-2", "<p>Citation.</p>", "Extra", "div"),
            ("endnote-2", "<p>Citation.</p>", "", "pre"),
            ("endnote-2", "<p>Citation.</p>", "", "code"),
        ):
            with self.subTest(
                note_id=note_id, citation=citation, suffix=suffix, wrapper=wrapper
            ):
                attr = f' id="{note_id}"' if note_id else ""
                soup = BeautifulSoup(
                    f"<{wrapper}><ol><li{attr}>{citation}"
                    f'<p><a href="#endnote-ref-2">↑</a></p>{suffix}'
                    f"</li></ol></{wrapper}>",
                    "html.parser",
                )
                before = str(soup)
                self.assertEqual(inline_native_note_return_links(soup), 0)
                self.assertEqual(str(soup), before)

    def test_already_inline_and_nested_note_do_not_merge_outer_paragraphs(self):
        soup = BeautifulSoup(
            '<ol><li id="endnote-2"><p>Citation <a href="#endnote-ref-2">↑</a></p>'
            '<ol><li id="endnote-3"><p>Nested citation.</p>'
            '<p><a href="#endnote-ref-3">↑</a></p></li></ol></li></ol>',
            "html.parser",
        )
        self.assertEqual(inline_native_note_return_links(soup), 1)
        self.assertEqual(
            len(soup.find(id="endnote-2").find_all("p", recursive=False)), 1
        )
        self.assertEqual(len(soup.find(id="endnote-3").find_all("p")), 1)

    def test_shared_import_keeps_repaired_structure_through_markdown(self):
        result = process_document_content(
            "<h1>Program</h1><p>Claim "
            '<a id="endnote-ref-2" href="#endnote-2">[1]</a>.</p>'
            '<h1>Endnotes</h1><ol><li id="endnote-2"><p>First paragraph.</p>'
            "<p>Second <em>citation</em>.</p>"
            '<p><a href="#endnote-ref-2">↑</a></p></li></ol>'
        )
        body = "\n".join(
            md("".join(str(tag) for tag in subsection["body"]))
            for section in result.sections
            for subsection in section["subsections"]
        )
        rendered = BeautifulSoup(markdown.markdown(body), "html.parser")
        note = rendered.find(id="endnote-2")
        paragraphs = note.find_all("p", recursive=False)
        self.assertEqual(len(paragraphs), 2)
        self.assertEqual(paragraphs[0].get_text(strip=True), "First paragraph.")
        self.assertIs(note.find("a", href="#endnote-ref-2").parent, paragraphs[-1])
        self.assertIsNotNone(rendered.find("a", id="endnote-ref-2", href="#endnote-2"))
        self.assertIsNotNone(paragraphs[-1].find("em"))

    def test_repair_precedes_generic_cleanup_that_erases_extra_elements(self):
        soup = BeautifulSoup(
            '<h1>Endnotes</h1><ol><li id="endnote-2"><p>Citation.</p>'
            '<p><span></span><a href="#endnote-ref-2">↑</a></p></li></ol>',
            "html.parser",
        )
        processed, _ = process_nofo_html(soup, "h1")
        self.assertEqual(len(processed.find("li").find_all("p")), 2)
