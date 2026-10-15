"""Import-only external citation links, through real shared consumers."""

from io import BytesIO
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

from bs4 import BeautifulSoup, Comment
from compare.models import CompareSection, CompareSubsection
from compare.utils import create_compare_document
from composer.models import ContentGuideSection, ContentGuideSubsection
from composer.utils import create_content_guide_document
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.endnotes import linkify_endnote_citations
from nofos.nofo import add_headings_to_document, parse_uploaded_file_as_html_string
from nofos.pdf_service import generate_nofo_pdf
from nofos.tests_nofos import test_endnote_import as note_tests
from nofos.tests_nofos.test_endnote_import import (
    DOCX_CONTENT_TYPE,
    assert_internal_endnote_links_are_reciprocal,
    import_html_to_nofo,
    native_notes_docx,
    process_html_to_sections,
    render_stored_document,
)

EXAMPLES = [
    ("https://www.cdc.gov/injury/wisqars/index.html", None),
    ("https://doi.org/10.1016/j.amepre.2019.11.020", None),
    ("https://doi.org/10.1016/S2468-2667(17)30118-4", None),
    ("https://doi.org/10.1001/jamapediatrics.2016.1559", None),
    ("https://nces.ed.gov/pubsearch/pubsinfo.asp?pubid=2024043", None),
    (
        "www.cdc.gov/nchs/rss/round2/technology-facilitated-sexual-violence.html",
        "https://www.cdc.gov/nchs/rss/round2/technology-facilitated-sexual-violence.html",
    ),
    ("doi:10.1017/S0033291722000836", "https://doi.org/10.1017/S0033291722000836"),
    ("doi:10.1016/j.jaac.2024.03.019", "https://doi.org/10.1016/j.jaac.2024.03.019"),
    ("http://example.org/study?a=1&b=2#findings", None),
]


def citation_docx():
    """Same note has typed addresses and a real external Word relationship."""
    with ZipFile(BytesIO(native_notes_docx())) as source:
        parts = {name: source.read(name) for name in source.namelist()}
    parts["word/endnotes.xml"] = b"""<?xml version="1.0" encoding="UTF-8"?>
<w:endnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<w:endnote w:id="1"><w:p><w:r><w:endnoteRef/><w:t xml:space="preserve"> Typed https://www.cdc.gov/injury/wisqars/index.html, doi:10.1017/S0033291722000836 and www.example.org/study. </w:t></w:r>
<w:hyperlink r:id="citation"><w:r><w:rPr><w:i/></w:rPr><w:t>Existing source</w:t></w:r></w:hyperlink>
</w:p></w:endnote></w:endnotes>"""
    parts[
        "word/_rels/endnotes.xml.rels"
    ] = b"""<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="citation" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="https://doi.org/10.1111/cch.12617" TargetMode="External"/></Relationships>"""
    result = BytesIO()
    with ZipFile(result, "w", ZIP_DEFLATED) as archive:
        for name, content in parts.items():
            archive.writestr(name, content)
    return result.getvalue()


class CitationLinkificationTests(SimpleTestCase):
    def linkify(self, content):
        soup = BeautifulSoup(
            '<ol><li id="endnote-1" tabindex="-1"><p>'
            + content
            + '<a href="#endnote-ref-1">↑</a></p></li></ol>',
            "html.parser",
        )
        before = soup.get_text()
        linkify_endnote_citations(soup)
        self.assertEqual(soup.get_text(), before)
        self.assertEqual(soup.li["tabindex"], "-1")
        return soup

    def test_issue_examples_and_citation_punctuation(self):
        for label, href in EXAMPLES:
            for suffix in (".", ",", ";", ") (Accessed May 6, 2026)."):
                with self.subTest(label=label, suffix=suffix):
                    soup = self.linkify("Citation (" + label + suffix)
                    anchor = soup.find("a", href=href or label)
                    self.assertIsNotNone(anchor)
                    self.assertEqual(anchor.get_text(), label)
                    self.assertTrue(str(anchor.next_sibling).startswith(suffix))

    def test_preserves_formatted_split_address_query_fragment_and_escaping(self):
        soup = self.linkify(
            "Study <em>https://example.org/</em><strong>paper(a)</strong>?a=1&amp;b=2#results. More."
        )
        anchor = soup.find("a", href="https://example.org/paper(a)?a=1&b=2#results")
        self.assertIsNotNone(anchor)
        self.assertEqual(anchor.em.get_text(), "https://example.org/")
        self.assertEqual(anchor.strong.get_text(), "paper(a)")
        self.assertIn("a=1&amp;b=2#results", str(anchor))
        self.assertEqual(str(anchor.next_sibling), ". More.")

    def test_preserves_existing_links_and_excludes_non_citation_or_unsafe_content(self):
        html = """<p>https://example.org/outside</p><li id="endnote-ref-1">https://example.org/reference</li>
<li id="endnote-1"><p><a href="http://dx.doi.org/10.15585/mmwr.su7304a5" title="original"><em>http://dx.doi.org/10.15585/mmwr.su7304a5</em></a>
<a href="https://doi.org/https://doi.org/10.1016/j.childyouth.2016.10.021">Malformed existing source</a>
<code>https://example.org/code</code><script>https://example.org/script</script><!-- https://example.org/comment -->
<span title="https://example.org/attribute">Citation without an address.</span>
javascript:alert(1) file:///etc/passwd user@www.example.org</p></li>"""
        soup = BeautifulSoup(html, "html.parser")
        before = str(soup)
        linkify_endnote_citations(soup)
        self.assertEqual(str(soup), before)

    def test_linking_other_text_keeps_comments_hidden_and_excluded_tags_intact(self):
        soup = self.linkify(
            "<!--hidden https://example.org/comment--><code>https://example.org/code</code><script>https://example.org/script</script><style>https://example.org/style</style> https://example.org/actual. <!--trailing comment-->"
        )
        self.assertEqual(
            [
                str(node)
                for node in soup.find_all(string=lambda node: isinstance(node, Comment))
            ],
            ["hidden https://example.org/comment", "trailing comment"],
        )
        self.assertNotIn("trailing comment", soup.get_text())
        for tag in ("code", "script", "style"):
            self.assertEqual(soup.find(tag).string, f"https://example.org/{tag}")
        self.assertEqual(len(soup.select('a[href^="http"]')), 1)

    def test_idempotent_and_does_not_fix_malformed_typed_resolver(self):
        soup = self.linkify(
            "https://example.org/one, doi:10.1234/two. https://doi.org/https://doi.org/10.1234/broken"
        )
        before = str(soup)
        linkify_endnote_citations(soup)
        self.assertEqual(str(soup), before)
        self.assertEqual(len(soup.select('a[href^="http"]')), 2)
        self.assertFalse(soup.select("a a"))

    def test_hard_breaks_and_blocks_do_not_join_address_with_following_text(self):
        for boundary in (
            "<br>",
            "<hr>",
            '<img src="local.png" alt="diagram">',
            "<wbr>",
        ):
            with self.subTest(boundary=boundary):
                soup = self.linkify(
                    "https://example.org/path"
                    + boundary
                    + "Next sentence https://example.org/two."
                )
                self.assertTrue(soup.find("a", href="https://example.org/path"))
                self.assertFalse(soup.find("a", href="https://example.org/pathNext"))
                self.assertTrue(soup.find("a", href="https://example.org/two"))
                self.assertIsNotNone(soup.find(boundary.split()[0][1:].split(">")[0]))
        soup = BeautifulSoup(
            '<li id="endnote-1"><p>https://example.org/path</p><p>Next</p></li>',
            "html.parser",
        )
        linkify_endnote_citations(soup)
        self.assertEqual(soup.find("a")["href"], "https://example.org/path")

    def test_mixed_direct_and_paragraph_citation_text_is_linked_once(self):
        soup = BeautifulSoup(
            '<li id="endnote-1">Available https://example.org/direct<p>Additional https://example.org/paragraph</p> After https://example.org/last.</li>',
            "html.parser",
        )
        before = soup.get_text()
        linkify_endnote_citations(soup)
        self.assertEqual(soup.get_text(), before)
        self.assertEqual(
            [anchor["href"] for anchor in soup.select("a")],
            [
                "https://example.org/direct",
                "https://example.org/paragraph",
                "https://example.org/last",
            ],
        )
        linkify_endnote_citations(soup)
        self.assertEqual(len(soup.select("a")), 3)


class CitationPersistenceTests(TestCase):
    def test_real_docx_distinguishes_hyperlink_relationship_from_typed_text(self):
        upload = SimpleUploadedFile(
            "synthetic-citations.docx", citation_docx(), content_type=DOCX_CONTENT_TYPE
        )
        html, _ = parse_uploaded_file_as_html_string(upload)
        intermediate = BeautifulSoup(html, "html.parser")
        self.assertEqual(len(intermediate.select('a[href^="http"]')), 1)
        self.assertEqual(
            intermediate.find(
                "a", href="https://doi.org/10.1111/cch.12617"
            ).em.get_text(),
            "Existing source",
        )
        nofo = import_html_to_nofo(html)
        stored = render_stored_document(nofo)
        self.assertEqual(len(stored.select('a[href^="http"]')), 4)
        assert_internal_endnote_links_are_reciprocal(self, stored)
        self.assertTrue(stored.find("a", href="https://www.example.org/study"))

        user = BloomUser.objects.create_user(
            email="citations@example.com",
            password="local-test-only",
            group=nofo.group,
            force_password_reset=False,
        )
        self.client.force_login(user)
        before = list(nofo.sections.values_list("subsections__body", flat=True))
        response = self.client.get(reverse("nofos:nofo_view", kwargs={"pk": nofo.pk}))
        self.assertEqual(response.status_code, 200)
        rendered = BeautifulSoup(response.content, "html.parser")
        self.assertTrue(rendered.find("a", href="https://www.example.org/study"))
        self.assertEqual(
            list(nofo.sections.values_list("subsections__body", flat=True)), before
        )

    def test_manual_note_and_shared_consumers_preserve_links_and_formatting(self):
        html = "<h1>Program</h1><p>Evidence [1].</p><h1>Endnotes</h1><p>[1] Citation <em>https://example.org/</em><strong>study</strong>?a=1&amp;b=2#findings.</p>"
        for create, section_model, subsection_model in (
            (None, None, None),
            (create_compare_document, CompareSection, CompareSubsection),
            (
                create_content_guide_document,
                ContentGuideSection,
                ContentGuideSubsection,
            ),
        ):
            with self.subTest(consumer=create):
                if create is None:
                    document = import_html_to_nofo(html)
                else:
                    _, sections = process_html_to_sections(html)
                    document = create("Citation test", sections, "TEST")
                    add_headings_to_document(
                        document,
                        SectionModel=section_model,
                        SubsectionModel=subsection_model,
                    )
                stored = render_stored_document(document)
                assert_internal_endnote_links_are_reciprocal(self, stored)
                anchor = stored.find(
                    "a", href="https://example.org/study?a=1&b=2#findings"
                )
                self.assertIsNotNone(anchor)
                self.assertTrue(anchor.em)
                self.assertTrue(anchor.strong)

    @patch("nofos.pdf_service.docraptor.DocApi")
    def test_pdf_service_submits_linked_citations_without_changing_saved_content(
        self, doc_api
    ):
        nofo = import_html_to_nofo(
            "<h1>Program</h1><p>Evidence [1].</p><h1>Endnotes</h1><p>[1] https://example.org/study?a=1&amp;b=2#findings.</p>"
        )
        before = list(nofo.sections.values_list("subsections__body", flat=True))
        doc_api.return_value.create_doc.return_value = b"synthetic-provider-response"
        result = generate_nofo_pdf(
            nofo, base_url="https://example.org/nofo/", is_test_pdf=True
        )
        payload = doc_api.return_value.create_doc.call_args.args[0]
        rendered = BeautifulSoup(payload["document_content"], "html.parser")
        self.assertTrue(
            rendered.find("a", href="https://example.org/study?a=1&b=2#findings")
        )
        self.assertTrue(payload["test"])
        self.assertEqual(result.content, b"synthetic-provider-response")
        self.assertEqual(
            list(nofo.sections.values_list("subsections__body", flat=True)), before
        )

    @patch("nofos.pdf_service.docraptor.DocApi")
    def test_saved_plain_citation_is_not_rewritten_on_view_or_export(self, doc_api):
        nofo = import_html_to_nofo(
            "<h1>Program</h1><p>Evidence [1].</p><h1>Endnotes</h1><p>[1] Source.</p>"
        )
        subsection = nofo.sections.get(name="Endnotes").subsections.first()
        subsection.body = (
            '<p id="endnote-manual-1">Existing https://example.org/not-reimported.</p>'
        )
        subsection.save(update_fields=["body"])
        original = subsection.body
        user = BloomUser.objects.create_user(
            email="old-citations@example.com",
            password="local-test-only",
            group=nofo.group,
            force_password_reset=False,
        )
        self.client.force_login(user)
        response = self.client.get(reverse("nofos:nofo_view", kwargs={"pk": nofo.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(
            BeautifulSoup(response.content, "html.parser").find(
                "a", href="https://example.org/not-reimported"
            )
        )
        doc_api.return_value.create_doc.return_value = b"synthetic-provider-response"
        generate_nofo_pdf(nofo, base_url="https://example.org/nofo/", is_test_pdf=True)
        payload = doc_api.return_value.create_doc.call_args.args[0]
        self.assertIsNone(
            BeautifulSoup(payload["document_content"], "html.parser").find(
                "a", href="https://example.org/not-reimported"
            )
        )
        subsection.refresh_from_db()
        self.assertEqual(subsection.body, original)


class CitationReimportTests(note_tests.EndnoteReimportTests):
    def upload(self):
        upload = super().upload()
        return SimpleUploadedFile(
            "citations.html",
            upload.read().replace(
                b"Replacement source.", b"Replacement https://example.org/study."
            ),
            content_type="text/html",
        )

    def test_reimport_creates_external_citation_links(self):
        response = self.client.post(self.url, {"nofo-import": self.upload()})
        self.assertEqual(response.status_code, 302)
        stored = render_stored_document(self.nofo)
        self.assertTrue(stored.find("a", href="https://example.org/study"))
