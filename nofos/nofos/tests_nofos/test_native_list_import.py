"""Native Word list semantics survive real upload, persistence and reimport."""

from bs4 import BeautifulSoup
from compare.models import CompareDocument
from composer.models import ContentGuide
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from martor.templatetags.martortags import safe_markdown

from nofos.models import Nofo
from nofos.tests_nofos.test_word_lists import docx, level, paragraph


def native_list_source(*, custom=False):
    styles = (
        '<w:style w:type="paragraph" w:styleId="Heading1">'
        '<w:name w:val="heading 1"/></w:style>'
        '<w:style w:type="paragraph" w:styleId="Heading2">'
        '<w:name w:val="heading 2"/></w:style>'
    )
    body = "".join(
        paragraph(text, num=None)
        for text in (
            "Opdiv: CDC",
            "Opportunity number: SYNTHETIC-LISTS-1121",
            "Opportunity name: Native list verification",
        )
    )
    body += paragraph("Step 1: Review the opportunity", num=None, style="Heading1")
    body += paragraph("Activities", num=None, style="Heading2")
    body += paragraph("Read the activities before applying.", num=None)
    body += paragraph("First activity", level=1)
    body += paragraph("First subactivity", level=2)
    body += paragraph("First criterion", level=3)
    body += paragraph("Additional criterion explanation.", num=None, indent=2880)
    body += paragraph("Second criterion", level=3)
    body += paragraph("Second activity", level=1)
    body += paragraph(
        "Inline 1) one option and 2) another option stay prose.", num=None
    )
    return docx(
        body,
        levels=level(1, "lowerLetter", text="Section %2" if custom else None)
        + level(2, "lowerRoman")
        + level(3),
        styles=styles,
    )


@override_settings(DEBUG=False)
class NativeListImportTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="native-list-test@example.com",
            password="local-test-only",
            group="bloom",
            force_password_reset=False,
            is_composer_admin=True,
        )
        self.client.force_login(self.user)

    def upload(self, source=None, url=None):
        source = source or native_list_source()
        return self.client.post(
            url or reverse("nofos:nofo_import"),
            {
                "nofo-import": SimpleUploadedFile(
                    "synthetic-native-lists.docx",
                    source.getvalue(),
                    content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

    def assert_saved_tree(self, document):
        body = document.sections.get().subsections.get(name="Activities").body
        rendered = BeautifulSoup(safe_markdown(body), "html.parser")
        self.assertEqual(
            [node["type"] for node in rendered.find_all("ol")], ["a", "i", "1"]
        )
        self.assertEqual(len(rendered.find_all("li")), 5)
        self.assertIsNotNone(rendered.find("li", string="Second criterion"))
        continuation = rendered.find("p", string="Additional criterion explanation.")
        self.assertIsNotNone(continuation.find_parent("li"))
        self.assertIn("First criterion", continuation.parent.get_text())
        self.assertIsNotNone(
            rendered.find(
                "p", string="Inline 1) one option and 2) another option stay prose."
            )
        )
        self.assertNotIn("data-nofo-source-list", body)
        self.assertNotIn("nofo-native-list-", body)
        return body

    def test_actual_word_import_persists_source_types_and_continuation(self):
        response = self.upload()
        self.assertEqual(response.status_code, 302)
        document = Nofo.objects.latest("created")
        before = self.assert_saved_tree(document)
        response = self.client.get(reverse("nofos:nofo_edit", args=[document.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'type="a"')
        self.assertEqual(self.assert_saved_tree(document), before)

    def test_unsupported_custom_marker_shows_nonblocking_review_guidance(self):
        response = self.upload(native_list_source(custom=True))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(response.url)
        self.assertContains(response, "Check list numbering")
        self.assertContains(
            response, "Some Word list numbering could not be preserved automatically."
        )
        self.assertContains(response, "Save subsection")
        self.assertNotContains(response, "Check for leftover template instructions")

    def test_reimport_does_not_compound_list_wrappers_or_duplicate_markers(self):
        self.assertEqual(self.upload().status_code, 302)
        document = Nofo.objects.latest("created")
        original = self.assert_saved_tree(document)
        for _ in range(2):
            response = self.upload(
                url=reverse("nofos:nofo_import_overwrite", kwargs={"pk": document.pk})
            )
            self.assertEqual(response.status_code, 302)
            document.refresh_from_db()
            self.assertEqual(self.assert_saved_tree(document), original)

    def test_actual_word_upload_retains_lists_in_shared_consumers(self):
        for route, model in (
            ("composer:composer_import", ContentGuide),
            ("compare:compare_import", CompareDocument),
        ):
            with self.subTest(route=route):
                self.assertEqual(self.upload(url=reverse(route)).status_code, 302)
                self.assert_saved_tree(model.objects.get())
