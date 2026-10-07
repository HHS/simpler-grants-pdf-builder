"""Referenced list-item targets survive import without changing list policy."""

from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from martor.templatetags.martortags import safe_markdown

from nofos.models import Nofo
from nofos.nofo import preserve_bookmark_targets
from nofos.nofo_markdown import PRESERVE_BOOKMARK_TARGET_ATTR, md


class ListAnchorConversionTests(SimpleTestCase):
    def convert(self, html):
        soup = BeautifulSoup(html, "html.parser")
        preserve_bookmark_targets(soup)
        body = md(str(soup))
        return soup, body, BeautifulSoup(safe_markdown(body), "html.parser")

    def test_referenced_targets_in_ordered_unordered_nested_and_start_lists(self):
        for content in (
            '<ol><li id="note-1">Review eligibility.</li><li>Apply online.</li></ol>',
            '<ul><li id="note-1">Review eligibility.</li><li>Apply online.</li></ul>',
            '<ul><li>Parent<ul><li id="note-1">Review eligibility.</li></ul></li></ul>',
            '<ol start="3"><li id="note-1">Review eligibility.</li></ol>',
        ):
            with self.subTest(content=content):
                soup, body, rendered = self.convert(
                    '<p><a href="#note-1">Read note</a></p>' + content
                )
                self.assertEqual(len(rendered.find_all(id="note-1")), 1)
                target = rendered.find(id="note-1")
                self.assertEqual(target.name, "a")
                self.assertIsNotNone(target.find_parent("li"))
                self.assertIn(
                    "Review eligibility.", target.find_parent("li").get_text()
                )
                self.assertEqual(rendered.find("a", href=True)["href"], "#note-1")
                self.assertNotIn(PRESERVE_BOOKMARK_TARGET_ATTR, body)
                self.assertEqual(len(soup.find_all(id="note-1")), 1)

    def test_explicit_anchor_control_remains_at_source_location(self):
        _, body, rendered = self.convert(
            '<p><a href="#note-1">Read note</a></p><ol><li>Before <a id="note-1"></a>after.</li></ol>'
        )
        self.assertIn('Before <a id="note-1"></a>after.', body)
        self.assertEqual(len(rendered.find_all(id="note-1")), 1)

    def test_unreferenced_and_duplicate_ids_do_not_get_new_anchors(self):
        for content in (
            '<ol><li id="unused">Review eligibility.</li></ol>',
            '<p><a href="#note-1">Read note</a></p><ol><li id="note-1">First</li><li id="note-1">Second</li></ol>',
            '<p id="note-1">Existing target</p><p><a href="#note-1">Read note</a></p><ol><li id="note-1">Duplicate</li></ol>',
        ):
            with self.subTest(content=content):
                soup, _, _ = self.convert(content)
                self.assertIsNone(
                    soup.find("a", attrs={PRESERVE_BOOKMARK_TARGET_ATTR: True})
                )
                self.assertIsNone(soup.find("li").find("a", id=True))

    def test_native_endnote_targets_and_numbering_are_not_replaced(self):
        _, body, rendered = self.convert(
            '<p><a href="#footnote-1" id="footnote-ref-1">1</a></p><ol><li id="footnote-1">Source<a href="#footnote-ref-1">↑</a></li></ol>'
        )
        self.assertEqual(rendered.find(id="footnote-1").name, "li")
        self.assertEqual(rendered.find(id="footnote-1")["tabindex"], "-1")
        self.assertEqual(len(rendered.find_all(id="footnote-1")), 1)
        self.assertNotIn(PRESERVE_BOOKMARK_TARGET_ATTR, body)

    def test_list_target_in_table_retains_one_target_without_marker(self):
        _, body, rendered = self.convert(
            '<p><a href="#note-1">Read note</a></p><table><tr><th>Reference</th></tr><tr><td><ul><li id="note-1">Review eligibility.</li></ul></td></tr></table>'
        )
        self.assertEqual(len(rendered.find_all(id="note-1")), 1)
        self.assertIsNotNone(rendered.find(id="note-1").find_parent("li"))
        self.assertNotIn(PRESERVE_BOOKMARK_TARGET_ATTR, body)

    def test_target_does_not_copy_event_handlers(self):
        _, body, rendered = self.convert(
            '<p><a href="#note-1">Read note</a></p><ol><li id="note-1" onclick="alert(1)">Review eligibility.</li></ol>'
        )
        self.assertNotIn("onclick", body)
        self.assertEqual(rendered.find(id="note-1").attrs, {"id": "note-1"})


@override_settings(DEBUG=False)
class ListAnchorImportTests(TestCase):
    prefix = "<p>Opdiv: CDC</p><p>Opportunity number: SYNTHETIC-ANCHOR</p><p>Opportunity title: Synthetic list anchors</p><h1>Opportunity</h1><h2>References</h2>"

    def setUp(self):
        user = get_user_model().objects.create_user(
            email="anchor-test@example.com",
            password="local-test-only",
            group="bloom",
            force_password_reset=False,
        )
        self.client.force_login(user)

    def test_referenced_list_target_survives_actual_import_and_rendering(self):
        for content in (
            '<ol><li id="note-1">Review eligibility.</li></ol>',
            '<ul><li id="note-1">Review eligibility.</li></ul>',
            '<ol start="3"><li id="note-1">Review eligibility.</li></ol>',
            '<ol><li>Review <a id="note-1"></a>eligibility.</li></ol>',
        ):
            with self.subTest(content=content):
                html = self.prefix + '<p><a href="#note-1">Read note</a></p>' + content
                response = self.client.post(
                    reverse("nofos:nofo_import"),
                    {
                        "nofo-import": SimpleUploadedFile(
                            "anchor-test.html", html.encode(), content_type="text/html"
                        )
                    },
                )
                self.assertEqual(response.status_code, 302)
                document = Nofo.objects.latest("created")
                body = document.sections.get().subsections.get().body
                rendered = BeautifulSoup(safe_markdown(body), "html.parser")
                self.assertEqual(len(rendered.find_all(id="note-1")), 1)
                self.assertIsNotNone(rendered.find(id="note-1").find_parent("li"))
                self.assertEqual(rendered.find("a", href=True)["href"], "#note-1")
                self.assertNotIn(PRESERVE_BOOKMARK_TARGET_ATTR, body)
