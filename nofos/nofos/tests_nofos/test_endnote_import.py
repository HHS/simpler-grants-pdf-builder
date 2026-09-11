from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

import markdown
from bs4 import BeautifulSoup
from compare.models import CompareSection, CompareSubsection
from compare.utils import create_compare_document
from composer.models import ContentGuideSection, ContentGuideSubsection
from composer.utils import create_content_guide_document
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.models import Nofo, Section, Subsection
from nofos.nofo import (
    add_headings_to_document,
    create_nofo,
    find_endnote_issues,
    get_sections_from_soup,
    get_subsections_from_sections,
    parse_uploaded_file_as_html_string,
    process_nofo_html,
    resolve_section_heading_level,
)

DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def import_html_to_nofo(html, title="Endnote regression test"):
    soup, sections = process_html_to_sections(html)
    nofo = create_nofo(title, sections, opdiv="TEST")
    add_headings_to_document(nofo)
    return nofo


def process_html_to_sections(html):
    soup = BeautifulSoup(html, "html.parser")
    top_heading_level = resolve_section_heading_level(soup)
    soup, _ = process_nofo_html(soup, top_heading_level)
    sections = get_sections_from_soup(soup, top_heading_level)
    sections = get_subsections_from_sections(sections, top_heading_level)
    return soup, sections


def render_stored_document(nofo):
    """Render persisted markdown bodies together so fragment links can be checked."""
    soup = BeautifulSoup("", "html.parser")
    for section in nofo.sections.all().order_by("order"):
        for subsection in section.subsections.all().order_by("order"):
            fragment = BeautifulSoup(
                markdown.markdown(subsection.body or "", extensions=["extra"]),
                "html.parser",
            )
            for node in list(fragment.contents):
                soup.append(node.extract())
    return soup


def assert_internal_endnote_links_are_reciprocal(test_case, soup):
    forward_links = [
        link
        for link in soup.select("a[id][href^='#']")
        if link.get_text("", strip=True).startswith("[")
    ]
    test_case.assertTrue(forward_links)
    test_case.assertEqual(
        len({link["id"] for link in forward_links}), len(forward_links)
    )

    for forward in forward_links:
        targets = soup.find_all(id=forward["href"][1:])
        test_case.assertEqual(len(targets), 1, forward)
        backlinks = targets[0].select(f'a[href="#{forward["id"]}"]')
        test_case.assertTrue(backlinks, forward)


def native_notes_docx():
    """Build a minimal real DOCX with one Word footnote and one Word endnote."""
    fixture = Path(__file__).parents[1] / "fixtures" / "docx" / "lists.docx"
    document_xml = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
 <w:body>
  <w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>Program</w:t></w:r></w:p>
  <w:p><w:r><w:t xml:space="preserve">Footnote claim</w:t></w:r><w:r><w:footnoteReference w:id="1"/><w:t xml:space="preserve"> and endnote claim</w:t></w:r><w:r><w:endnoteReference w:id="1"/><w:t>.</w:t></w:r></w:p>
  <w:sectPr/>
 </w:body>
</w:document>"""
    footnotes_xml = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:footnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
 <w:footnote w:id="1"><w:p><w:r><w:footnoteRef/><w:t xml:space="preserve"> Footnote citation.</w:t></w:r></w:p></w:footnote>
</w:footnotes>"""
    endnotes_xml = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:endnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
 <w:endnote w:id="1"><w:p><w:r><w:endnoteRef/><w:t xml:space="preserve"> Endnote citation.</w:t></w:r></w:p></w:endnote>
</w:endnotes>"""

    with ZipFile(fixture) as source:
        files = {name: source.read(name) for name in source.namelist()}

    content_types = files["[Content_Types].xml"].replace(
        b"</Types>",
        b'<Override PartName="/word/footnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"/>'
        b'<Override PartName="/word/endnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.endnotes+xml"/>'
        b"</Types>",
    )
    relationships = files["word/_rels/document.xml.rels"].replace(
        b"</Relationships>",
        b'<Relationship Id="rIdFootnotes" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes" Target="footnotes.xml"/>'
        b'<Relationship Id="rIdEndnotes" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/endnotes" Target="endnotes.xml"/>'
        b"</Relationships>",
    )
    files.update(
        {
            "[Content_Types].xml": content_types,
            "word/_rels/document.xml.rels": relationships,
            "word/document.xml": document_xml,
            "word/footnotes.xml": footnotes_xml,
            "word/endnotes.xml": endnotes_xml,
        }
    )

    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return output.getvalue()


def manual_notes_docx():
    """Build a DOCX whose manual marker is split across formatted Word runs."""
    fixture = Path(__file__).parents[1] / "fixtures" / "docx" / "lists.docx"
    document_xml = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
 <w:body>
  <w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>Program</w:t></w:r></w:p>
  <w:p><w:r><w:t>Manual claim [</w:t></w:r><w:r><w:rPr><w:b/></w:rPr><w:t>1</w:t></w:r><w:r><w:t>] in a Word document.</w:t></w:r></w:p>
  <w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>ENDNOTES:</w:t></w:r></w:p>
  <w:p><w:r><w:t>[</w:t></w:r><w:r><w:rPr><w:b/></w:rPr><w:t>1</w:t></w:r><w:r><w:t>] Manual source citation.</w:t></w:r></w:p>
  <w:sectPr/>
 </w:body>
</w:document>"""

    output = BytesIO()
    with ZipFile(fixture) as source, ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for name in source.namelist():
            archive.writestr(
                name,
                document_xml if name == "word/document.xml" else source.read(name),
            )
    return output.getvalue()


class BracketedEndnoteImportTests(TestCase):
    def test_real_pipeline_persists_reciprocal_links_for_formatting_split_markers(self):
        nofo = import_html_to_nofo(
            "<h1>Program</h1>"
            "<p>Evidence [<strong>1</strong>] supports this claim.</p>"
            "<h1>ENDNOTES:</h1>"
            "<p>[<em>1</em>] <strong>Source title</strong>.</p>"
        )

        self.assertTrue(nofo.sections.filter(name="Endnotes").exists())
        stored = render_stored_document(nofo)
        self.assertEqual(
            [link.get_text("", strip=True) for link in stored.select("a")].count("[1]"),
            2,
        )
        self.assertIsNotNone(stored.select_one("a strong"))
        self.assertIsNotNone(stored.select_one("a em"))
        assert_internal_endnote_links_are_reciprocal(self, stored)
        self.assertEqual(find_endnote_issues(nofo), [])

    def test_numbering_gap_is_advisory_and_complete_pairs_are_still_linked(self):
        nofo = import_html_to_nofo(
            "<h1>Program</h1><p>First [1], then third [3].</p>"
            "<h1>Endnotes</h1><p>[1] First source.</p><p>[3] Third source.</p>"
        )

        stored = render_stored_document(nofo)
        self.assertEqual(len(stored.select("a[id][href^='#']")), 2)
        assert_internal_endnote_links_are_reciprocal(self, stored)
        messages = [issue["message"] for issue in find_endnote_issues(nofo)]
        self.assertTrue(any("sequential" in message for message in messages))

    def test_processing_already_converted_html_does_not_duplicate_links_or_backlinks(
        self,
    ):
        html = (
            "<h1>Program</h1><p>Evidence [1].</p>" "<h1>Endnotes</h1><p>[1] Source.</p>"
        )
        soup = BeautifulSoup(html, "html.parser")
        top_heading_level = resolve_section_heading_level(soup)
        soup, _ = process_nofo_html(soup, top_heading_level)
        soup, _ = process_nofo_html(soup, top_heading_level)

        self.assertEqual(len(soup.select("a[id][href^='#']")), 1)
        self.assertEqual(len(soup.find_all("a", string="↑")), 1)
        assert_internal_endnote_links_are_reciprocal(self, soup)

    def test_saved_warning_locations_are_recomputed_after_an_edit(self):
        nofo = import_html_to_nofo(
            "<h1>Program</h1><p>Evidence [1].</p>" "<h1>Endnotes</h1><p>[1] Source.</p>"
        )
        program = nofo.sections.get(name="Program").subsections.first()
        endnotes = nofo.sections.get(name="Endnotes").subsections.first()
        program.body = "Changed claim [2]."
        program.save(update_fields=["body"])
        endnotes.body = "[1] Source."
        endnotes.save(update_fields=["body"])

        issues = find_endnote_issues(nofo)
        self.assertTrue(any("[2]" in issue["message"] for issue in issues))
        issue = next(issue for issue in issues if "[2]" in issue["message"])
        self.assertEqual(issue["section"], program.section)
        self.assertEqual(issue["subsection"], program)


class NativeWordNoteImportTests(TestCase):
    def test_docx_footnote_and_endnote_relationships_survive_storage(self):
        upload = SimpleUploadedFile(
            "native-notes.docx", native_notes_docx(), content_type=DOCX_CONTENT_TYPE
        )
        html, _ = parse_uploaded_file_as_html_string(upload)
        nofo = import_html_to_nofo(html, title="Native notes")

        stored = render_stored_document(nofo)
        self.assertIn("Footnote citation.", stored.get_text(" ", strip=True))
        self.assertIn("Endnote citation.", stored.get_text(" ", strip=True))
        self.assertTrue(stored.select_one('a[href^="#footnote-"]'))
        self.assertTrue(stored.select_one('a[href^="#endnote-"]'))
        assert_internal_endnote_links_are_reciprocal(self, stored)
        self.assertEqual(find_endnote_issues(nofo), [])

    def test_manual_word_markers_reach_stored_html_and_the_real_nofo_view(self):
        upload = SimpleUploadedFile(
            "manual-notes.docx", manual_notes_docx(), content_type=DOCX_CONTENT_TYPE
        )
        html, _ = parse_uploaded_file_as_html_string(upload)
        self.assertIn("Manual claim [<strong>1</strong>]", html)

        nofo = import_html_to_nofo(html, title="Manual notes from Word")
        stored = render_stored_document(nofo)
        assert_internal_endnote_links_are_reciprocal(self, stored)
        self.assertEqual(find_endnote_issues(nofo), [])

        user = BloomUser.objects.create_user(
            email="endnote-view@example.com",
            password="testpass123",
            group=nofo.group,
            force_password_reset=False,
        )
        self.client.force_login(user)
        response = self.client.get(reverse("nofos:nofo_view", kwargs={"pk": nofo.pk}))
        self.assertEqual(response.status_code, 200)
        rendered = BeautifulSoup(response.content, "html.parser")
        forward = next(
            link
            for link in rendered.select("a[id][href^='#']")
            if link.get_text("", strip=True) == "[1]"
        )
        self.assertEqual(forward.get("aria-label"), "Endnote 1")
        target = rendered.find(id=forward["href"][1:])
        self.assertIsNotNone(target)
        self.assertEqual(target.get("tabindex"), "-1")
        backlink = target.select_one(f'a[href="#{forward["id"]}"]')
        self.assertIsNotNone(backlink)
        self.assertEqual(backlink.get("aria-label"), "Return to endnote 1 reference")


class SharedImportPipelineTests(TestCase):
    def test_compare_and_composer_consumers_store_the_converted_links(self):
        html = (
            "<h1>Program</h1><p>Shared pipeline claim [1].</p>"
            "<h1>Endnotes</h1><p>[1] Shared pipeline source.</p>"
        )

        for create_document, section_model, subsection_model in (
            (create_compare_document, CompareSection, CompareSubsection),
            (
                create_content_guide_document,
                ContentGuideSection,
                ContentGuideSubsection,
            ),
        ):
            with self.subTest(consumer=create_document.__name__):
                _, sections = process_html_to_sections(html)
                document = create_document("Shared endnotes", sections, "TEST")
                add_headings_to_document(
                    document,
                    SectionModel=section_model,
                    SubsectionModel=subsection_model,
                )
                assert_internal_endnote_links_are_reciprocal(
                    self, render_stored_document(document)
                )


class EndnoteReimportTests(TestCase):
    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="endnote-reimport@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client = Client()
        self.client.force_login(self.user)
        self.nofo = Nofo.objects.create(
            title="Reimport endnotes",
            short_name="reimport-endnotes",
            number="TEST-884",
            opdiv="TEST",
            group="bloom",
            status="draft",
        )
        section = Section.objects.create(
            nofo=self.nofo, name="Original section", html_id="original", order=1
        )
        Subsection.objects.create(
            section=section, name="", body="Original content", order=1
        )
        self.url = reverse("nofos:nofo_import_overwrite", kwargs={"pk": self.nofo.pk})

    def upload(self):
        html = (
            "<p>Opdiv: TEST</p>"
            "<p>Opportunity number: TEST-884</p>"
            "<h1>Program</h1><p>Replacement claim [1].</p>"
            "<h1>Endnotes</h1><p>[1] Replacement source.</p>"
        )
        return SimpleUploadedFile(
            "endnotes.html", html.encode(), content_type="text/html"
        )

    def test_reimport_preserves_parent_id_and_archives_linked_history(self):
        original_id = self.nofo.pk
        response = self.client.post(self.url, {"nofo-import": self.upload()})

        self.assertRedirects(
            response,
            reverse("nofos:nofo_edit", kwargs={"pk": original_id}),
            fetch_redirect_response=False,
        )
        current = Nofo.objects.get(pk=original_id)
        assert_internal_endnote_links_are_reciprocal(
            self, render_stored_document(current)
        )
        history = Nofo.objects.get(successor=current)
        self.assertIsNotNone(history.archived)
        self.assertEqual(
            history.sections.get(name="Original section").subsections.first().body,
            "Original content",
        )

    @patch("nofos.views.add_headings_to_document")
    def test_failed_reimport_rolls_back_history_and_original_content(
        self, add_headings
    ):
        add_headings.side_effect = ValidationError("forced failure")
        response = self.client.post(self.url, {"nofo-import": self.upload()})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Nofo.objects.count(), 1)
        self.assertFalse(Nofo.objects.filter(successor=self.nofo).exists())
        self.nofo.refresh_from_db()
        self.assertEqual(
            self.nofo.sections.get().subsections.get().body, "Original content"
        )
