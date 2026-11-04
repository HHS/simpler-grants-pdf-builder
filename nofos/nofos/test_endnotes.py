from unittest import TestCase

from bs4 import BeautifulSoup

from .endnotes import (
    analyze_endnotes,
    convert_bracketed_endnotes,
    normalize_repeated_native_note_links,
    remove_duplicate_native_note_custom_marks,
)


class BracketedEndnotesTests(TestCase):
    def test_repeated_native_links_do_not_disrupt_mixed_manual_numbering(self):
        soup = self.soup(
            '<p><a id="endnote-ref-2" href="#endnote-2">[1]</a> then '
            '<a href="#endnote-2">1</a> then [2]</p>'
            '<h1>Endnotes</h1><ol><li id="endnote-2">Native '
            '<a href="#endnote-ref-2">↑</a></li></ol><p>[2] Manual</p>'
        )
        normalize_repeated_native_note_links(soup)
        self.assertEqual(convert_bracketed_endnotes(soup), [])
        self.assertEqual(analyze_endnotes(soup), [])

    def test_native_repair_leaves_ambiguous_targets_labels_and_id_collisions(self):
        for extra, second in (
            ('<li id="endnote-2">Duplicate target</li>', "[1]"),
            ("", "[2]"),
            ('<p id="endnote-ref-2">Unrelated bookmark</p>', "[1]"),
        ):
            with self.subTest(extra=extra, second=second):
                soup = self.soup(
                    '<p><a id="endnote-ref-2" href="#endnote-2">[1]</a>'
                    f'<a id="endnote-ref-2" href="#endnote-2">{second}</a></p>'
                    f'<ol><li id="endnote-2">Citation</li>{extra}</ol>'
                )
                before = str(soup)
                normalize_repeated_native_note_links(soup)
                self.assertEqual(str(soup), before)
                self.assertTrue(analyze_endnotes(soup))

    def test_explicit_repeated_native_links_get_unique_returns_and_survive_markdown(
        self,
    ):
        import markdown

        from .nofo_markdown import md

        soup = self.soup(
            '<h1>Program</h1><p><a id="endnote-ref-2" href="#endnote-2">[1]</a>'
            ' then <a id="endnote-ref-2" href="#endnote-2">[1]</a>'
            ' then <a href="#endnote-2">1</a> and <sup>1,2</sup>.</p>'
            '<h1>Endnotes</h1><ol><li id="endnote-2"><p>Citation '
            '<a href="#endnote-ref-2">↑</a></p></li></ol>'
        )
        normalize_repeated_native_note_links(soup)
        before = str(soup)
        self.assertIn("<sup>1,2</sup>", before)
        normalize_repeated_native_note_links(soup)
        self.assertEqual(str(soup), before)
        rendered = self.soup(markdown.markdown(md(str(soup)), extensions=["extra"]))
        refs = rendered.select('a[href="#endnote-2"]')
        self.assertEqual(len(refs), 3)
        self.assertEqual(len({a["id"] for a in refs}), 3)
        for anchor in refs:
            self.assertEqual(anchor.parent.name, "sup")
            self.assertIsNotNone(
                rendered.find(id="endnote-2").find("a", href="#" + anchor["id"])
            )
        self.assertIn("1,2", rendered.get_text())
        self.assertEqual(analyze_endnotes(rendered), [])

    def test_duplicate_word_custom_mark_is_removed_only_from_nested_superscript(self):
        soup = self.soup(
            '<p><sup><sup><a href="#endnote-2" id="endnote-ref-2">[1]</a>'
            '</sup>[1]</sup> <sup><a href="#endnote-3" '
            'id="endnote-ref-3">[2]</a></sup>[2]</p>'
            '<ol><li id="endnote-2"><p>[1] Source one '
            '<a href="#endnote-ref-2">↑</a></p></li></ol>'
        )

        self.assertEqual(remove_duplicate_native_note_custom_marks(soup), 1)
        self.assertEqual(soup.find("p").get_text(), "[1] [2][2]")
        self.assertEqual(
            soup.find(id="endnote-2").get_text(" ", strip=True), "Source one ↑"
        )
        self.assertEqual(remove_duplicate_native_note_custom_marks(soup), 0)

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
            "<p>[1] [2] [3]</p><h1>Endnotes</h1><p>[1] A</p><p>[1] B</p><p>[2]</p>"
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


class ReusedManualEndnoteTests(TestCase):
    def inspect(self, html):
        return analyze_endnotes(BeautifulSoup(html, "html.parser"))

    def test_reused_raw_references_import_with_individual_return_links(self):
        soup = BeautifulSoup(
            "<p>A[1] B[1]</p><h1>Endnotes</h1><p>[1] Source</p>", "html.parser"
        )
        self.assertEqual(convert_bracketed_endnotes(soup), [])
        refs = soup.select("sup a")
        self.assertEqual(len(refs), 2)
        self.assertEqual(len({a["id"] for a in refs}), 2)
        self.assertEqual(len({a["href"] for a in refs}), 1)
        for a in refs:
            self.assertIsNotNone(soup.find("a", href="#" + a["id"]))
        self.assertEqual(analyze_endnotes(soup), [])
        before = str(soup)
        convert_bracketed_endnotes(soup)
        self.assertEqual(str(soup), before)

    def test_group_collision_and_preserve_independent_missing_destination(self):
        html = (
            '<p><a id="endnote-ref-manual-1" href="#endnote-manual-1">[1]</a></p>' * 3
            + '<h1>Endnotes</h1><p id="endnote-manual-1">'
            '<a href="#endnote-ref-manual-1">[1]</a> Source '
            '<a href="#endnote-ref-manual-1">↑</a></p>'
        )
        issues = self.inspect(html)
        self.assertEqual(
            [i["message"] for i in issues],
            ["Endnote [1] has conflicting link IDs across 3 references."],
        )
        issues = self.inspect(html + '<a href="#endnote-missing">↑</a>')
        self.assertEqual(len(issues), 2)

    def test_independent_gaps_order_empty_and_duplicate_entries(self):
        for html, code in (
            (
                "<p>[1] [1] [3]</p><h1>Endnotes</h1><p>[1] A</p><p>[3] B</p>",
                "numbering",
            ),
            ("<p>[1] [1] [2]</p><h1>Endnotes</h1><p>[2] B</p><p>[1] A</p>", "order"),
            ("<p>[1] [1]</p><h1>Endnotes</h1><p>[1]</p>", "empty"),
            ("<p>[1]</p><h1>Endnotes</h1><p>[1] A</p><p>[1] B</p>", "duplicate"),
        ):
            with self.subTest(code=code):
                self.assertIn(code, {i["code"] for i in self.inspect(html)})

    def test_manual_links_to_different_targets_still_warn(self):
        issues = self.inspect(
            '<p><a id="endnote-ref-manual-1" href="#endnote-manual-1">[1]</a>'
            '<a id="endnote-ref-manual-1-b" href="#endnote-manual-other">[1]</a></p>'
            '<h1>Endnotes</h1><p id="endnote-manual-1">[1] A</p>'
            '<p id="endnote-manual-other">Other</p>'
        )
        self.assertIn("duplicate", {i["code"] for i in issues})

    def test_generic_target_collisions_and_two_independent_ids(self):
        html = (
            '<p><a href="#endnote-1">1</a></p>'
            '<ol><li id="endnote-1">A</li><li id="endnote-1">B</li></ol>'
        )
        issues = self.inspect(html)
        self.assertEqual(
            [i["message"] for i in issues],
            ["Endnote links have a conflicting destination ID."],
        )
        html += (
            '<p><a id="endnote-ref-2" href="#endnote-2">[2]</a></p>' * 2
            + '<ol><li id="endnote-2">C <a href="#endnote-ref-2">↑</a></li></ol>'
        )
        self.assertEqual(len(self.inspect(html)), 2)

    def test_reuse_preserves_missing_return_and_conflicting_labels(self):
        html = (
            '<p><a id="endnote-ref-manual-1" href="#endnote-manual-1">[1]</a>'
            '<a id="endnote-ref-manual-1-b" href="#endnote-manual-1">[1]</a></p>'
            '<h1>Endnotes</h1><p id="endnote-manual-1">'
            '<a href="#endnote-ref-manual-1">[1]</a> A</p>'
        )
        self.assertEqual([i["code"] for i in self.inspect(html)], ["return-link"])
        issues = self.inspect(html.replace(">[1]</a></p>", ">[2]</a></p>"))
        self.assertIn("conflict", {i["code"] for i in issues})

    def test_new_raw_reference_reuses_existing_manual_target(self):
        soup = BeautifulSoup("<p>[1]</p><h1>Endnotes</h1><p>[1] A</p>", "html.parser")
        convert_bracketed_endnotes(soup)
        extra = soup.new_tag("p")
        extra.string = "Again [1]"
        soup.h1.insert_before(extra)
        convert_bracketed_endnotes(soup)
        self.assertEqual(analyze_endnotes(soup), [])
        self.assertEqual(len(soup.select("sup a")), 2)
        self.assertEqual(len({a["href"] for a in soup.select("sup a")}), 1)

    def test_colliding_citation_id_does_not_gain_new_links(self):
        for identifier in ("endnote-manual-1", "source-bookmark"):
            with self.subTest(identifier=identifier):
                soup = BeautifulSoup(
                    f'<p>Read [1] again [1]</p><div id="{identifier}">Bookmark</div>'
                    f'<h1>Endnotes</h1><p id="{identifier}">[1] Source</p>',
                    "html.parser",
                )
                before = str(soup)
                convert_bracketed_endnotes(soup)
                self.assertEqual(str(soup), before)
                self.assertIsNone(soup.find("sup"))

    def test_manual_citation_collision_is_reported_without_incoming_links(self):
        issues = self.inspect(
            '<p>[1]</p><div id="endnote-manual-1">Bookmark</div>'
            '<h1>Endnotes</h1><p id="endnote-manual-1">[1] Source</p>'
        )
        self.assertEqual(sum(i["code"] == "destination" for i in issues), 1)

    def test_repeated_manual_references_survive_markdown_storage_and_reimport(self):
        import markdown

        from .nofo_markdown import md

        soup = BeautifulSoup(
            "<h1>Program</h1><p>First [1], repeated [1].</p><p>Again [1].</p>"
            "<h1>Endnotes</h1><p>[1] Source <em>title</em>.</p>",
            "html.parser",
        )
        self.assertEqual(convert_bracketed_endnotes(soup), [])
        rendered = BeautifulSoup(
            markdown.markdown(md(str(soup)), extensions=["extra"]), "html.parser"
        )
        references = rendered.select("sup a")
        self.assertEqual(len(references), 3)
        self.assertEqual(len({a["id"] for a in references}), 3)
        for reference in references:
            targets = rendered.find_all(id=reference["href"][1:])
            self.assertEqual(len(targets), 1)
            self.assertIsNotNone(targets[0].find("a", href="#" + reference["id"]))
        self.assertEqual(analyze_endnotes(rendered), [])
        before = str(rendered)
        self.assertEqual(convert_bracketed_endnotes(rendered), [])
        self.assertEqual(str(rendered), before)
