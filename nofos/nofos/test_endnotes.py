from unittest import TestCase

from bs4 import BeautifulSoup

from .endnotes import analyze_endnotes, convert_bracketed_endnotes


class BracketedEndnotesTests(TestCase):
    def test_partial_ordered_citations_retain_generated_target_in_markdown(self):
        from .nofo_markdown import md

        soup = self.soup(
            "<p>Read [1] [2]</p><h1>Endnotes</h1><ol><li>[1]</li><li>[2] Source</li></ol>"
        )
        convert_bracketed_endnotes(soup)
        stored = md(str(soup))
        self.assertIn('id="endnote-manual-2"', stored)
        self.assertIn('href="#endnote-manual-2"', stored)

    def test_nested_citations_keep_targets_in_both_reference_orders(self):
        from .nofo_markdown import md

        for references in ("[1] [2]", "[2] [1]"):
            with self.subTest(references=references):
                soup = self.soup(
                    f"<p>Read {references}</p><h1>Endnotes</h1><ul><li>[1] Outer<ul><li>[2] Inner</li></ul></li></ul>"
                )
                convert_bracketed_endnotes(soup)
                stored = md(str(soup))
                for number in (1, 2):
                    self.assertEqual(
                        len(soup.find_all(id=f"endnote-manual-{number}")), 1
                    )
                    self.assertIn(f'id="endnote-manual-{number}"', stored)
                self.assertFalse(
                    any(
                        issue["code"] == "destination"
                        for issue in analyze_endnotes(soup)
                    )
                )

    def test_mixed_numbering_uses_document_order(self):
        native = '<a id="footnote-ref-8" href="#footnote-8">[1]</a>'
        citations = '<h1>Endnotes</h1><ol><li id="footnote-8">Native<a href="#footnote-ref-8">↑</a></li></ol><p>[2] Manual</p>'
        correct = self.soup(f"<p>{native} then [2]</p>{citations}")
        self.assertEqual(convert_bracketed_endnotes(correct), [])
        self.assertEqual(analyze_endnotes(correct), [])
        reversed_notes = self.soup(f"<p>[2] then {native}</p>{citations}")
        self.assertIn(
            "numbering", [i["code"] for i in convert_bracketed_endnotes(reversed_notes)]
        )

    def test_nested_numbering_uses_actual_text_order(self):
        soup = self.soup(
            "<ul><li><ul><li>First [1]</li></ul>Second [2]</li></ul><h1>Endnotes</h1><p>[1] A</p><p>[2] B</p>"
        )
        self.assertEqual(convert_bracketed_endnotes(soup), [])
        self.assertEqual(analyze_endnotes(soup), [])

    def soup(self, html):
        return BeautifulSoup(html, "html.parser")

    def test_void_elements_bookmarks_and_split_ids_survive(self):
        soup = self.soup(
            '<p><a id="bookmark"></a><img src="x"><span id="run">Before [<b>1</b>] after</span><br></p><h1>Endnotes</h1><p id="old-citation">[1] Text<img src="y"></p>'
        )
        convert_bracketed_endnotes(soup)
        self.assertEqual(len(soup.find_all("img")), 2)
        self.assertEqual(len(soup.find_all("br")), 1)
        for name in ("bookmark", "run", "old-citation"):
            self.assertEqual(len(soup.find_all(id=name)), 1)

    def test_nested_list_direct_reference_and_code_exclusion(self):
        soup = self.soup(
            "<ul><li>Direct [1]<ul><li>Child [2]</li></ul></li></ul><p><code>[1]</code></p><h7>Endnotes:</h7><p>[1] A</p><p>[2] B</p>"
        )
        convert_bracketed_endnotes(soup)
        self.assertEqual(len(soup.find_all("sup")), 2)
        self.assertEqual(soup.code.text, "[1]")
        self.assertIsNone(soup.code.a)

    def test_crossed_native_returns_warn(self):
        soup = self.soup(
            '<p><a id="footnote-ref-1" href="#footnote-1">[1]</a><a id="footnote-ref-2" href="#footnote-2">[2]</a></p><h1>Endnotes</h1><ol><li id="footnote-1">A<a href="#footnote-ref-2">↑</a></li><li id="footnote-2">B<a href="#footnote-ref-1">↑</a></li></ol>'
        )
        self.assertEqual(
            sum(i["code"] == "return-link" for i in analyze_endnotes(soup)), 2
        )

    def test_extremely_long_numeric_text_does_not_crash(self):
        soup = self.soup("<p>[" + "9" * 5000 + "]</p><h1>Endnotes</h1>")
        convert_bracketed_endnotes(soup)

    def test_unrelated_heading_links_and_years_are_not_notes(self):
        soup = self.soup(
            '<p>[2025] <a href="#endnotes">Endnotes</a> <a href="#reference-section">1</a></p><h1 id="endnotes">Endnotes</h1>'
        )
        self.assertEqual(analyze_endnotes(soup), [])

    def test_malformed_citation_markers(self):
        for marker in ("[0]", "[01]", "[ 1]", "[1 ]", "[1", "1]"):
            soup = self.soup(
                f"<p>Reference [1]</p><h1>Endnotes</h1><p>{marker} Source</p>"
            )
            self.assertIn(
                "malformed", [issue["code"] for issue in analyze_endnotes(soup)], marker
            )

    def test_split_formatting_preserved_and_conversion_idempotent(self):
        soup = self.soup(
            "<p>Read [<b>1</b>] now.</p><h1>Endnotes</h1><p>[1] Source <em>title</em>.</p>"
        )
        convert_bracketed_endnotes(soup)
        self.assertEqual(soup.p.get_text(), "Read [1] now.")
        self.assertEqual(soup.p.a.b.text, "1")
        self.assertEqual(soup.find(id="endnote-manual-1").em.text, "title")
        before = str(soup)
        convert_bracketed_endnotes(soup)
        self.assertEqual(str(soup), before)
        self.assertEqual(analyze_endnotes(soup), [])

    def test_gaps_link_but_warn(self):
        soup = self.soup("<p>A[1] B[3]</p><h1>Endnotes</h1><p>[1] A</p><p>[3] B</p>")
        issues = convert_bracketed_endnotes(soup)
        self.assertIn("numbering", [i["code"] for i in issues])
        self.assertEqual(len(soup.find_all("sup")), 2)
        self.assertIn("numbering", [i["code"] for i in analyze_endnotes(soup)])

    def test_duplicate_missing_empty_remain_unchanged(self):
        soup = self.soup(
            "<p>[1] [1] [2] [3]</p><h1>Endnotes</h1><p>[1] A</p><p>[2]</p>"
        )
        before = str(soup)
        codes = {i["code"] for i in convert_bracketed_endnotes(soup)}
        self.assertTrue({"duplicate", "empty", "missing-citation"} <= codes)
        self.assertEqual(str(soup), before)

    def test_continuation_and_following_section_boundaries(self):
        soup = self.soup(
            "<p>[1] [2]</p><h1>Endnotes</h1><p>[1]</p><ul><li>Continuation</li></ul><table><tr><td>Data</td></tr></table><p>[2]</p><h1>Other</h1><p>Not citation content</p>"
        )
        codes = [i["code"] for i in convert_bracketed_endnotes(soup)]
        self.assertIn("empty", codes)
        self.assertIsNotNone(soup.find(id="endnote-manual-1"))
        self.assertIsNone(soup.find(id="endnote-manual-2"))
        self.assertEqual(soup.table.get_text(), "Data")

    def test_native_relationships_and_conflicts(self):
        soup = self.soup(
            '<p><sup><a id="footnote-ref-8" href="#footnote-8">[1]</a></sup> [1] [2]</p><h1>Endnotes</h1><ol><li id="footnote-8">Native <a href="#footnote-ref-8">↑</a></li></ol><p>[1] Conflict</p><p>[2] Manual</p>'
        )
        issues = convert_bracketed_endnotes(soup)
        self.assertIn("conflict", [i["code"] for i in issues])
        self.assertEqual(soup.find(id="footnote-ref-8")["href"], "#footnote-8")
        self.assertIsNotNone(soup.find(id="endnote-manual-2"))
        self.assertIsNone(soup.find(id="endnote-manual-1"))

    def test_no_note_evidence_does_not_flag_brackets(self):
        soup = self.soup("<p>Array [1] and [3] values.</p>")
        self.assertEqual(convert_bracketed_endnotes(soup), [])
        self.assertIsNone(soup.a)

    def test_ambiguous_headings_and_bold_heading(self):
        for html in (
            "<p>[1]</p><p><b>Endnotes</b></p><p>[1] A</p>",
            "<p>[1]</p><h1>Endnotes</h1><p>[1] A</p><h1>Footnotes</h1>",
        ):
            soup = self.soup(html)
            self.assertIn(
                "heading", [i["code"] for i in convert_bracketed_endnotes(soup)]
            )
            self.assertIsNone(soup.a)

    def test_analysis_read_only_and_broken_link(self):
        soup = self.soup(
            '<p><a id="endnote-ref-manual-1" href="#endnote-manual-1">[1]</a></p><h1>Endnotes</h1>'
        )
        before = str(soup)
        self.assertIn("destination", [i["code"] for i in analyze_endnotes(soup)])
        self.assertEqual(str(soup), before)
