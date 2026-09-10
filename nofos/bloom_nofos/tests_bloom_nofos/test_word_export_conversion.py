"""Exercise the installed converter, including the deployed reference and adapter."""

import io
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import skipUnless
from zipfile import ZipFile

from bloom_nofos.word_export import W, convert_html, normalize_docx
from constance.test import override_config
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from nofos.nofo import parse_uploaded_file_as_html_string

FIXTURE = Path(__file__).parent / "fixtures" / "word_export.html"


class PageBreakPreservationTests(SimpleTestCase):
    def document(self, body):
        output = io.BytesIO()
        with ZipFile(output, "w") as archive:
            archive.writestr(
                "word/document.xml",
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                "<w:body>" + body + "</w:body></w:document>",
            )
        with ZipFile(io.BytesIO(normalize_docx(output.getvalue()))) as archive:
            return ET.fromstring(archive.read("word/document.xml"))

    def test_break_before_heading_becomes_native_paragraph_property(self):
        xml = self.document(
            '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
            '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr>'
            "<w:r><w:t>Next section</w:t></w:r></w:p>"
        )
        self.assertEqual(len(list(xml.iter(W + "p"))), 1)
        self.assertIsNotNone(xml.find(".//" + W + "pageBreakBefore"))
        self.assertEqual(xml.find(".//" + W + "pStyle").get(W + "val"), "Heading1")

    def test_break_before_table_is_retained_in_place(self):
        xml = self.document(
            '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
            "<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Table content</w:t></w:r>"
            "</w:p></w:tc></w:tr></w:tbl>"
        )
        body = xml.find(W + "body")
        self.assertEqual([node.tag for node in body], [W + "p", W + "tbl"])
        self.assertIsNotNone(body[0].find(".//" + W + "br"))

    def test_break_with_content_or_drawing_is_not_removed(self):
        for content in ("<w:t>Before break</w:t>", "<w:drawing/>"):
            with self.subTest(content=content):
                xml = self.document(
                    "<w:p><w:r>" + content + '<w:br w:type="page"/></w:r></w:p>'
                    "<w:p><w:r><w:t>After break</w:t></w:r></w:p>"
                )
                self.assertEqual(len(list(xml.iter(W + "p"))), 2)
                self.assertIsNotNone(xml.find(".//" + W + "br"))


@skipUnless(
    shutil.which(getattr(settings, "PANDOC_BINARY", "pandoc")),
    "Requires the Pandoc binary bundled in the application image",
)
class InstalledPandocTests(TestCase):
    @override_config(WORD_IMPORT_STRICT_MODE=True)
    def test_editable_structure_links_lists_and_page_break_survive(self):
        data = convert_html(FIXTURE.read_text())
        with ZipFile(io.BytesIO(data)) as archive:
            xml = ET.fromstring(archive.read("word/document.xml"))
            relationships = archive.read("word/_rels/document.xml.rels")
            numbering = archive.read("word/numbering.xml")
        text = " ".join(node.text or "" for node in xml.iter(W + "t"))
        expected = (
            "Step 1: Review the Opportunity",
            "Eligibility",
            "Third requirement",
            "Fourth requirement",
            "Nested evidence",
            "First attachment",
            "Second attachment",
            "Editable amount {Amount}",
            "Step 2: Get Ready to Apply",
            "Funding details",
            "Final content sentinel.",
        )
        positions = [text.index(value) for value in expected]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(len(list(xml.iter(W + "tbl"))), 1)
        styles = {node.get(W + "val") for node in xml.iter(W + "pStyle")}
        self.assertTrue({"Heading1", "Heading2"}.issubset(styles))
        self.assertTrue(list(xml.iter(W + "b")))
        self.assertTrue(list(xml.iter(W + "i")))
        self.assertTrue(list(xml.iter(W + "numPr")))
        self.assertIn(b'w:val="3"', numbering)
        self.assertIn(b"https://www.grants.gov/", relationships)
        self.assertIn(
            "funding", [node.get(W + "anchor") for node in xml.iter(W + "hyperlink")]
        )
        self.assertTrue(list(xml.iter(W + "pageBreakBefore")))
        html, warnings = parse_uploaded_file_as_html_string(
            SimpleUploadedFile(
                "synthetic.docx",
                data,
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        )
        self.assertEqual(warnings, 0)
        self.assertIn("Final content sentinel.", html)


@skipUnless(
    shutil.which(getattr(settings, "PANDOC_BINARY", "pandoc")),
    "Requires the Pandoc binary bundled in the application image",
)
@override_config(PANDOC_WORD_EXPORT_ENABLED=True, HHS_NOFO_POLICY_EXPORT_ENABLED=True)
class PandocClearanceRouteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Use the canonical clearance-view matrix: intact, altered, prominent,
        # ordinary content, and a missing required slot. Convert the real route.
        from nofos.tests_nofos.test_policy_language_export import (
            NofoExportPolicyLanguageRenderingTests,
        )

        NofoExportPolicyLanguageRenderingTests.setUpTestData.__func__(cls)

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse("nofos:nofo_export", args=[self.nofo.pk])

    def exported_text(self, action):
        response = self.client.post(self.url, {"export_action": action})
        self.assertEqual(response.status_code, 200, response.content[:300])
        with ZipFile(io.BytesIO(response.content)) as archive:
            xml = ET.fromstring(archive.read("word/document.xml"))
        return " ".join(node.text or "" for node in xml.iter(W + "t"))

    def test_normal_and_clearance_keep_their_distinct_content(self):
        normal = self.exported_text("download")
        clearance = self.exported_text("download_stripped")
        canonical = self.sam_slot.variants.first().canonical_text
        self.assertIn(canonical, normal)
        self.assertNotIn(canonical, clearance)
        self.assertIn("PRE-DECISIONAL", clearance)
        self.assertIn("Missing Required Slot", clearance)
        self.assertIn("omitted from this abbreviated review copy", clearance)
        self.assertIn("Priority review:", clearance)
        self.assertIn("Review:", clearance)
        for text in (normal, clearance):
            self.assertIn(
                "This text has clearly been rewritten by the program office.", text
            )
            self.assertIn(
                "A modified version of the funding preferences language.", text
            )
            self.assertIn(
                "This program funds community health workers in rural areas.", text
            )

    @override_config(HHS_NOFO_POLICY_EXPORT_ENABLED=False)
    def test_clearance_flag_still_blocks_download(self):
        response = self.client.post(self.url, {"export_action": "download_stripped"})
        self.assertEqual(response.status_code, 400)

    def test_clearance_rechecks_content_after_edit(self):
        from nofos.models import Subsection

        self.exported_text("download_stripped")
        subsection = Subsection.objects.get(
            section__nofo=self.nofo, policy_language_slot=self.sam_slot
        )
        subsection.body = "New program-specific registration requirement."
        subsection.save()
        clearance = self.exported_text("download_stripped")
        self.assertIn(subsection.body, clearance)

    def test_clearance_rechecks_revised_canonical_language(self):
        self.exported_text("download_stripped")
        variant = self.sam_slot.variants.first()
        original = variant.canonical_text
        variant.canonical_text = "New canonical registration requirement."
        variant.save()
        self.assertIn(original, self.exported_text("download_stripped"))

    def test_other_group_cannot_download_unpublished_document(self):
        self.user.group = "acf"
        self.user.save()
        response = self.client.post(self.url, {"export_action": "download"})
        self.assertEqual(response.status_code, 403)
