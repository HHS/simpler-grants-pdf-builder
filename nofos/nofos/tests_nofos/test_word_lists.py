"""Synthetic OOXML exercises the real Mammoth numbering-preservation boundary."""

from io import BytesIO
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

import mammoth
from bs4 import BeautifulSoup
from django.test import SimpleTestCase

from nofos.import_transforms import (
    APPLICATION_CHECKLIST_CHILD_STYLE_MAP,
    transform_word_document,
)
from nofos.word_lists import SOURCE_LIST_ATTR, WORD_NS, prepare_word_lists


def paragraph(text, *, num="1", level=0, style=None, indent=None, runs=None):
    properties = ""
    if style:
        properties += f'<w:pStyle w:val="{style}"/>'
    if num is not None:
        properties += (
            f'<w:numPr><w:ilvl w:val="{level}"/><w:numId w:val="{num}"/></w:numPr>'
        )
    if indent is not None:
        properties += f'<w:ind w:left="{indent}"/>'
    return f"<w:p><w:pPr>{properties}</w:pPr>{runs or f'<w:r><w:t>{escape(text)}</w:t></w:r>'}</w:p>"


def level(index, fmt="decimal", start=1, *, restart=None, text=None):
    restart_xml = "" if restart is None else f'<w:lvlRestart w:val="{restart}"/>'
    return (
        f'<w:lvl w:ilvl="{index}"><w:start w:val="{start}"/>'
        f'<w:numFmt w:val="{fmt}"/><w:lvlText w:val="{text or f"%{index + 1}."}"/>'
        f'{restart_xml}<w:pPr><w:ind w:left="{720 * (index + 1)}"/></w:pPr></w:lvl>'
    )


def docx(body, *, levels=None, numbers=None, styles="", extra=None):
    levels = levels if levels is not None else level(0)
    numbers = numbers or '<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>'
    parts = {
        "[Content_Types].xml": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/></Types>',
        "_rels/.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        "word/document.xml": f'<w:document xmlns:w="{WORD_NS}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body>{body}</w:body></w:document>',
        "word/styles.xml": f'<w:styles xmlns:w="{WORD_NS}">{styles}</w:styles>',
        "word/numbering.xml": f'<w:numbering xmlns:w="{WORD_NS}"><w:abstractNum w:abstractNumId="0">{levels}</w:abstractNum>{numbers}</w:numbering>',
        **(extra or {}),
    }
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for name, data in parts.items():
            archive.writestr(name, data)
    output.seek(0)
    return output


def convert(source):
    copied, plan = prepare_word_lists(source)
    converted = mammoth.convert_to_html(
        copied,
        style_map=plan.style_map,
        transform_document=transform_word_document,
    )
    return BeautifulSoup(plan.restore_html(converted.value), "html.parser"), plan


class NativeWordListsTests(SimpleTestCase):
    def test_bullets_continue_across_numbering_instances(self):
        numbers = "".join(
            f'<w:num w:numId="{n}"><w:abstractNumId w:val="0"/></w:num>'
            for n in (1, 2, 3)
        )
        soup, _ = convert(
            docx(
                paragraph("First", num="1")
                + paragraph("Second", num="2")
                + paragraph("Child", num="3", level=1)
                + paragraph("Third", num="1")
                + paragraph("Boundary", num=None)
                + paragraph("Separate", num="2"),
                numbers=numbers,
                levels=level(0, "bullet") + level(1, "bullet"),
            )
        )
        roots = soup.find_all("ul", recursive=False)
        self.assertEqual(len(roots), 2)
        self.assertEqual(
            [li.get_text() for li in roots[0].find_all("li", recursive=False)],
            ["First", "SecondChild", "Third"],
        )
        self.assertEqual(roots[0].select_one("li > ul > li").get_text(), "Child")
        self.assertEqual(roots[1].get_text(), "Separate")
        self.assertEqual(soup.p.get_text(), "Boundary")

    def test_nonzero_letter_roman_decimal_tree_has_no_empty_parent_items(self):
        soup, _ = convert(
            docx(
                paragraph("Parent", level=1)
                + paragraph("Child", level=2)
                + paragraph("Criterion", level=3)
                + paragraph("Next parent", level=1),
                levels=level(1, "lowerLetter") + level(2, "lowerRoman") + level(3),
            )
        )
        self.assertEqual([el["type"] for el in soup.find_all("ol")], ["a", "i", "1"])
        self.assertEqual(len(soup.find_all("li")), 4)
        self.assertEqual(len(soup.ol.find_all("li", recursive=False)), 2)
        self.assertTrue(
            all(el.has_attr(SOURCE_LIST_ATTR) for el in soup.find_all("ol"))
        )

    def test_all_supported_marker_formats(self):
        for fmt, marker in (
            ("decimal", "1"),
            ("lowerLetter", "a"),
            ("upperLetter", "A"),
            ("lowerRoman", "i"),
            ("upperRoman", "I"),
            ("bullet", None),
        ):
            with self.subTest(fmt=fmt):
                soup, plan = convert(docx(paragraph("Item"), levels=level(0, fmt)))
                listing = soup.find(["ul", "ol"])
                self.assertEqual(listing.name, "ul" if marker is None else "ol")
                self.assertEqual(listing.get("type"), marker)
                self.assertEqual(plan.warnings, [])

    def test_mixed_ordered_bullet_descendants(self):
        soup, _ = convert(
            docx(
                paragraph("Parent")
                + paragraph("Bullet", level=1)
                + paragraph("Roman", level=2),
                levels=level(0, "lowerLetter")
                + level(1, "bullet")
                + level(2, "upperRoman"),
            )
        )
        self.assertEqual(soup.ol.ul.ol["type"], "I")
        self.assertEqual(soup.ol.ul.parent.name, "li")

    def test_continued_numbering_after_unrelated_prose_uses_explicit_start(self):
        soup, _ = convert(
            docx(
                paragraph("First")
                + paragraph("Unrelated", num=None)
                + paragraph("Second")
            )
        )
        self.assertEqual(len(soup.find_all("ol")), 2)
        self.assertEqual(soup.find_all("ol")[1]["start"], "2")
        self.assertEqual(soup.find("p").get_text(), "Unrelated")

    def test_numbering_instances_do_not_merge(self):
        soup, _ = convert(
            docx(
                paragraph("First") + paragraph("Restart", num="2"),
                numbers='<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num><w:num w:numId="2"><w:abstractNumId w:val="0"/></w:num>',
            )
        )
        self.assertEqual(len(soup.find_all("ol")), 2)
        self.assertTrue(all(not el.has_attr("start") for el in soup.find_all("ol")))

    def test_start_override_and_full_level_override(self):
        soup, _ = convert(
            docx(
                paragraph("Override"),
                numbers='<w:num w:numId="1"><w:abstractNumId w:val="0"/><w:lvlOverride w:ilvl="0"><w:startOverride w:val="4"/>'
                + level(0, "upperLetter", 2)
                + "</w:lvlOverride></w:num>",
            )
        )
        self.assertEqual(soup.ol["type"], "A")
        self.assertEqual(soup.ol["start"], "4")

    def test_nested_level_restarts_after_parent(self):
        soup, _ = convert(
            docx(
                paragraph("A")
                + paragraph("A child", level=1)
                + paragraph("B")
                + paragraph("B child", level=1),
                levels=level(0, "upperLetter") + level(1, "lowerRoman"),
            )
        )
        self.assertEqual(len(soup.find_all("ol")), 3)
        self.assertTrue(all(not el.has_attr("start") for el in soup.find_all("ol")))

    def test_zero_restart_keeps_descendant_counter(self):
        soup, _ = convert(
            docx(
                paragraph("A")
                + paragraph("A child", level=1)
                + paragraph("B")
                + paragraph("B child", level=1),
                levels=level(0) + level(1, "lowerRoman", restart=0),
            )
        )
        self.assertEqual(soup.find_all("ol")[2]["start"], "2")

    def test_restart_target_does_not_reset_after_lower_ancestor(self):
        soup, _ = convert(
            docx(
                paragraph("A")
                + paragraph("A intermediate", level=1)
                + paragraph("First criterion", level=2)
                + paragraph("B intermediate", level=1)
                + paragraph("Second criterion", level=2),
                levels=level(0)
                + level(1, "lowerLetter")
                + level(2, "lowerRoman", restart=1),
            )
        )
        self.assertEqual(soup.find_all("ol")[-1]["start"], "2")

    def test_default_restart_resets_after_higher_ancestor_even_with_level_gap(self):
        soup, _ = convert(
            docx(
                paragraph("A")
                + paragraph("First criterion", level=2)
                + paragraph("B")
                + paragraph("First new criterion", level=2),
                levels=level(0) + level(2, "lowerRoman"),
            )
        )
        self.assertTrue(all(not el.has_attr("start") for el in soup.find_all("ol")))

    def test_paragraph_based_on_style_inherits_numbering(self):
        styles = '<w:style w:type="paragraph" w:styleId="Base"><w:name w:val="Base list"/><w:pPr><w:numPr><w:numId w:val="1"/><w:ilvl w:val="1"/></w:numPr></w:pPr></w:style><w:style w:type="paragraph" w:styleId="Child"><w:name w:val="Derived list"/><w:basedOn w:val="Base"/></w:style>'
        soup, _ = convert(
            docx(
                paragraph("Inherited", num=None, style="Child"),
                levels=level(1, "lowerLetter"),
                styles=styles,
            )
        )
        self.assertEqual(soup.ol["type"], "a")
        self.assertEqual(soup.li.get_text(), "Inherited")

    def test_direct_properties_override_style_level(self):
        styles = '<w:style w:type="paragraph" w:styleId="Base"><w:name w:val="Base list"/><w:pPr><w:numPr><w:numId w:val="1"/><w:ilvl w:val="1"/></w:numPr></w:pPr></w:style>'
        soup, _ = convert(
            docx(
                paragraph("Direct", level=0, style="Base"),
                levels=level(0, "upperRoman") + level(1, "lowerLetter"),
                styles=styles,
            )
        )
        self.assertEqual(soup.ol["type"], "I")

    def test_unique_numbering_style_association_without_numpr(self):
        styles = '<w:style w:type="paragraph" w:styleId="Associated"><w:name w:val="Associated list"/></w:style>'
        associated = level(1, "lowerLetter").replace(
            "</w:lvl>", '<w:pStyle w:val="Associated"/></w:lvl>'
        )
        soup, plan = convert(
            docx(
                paragraph("Associated", num=None, style="Associated"),
                levels=associated,
                styles=styles,
            )
        )
        self.assertEqual(soup.ol["type"], "a")
        self.assertEqual(plan.warnings, [])

    def test_ambiguous_style_association_keeps_existing_conversion_and_warns(self):
        styles = '<w:style w:type="paragraph" w:styleId="Associated"><w:name w:val="Associated list"/></w:style>'
        associated = level(0, "lowerLetter").replace(
            "</w:lvl>", '<w:pStyle w:val="Associated"/></w:lvl>'
        )
        source = docx(
            paragraph("Ambiguous", num=None, style="Associated"),
            levels=associated,
            styles=styles,
            numbers='<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num><w:num w:numId="2"><w:abstractNumId w:val="0"/></w:num>',
        )
        copied, plan = prepare_word_lists(source)
        self.assertIs(copied, source)
        self.assertEqual(len(plan.warnings), 1)

    def test_numid_zero_suppresses_implicit_style_association(self):
        styles = '<w:style w:type="paragraph" w:styleId="Associated"><w:name w:val="Associated list"/></w:style>'
        associated = level(0, "lowerLetter").replace(
            "</w:lvl>", '<w:pStyle w:val="Associated"/></w:lvl>'
        )
        source = docx(
            paragraph("Disabled", num="0", style="Associated"),
            levels=associated,
            styles=styles,
        )
        copied, plan = prepare_word_lists(source)
        self.assertIs(copied, source)
        self.assertEqual(plan.warnings, [])

    def test_outer_start_override_on_numbering_style_link(self):
        styles = '<w:style w:type="numbering" w:styleId="Linked"><w:name w:val="Linked"/><w:pPr><w:numPr><w:numId w:val="2"/></w:numPr></w:pPr></w:style>'
        numbers = '<w:abstractNum w:abstractNumId="1"><w:numStyleLink w:val="Linked"/></w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="1"/><w:lvlOverride w:ilvl="0"><w:startOverride w:val="7"/></w:lvlOverride></w:num><w:num w:numId="2"><w:abstractNumId w:val="0"/></w:num>'
        soup, plan = convert(
            docx(
                paragraph("Linked override"),
                levels=level(0, "upperRoman"),
                numbers=numbers,
                styles=styles,
            )
        )
        self.assertEqual(soup.ol["start"], "7")
        self.assertEqual(soup.ol["type"], "I")
        self.assertEqual(plan.warnings, [])

    def test_numbering_disabled_with_zero_stays_prose(self):
        soup, plan = convert(docx(paragraph("Not a list", num="0")))
        self.assertIsNone(soup.ol)
        self.assertEqual(soup.p.get_text(), "Not a list")
        self.assertFalse(plan.style_map)

    def test_bounded_indented_continuation_stays_in_previous_item(self):
        soup, _ = convert(
            docx(
                paragraph("First")
                + paragraph("Explanation", num=None, indent=720)
                + paragraph("Second")
            )
        )
        self.assertEqual(len(soup.find_all("li")), 2)
        self.assertEqual(soup.li.p.get_text(), "Explanation")

    def test_multiple_bounded_continuation_paragraphs_preserve_order(self):
        soup, _ = convert(
            docx(
                paragraph("First")
                + paragraph("Explanation one", num=None, indent=720)
                + paragraph("Explanation two", num=None, indent=720)
                + paragraph("Second")
            )
        )
        self.assertEqual(
            [p.get_text() for p in soup.li.find_all("p")],
            ["Explanation one", "Explanation two"],
        )
        self.assertEqual(len(soup.find_all("li")), 2)

    def test_unbounded_or_unindented_prose_is_not_absorbed(self):
        for middle in (
            paragraph("Prose", num=None),
            paragraph("Prose", num=None, indent=720),
        ):
            with self.subTest(middle=middle):
                suffix = "" if "w:left" in middle else paragraph("Second")
                soup, _ = convert(docx(paragraph("First") + middle + suffix))
                self.assertIsNone(soup.find("p").find_parent("li"))

    def test_unsupported_custom_format_keeps_existing_conversion_and_warns(self):
        for fmt, text in (("decimal", "%1.%2."), ("decimalZero", "%1.")):
            with self.subTest(fmt=fmt, text=text):
                source = docx(paragraph("Custom"), levels=level(0, fmt, text=text))
                copied, plan = prepare_word_lists(source)
                self.assertIs(copied, source)
                self.assertEqual(len(plan.warnings), 1)
                self.assertFalse(plan.style_map)
                self.assertEqual(
                    plan.restore_html("<p>unchanged</p>"), "<p>unchanged</p>"
                )

    def test_styles_cycle_terminates(self):
        styles = '<w:style w:type="paragraph" w:styleId="A"><w:name w:val="A"/><w:basedOn w:val="B"/></w:style><w:style w:type="paragraph" w:styleId="B"><w:name w:val="B"/><w:basedOn w:val="A"/></w:style>'
        soup, _ = convert(docx(paragraph("Prose", num=None, style="A"), styles=styles))
        self.assertEqual(soup.p.get_text(), "Prose")

    def test_links_emphasis_and_bookmarks_survive(self):
        runs = '<w:bookmarkStart w:id="1" w:name="target"/><w:r><w:rPr><w:b/></w:rPr><w:t>Strong </w:t></w:r><w:hyperlink w:anchor="target"><w:r><w:rPr><w:i/></w:rPr><w:t>linked</w:t></w:r></w:hyperlink><w:bookmarkEnd w:id="1"/>'
        soup, _ = convert(docx(paragraph("", runs=runs)))
        self.assertEqual(soup.strong.get_text(), "Strong ")
        self.assertEqual(soup.find("a", href="#target").em.get_text(), "linked")
        self.assertIsNotNone(soup.find(id="target"))

    def test_conversion_copy_does_not_modify_source_or_unrelated_zip_parts(self):
        source = docx(paragraph("Item"), extra={"custom/private.bin": b"unchanged"})
        original = source.getvalue()
        copied, _ = prepare_word_lists(source)
        self.assertEqual(source.getvalue(), original)
        with ZipFile(copied) as archive:
            self.assertEqual(archive.read("custom/private.bin"), b"unchanged")

    def test_table_boundaries_keep_distinct_trees(self):
        table = "<w:tbl><w:tr><w:tc>" + paragraph("In cell") + "</w:tc></w:tr></w:tbl>"
        soup, _ = convert(docx(paragraph("Before") + table + paragraph("After")))
        self.assertEqual(len(soup.find_all("ol")), 3)
        self.assertIsNotNone(soup.table.ol)
        self.assertEqual(soup.find_all("ol")[-1]["start"], "3")

    def test_native_numbered_checklist_rows_retain_existing_child_transform(self):
        table = (
            "<w:tbl><w:tr><w:tc>"
            + paragraph("☐ Parent", indent=0)
            + "</w:tc></w:tr><w:tr><w:tc>"
            + paragraph("☐ Child", indent=720)
            + "</w:tc></w:tr></w:tbl>"
        )
        source = docx(table)
        copied, plan = prepare_word_lists(source)
        html = mammoth.convert_to_html(
            copied,
            style_map="\n".join(
                [plan.style_map, APPLICATION_CHECKLIST_CHILD_STYLE_MAP]
            ),
            transform_document=transform_word_document,
        ).value
        soup = BeautifulSoup(plan.restore_html(html), "html.parser")
        self.assertIsNotNone(soup.find("p", class_="application-list--left-indent"))
        self.assertEqual(plan.style_map, "")

    def test_notes_parts_are_not_rewritten(self):
        footnotes = f'<w:footnotes xmlns:w="{WORD_NS}"><w:footnote w:id="1">{paragraph("Note")}</w:footnote></w:footnotes>'
        source = docx(paragraph("Item"), extra={"word/footnotes.xml": footnotes})
        copied, _ = prepare_word_lists(source)
        with ZipFile(copied) as archive:
            self.assertEqual(archive.read("word/footnotes.xml"), footnotes.encode())

    def test_malicious_xml_declarations_rejected(self):
        for part in ("word/document.xml", "word/styles.xml", "word/numbering.xml"):
            with self.subTest(part=part):
                source = docx(
                    paragraph("Item"),
                    extra={
                        part: b'<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><x>&e;</x>'
                    },
                )
                with self.assertRaisesRegex(ValueError, "Unsupported XML"):
                    prepare_word_lists(source)

    def test_plain_and_manual_marker_prose_unchanged(self):
        for text in ("Ordinary prose.", "1) First 2) Second", "a. Could be prose"):
            with self.subTest(text=text):
                source = docx(paragraph(text, num=None))
                copied, plan = prepare_word_lists(source)
                self.assertIs(copied, source)
                self.assertFalse(plan.style_map)

    def test_restore_is_idempotent(self):
        source = docx(
            paragraph("First") + paragraph("Child", level=1),
            levels=level(0, "lowerLetter") + level(1, "lowerRoman"),
        )
        copied, plan = prepare_word_lists(source)
        html = mammoth.convert_to_html(copied, style_map=plan.style_map).value
        once = plan.restore_html(html)
        self.assertEqual(plan.restore_html(once), once)
