import re
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

from bs4 import BeautifulSoup
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context, Template
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.content_processing import process_document_content
from nofos.forms import SubsectionCreateForm, SubsectionEditForm
from nofos.models import THEME_CHOICES, Nofo, Section, Subsection
from nofos.note_paragraphs import (
    NOTE_CALLOUT_MARKER,
    has_note_label,
    normalize_note_labels,
)
from nofos.pdf_service import generate_nofo_pdf
from nofos.templatetags.add_classes_to_paragraphs import (
    keep_tables_with_following_notes,
)
from nofos.tests_nofos.test_editable_introduction import fy27_docx


class NoteWorkflowTests(TestCase):
    def test_word_import_and_both_document_renderers(self):
        output = BytesIO()
        with ZipFile(BytesIO(fy27_docx())) as source:
            with ZipFile(output, "w", ZIP_DEFLATED) as target:
                for name in source.namelist():
                    data = source.read(name)
                    if name == "word/document.xml":
                        needle = b"Distinctive source text is editable after import."
                        self.assertIn(needle, data)
                        data = data.replace(
                            needle, b"PLEASE NOTE: Keep the signed form."
                        )
                    target.writestr(name, data)
        self.client.force_login(
            BloomUser.objects.create_user(
                email="note-editor@example.test",
                password=None,
                group="bloom",
                force_password_reset=False,
            )
        )
        response = self.client.post(
            reverse("nofos:nofo_import"),
            {
                "nofo-import": SimpleUploadedFile(
                    "note.docx",
                    output.getvalue(),
                    content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        self.assertEqual(response.status_code, 302)
        nofo = Nofo.objects.get()
        html = self.client.get(reverse("nofos:nofo_view", args=[nofo.pk]))
        self.assertEqual(html.status_code, 200)
        with patch("nofos.pdf_service.docraptor.DocApi") as provider:
            provider.return_value.create_doc.return_value = b"%PDF"
            generate_nofo_pdf(
                nofo, base_url="https://example.test/nofo", is_test_pdf=True
            )
            pdf_source = provider.return_value.create_doc.call_args.args[0][
                "document_content"
            ]
        subsection = nofo.sections.get(
            subsections__callout_style="note"
        ).subsections.get(callout_style="note")
        self.assertTrue(subsection.callout_box)
        self.assertEqual(subsection.body.strip(), "**Note:** Keep the signed form.")
        edit_page = BeautifulSoup(
            self.client.get(
                reverse(
                    "nofos:subsection_edit",
                    args=[nofo.pk, subsection.section.pk, subsection.pk],
                )
            ).content,
            "html.parser",
        )
        self.assertTrue(edit_page.select_one("#callout_style").has_attr("checked"))
        self.assertFalse(edit_page.select_one("#callout_box").has_attr("checked"))
        for rendered in (html.content, pdf_source):
            note = BeautifulSoup(rendered, "html.parser").select_one(
                "div.note-callout[role=note]"
            )
            self.assertIsNotNone(note)
            self.assertEqual(
                note.get_text(strip=True, separator=" "), "Note: Keep the signed form."
            )
            self.assertEqual(note.strong.get_text(), "Note:")


class NoteParagraphTests(SimpleTestCase):
    def test_normalizes_only_prefix_and_preserves_inline_body(self):
        for prefix in (
            "<strong>PLEASE NOTE:</strong>",
            "NOTE:",
            "Please note:",
            "<strong>Please note</strong><strong>:</strong>",
            "Note&nbsp;–",
            "N.B.",
            "N. B.:",
        ):
            with self.subTest(prefix=prefix):
                soup = BeautifulSoup(
                    f'<p>{prefix}&nbsp;Keep <em>THIS</em> <a href="/guide">link</a>.</p>',
                    "html.parser",
                )
                normalize_note_labels(soup)
                expected = (
                    f'<p {NOTE_CALLOUT_MARKER}="true"><strong>Note:</strong> '
                    'Keep <em>THIS</em> <a href="/guide">link</a>.</p>'
                )
                self.assertEqual(str(soup), expected)
                normalize_note_labels(soup)
                self.assertEqual(str(soup), expected)

    def test_leaves_ordinary_prose_and_nonformatting_prefixes_alone(self):
        for body in (
            "Please note that forms are due Friday.",
            "Attach the form. Please note: retain a copy.",
            "Note where to sign.",
            '<a href="/guidance">Note:</a> Read more.',
            '<span id="anchor">Note:</span> Read more.',
            '<img src="cover.png"/>Note: Read more.',
            "Note<br/>: Read more.",
            "Note that applicants must submit: (1) a budget.",
            "Note the following requirements: budget, narrative.",
            "Notes from the webinar: slides are posted.",
        ):
            with self.subTest(body=body):
                soup = BeautifulSoup(f"<p>{body}</p>", "html.parser")
                original = str(soup)
                normalize_note_labels(soup)
                self.assertEqual(str(soup), original)

    def test_keeps_table_with_next_standalone_note_without_styling_notes(self):
        rendered = BeautifulSoup(
            keep_tables_with_following_notes(
                '<table id="keep"><tr><td><strong>Note:</strong> Flat.</td>'
                "<td><p>Note: Nested.</p><p>Other.</p></td></tr></table>"
                "<p> </p><p><strong>Note:</strong> After the table.</p>"
                '<table id="ordinary"><tr><td>Other.</td></tr></table>'
                '<p><img src="example.png"/></p><p>Note: Not attached to the table.</p>'
                "<ol><li><p>Note: In a list item.</p></li></ol>"
                "<p>Note: Between two items of one list.</p><ol><li>Next</li></ol>"
            ),
            "html.parser",
        )
        # The former grey note style is gone: no note paragraph gets a class.
        self.assertFalse(rendered.select("p[class], td[class], .nofo-note"))
        self.assertEqual(
            [t["id"] for t in rendered.select(".table--with-following-note")], ["keep"]
        )
        self.assertFalse(rendered.select("[role], [aria-level]"))


class NoteCalloutImportTests(SimpleTestCase):
    def normalize(self, html):
        soup = BeautifulSoup(html, "html.parser")
        normalize_note_labels(soup)
        return soup

    def test_audience_labels_are_standardized_and_kept(self):
        for source, label in (
            ("Note for applicants: Budget.", "Note for applicants:"),
            ("<strong>Note for applicants:</strong> Budget.", "Note for applicants:"),
            (
                "Note (competing supplement applicants): Budget.",
                "Note (competing supplement applicants):",
            ),
            (
                "NOTE FOR new applicants (FY 2027 only) - Budget.",
                "Note FOR new applicants (FY 2027 only):",
            ),
            (
                "please note for non-profit applicants: Budget.",
                "Note for non-profit applicants:",
            ),
        ):
            with self.subTest(source=source):
                paragraph = self.normalize(f"<p>{source}</p>").p
                self.assertEqual(paragraph.strong.get_text(), label)
                self.assertEqual(paragraph.get_text(), f"{label} Budget.")
                self.assertEqual(paragraph[NOTE_CALLOUT_MARKER], "true")

    def test_bare_label_line_takes_the_following_paragraph(self):
        soup = self.normalize(
            "<p><strong>Note:</strong></p><p> </p><p>Sites do <em>not</em> transfer.</p>"
            "<p>After.</p>"
        )
        paragraphs = soup.find_all("p")
        self.assertEqual(paragraphs[0].get_text(), "Note: Sites do not transfer.")
        self.assertEqual(paragraphs[0][NOTE_CALLOUT_MARKER], "true")
        self.assertEqual(paragraphs[0].em.get_text(), "not")
        self.assertEqual(paragraphs[-1].get_text(), "After.")

    def test_bare_label_line_before_a_list_or_label_is_left_alone(self):
        for following in (
            "<ul><li>Item</li></ul>",
            "<p>Note: Another.</p>",
            "<h3>Next</h3>",
        ):
            with self.subTest(following=following):
                soup = self.normalize(f"<p>Note:</p>{following}")
                self.assertFalse(soup.p.has_attr(NOTE_CALLOUT_MARKER))
                self.assertEqual(soup.p.get_text(), "Note:")

    def test_only_standalone_notes_become_callouts(self):
        soup = self.normalize(
            "<ol><li><p>Note: In a list item.</p></li></ol>"
            "<p>Note: Between items.</p><ol><li>Next</li></ol>"
            "<table><tr><td><p>Note: In a cell.</p></td></tr></table>"
            "<ul><li>Last</li></ul><p>Note: After a list.</p>"
        )
        marked = [p.get_text() for p in soup.select(f"p[{NOTE_CALLOUT_MARKER}]")]
        self.assertEqual(marked, ["Note: After a list."])
        # Labels are still standardized everywhere.
        self.assertEqual(len(soup.select("p > strong")), 4)

    def test_builder_import_creates_note_callout_subsections(self):
        result = process_document_content(
            "<html><body><h1>Step 1: Review the opportunity</h1><p>Intro.</p>"
            "<p>Note for applicants:</p><p>Sites do not transfer.</p><p>After.</p>"
            "<ol><li>a</li></ol><p>Note: Between.</p><ol><li>b</li></ol>"
            "<table><tr><td><p>Note: In a callout box.</p></td></tr></table>"
            "</body></html>",
            builder_import=True,
        )
        subsections = result.sections[0]["subsections"]
        self.assertEqual(
            [(s["is_callout_box"], s.get("callout_style")) for s in subsections],
            [(False, None), (True, "note"), (False, None), (True, None)],
        )
        note_body = "".join(str(tag) for tag in subsections[1]["body"])
        self.assertEqual(
            note_body,
            "<p><strong>Note for applicants:</strong> Sites do not transfer.</p>",
        )
        self.assertNotIn(NOTE_CALLOUT_MARKER, str(result.soup))

    def test_compare_and_composer_processing_do_not_create_note_callouts(self):
        result = process_document_content(
            "<html><body><h1>Step 1</h1><p>Note: Keep it.</p></body></html>"
        )
        self.assertFalse(
            any(s["is_callout_box"] for s in result.sections[0]["subsections"])
        )


class NoteCalloutRenderTests(SimpleTestCase):
    def render(self, template, **context):
        return BeautifulSoup(Template(template).render(Context(context)), "html.parser")

    def test_note_callout_renders_as_a_div_note_without_box_markup(self):
        subsection = SimpleNamespace(
            body="**Note for applicants:** Keep the signed form.",
            callout_box=True,
            callout_style="note",
            html_id="note-1",
            html_class="",
            name="",
            tag="",
        )
        html = self.render(
            '{% include "includes/callout_box.html" with subsection=subsection nofo=nofo only %}',
            subsection=subsection,
            nofo=SimpleNamespace(icon_style=""),
        )
        note = html.select_one("div.note-callout")
        self.assertEqual(note["role"], "note")
        self.assertEqual(note["id"], "note-1")
        self.assertEqual(note.strong.get_text(), "Note for applicants:")
        self.assertFalse(html.select(".callout-box"))


class NoteCalloutFormTests(TestCase):
    def test_note_style_makes_a_headingless_callout(self):
        form = SubsectionCreateForm(
            data={"callout_style": "note", "body": "**Note:** Keep it."}
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertTrue(form.cleaned_data["callout_box"])
        self.assertEqual(form.cleaned_data["callout_style"], "note")

    def test_note_style_rejects_a_heading(self):
        form = SubsectionCreateForm(
            data={
                "name": "Heading",
                "tag": "h4",
                "callout_style": "note",
                "body": "Text",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("callout_style", form.errors)

    def test_callout_box_and_note_are_one_choice(self):
        form = SubsectionCreateForm(
            data={"callout_box": "on", "callout_style": "note", "body": "Text"}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("callout_style", form.errors)

    def test_missing_style_defaults_to_box(self):
        form = SubsectionCreateForm(data={"callout_box": "on", "body": "Text"})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["callout_style"], "box")


def _contrast(foreground, background):
    def luminance(hex_color):
        channels = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [
            c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
            for c in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    lighter, darker = sorted(
        (luminance(foreground), luminance(background)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


class NoteCalloutThemeTests(SimpleTestCase):
    def test_every_selectable_theme_defines_accessible_note_colors(self):
        static = Path(settings.BASE_DIR) / "bloom_nofos" / "static"
        for theme, _label in THEME_CHOICES:
            name = theme.split("-", 1)[1]
            with self.subTest(theme=theme):
                css = (static / f"theme-opdiv-{name}.css").read_text()
                values = dict(
                    re.findall(
                        r"--color--note-(rule|tint|label):\s*(#[0-9a-fA-F]{6})", css
                    )
                )
                self.assertEqual(set(values), {"rule", "tint", "label"})
                self.assertGreaterEqual(_contrast(values["rule"], "#ffffff"), 3)
                self.assertGreaterEqual(_contrast(values["label"], values["tint"]), 4.5)
                self.assertGreaterEqual(_contrast("#000000", values["tint"]), 4.5)


class NoteLabelWarningTests(SimpleTestCase):
    def test_has_note_label(self):
        for body in (
            "**Note:** Keep it.",
            "Note for applicants: Keep it.",
            "**NOTE (new applicants):** Keep it.",
            "__Note -__ Keep it.",
            "N.B. Keep it.",
        ):
            with self.subTest(body=body):
                self.assertTrue(has_note_label(body))
        for body in ("Keep it.", "**Notes from the webinar:** x", "", None):
            with self.subTest(body=body):
                self.assertFalse(has_note_label(body))

    def test_pdf_keeps_a_note_with_the_content_before_it(self):
        css = (
            Path(settings.BASE_DIR) / "bloom_nofos" / "static" / "theme-base.css"
        ).read_text()
        rule = re.search(r"@media print \{.*?\.note-callout \{([^}]*)\}", css, re.S)
        self.assertIn("break-before: avoid", rule.group(1))
        self.assertIn(".note-callout.page-break-before", css)


class NoteCalloutEditorTests(TestCase):
    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="note-edge@example.test",
            password=None,
            group="bloom",
            force_password_reset=False,
        )
        self.client.force_login(self.user)
        self.nofo = Nofo.objects.create(
            title="Note edge NOFO", group="bloom", opdiv="HRSA"
        )
        self.intro = Section.objects.create(
            nofo=self.nofo,
            name="Before you get started",
            html_id="before-you-get-started",
            order=1,
            role="introduction",
        )

    def note(self, section, body="**Note:** Keep the signed form."):
        return Subsection.objects.create(
            section=section,
            order=section.subsections.count() + 1,
            callout_box=True,
            callout_style="note",
            body=body,
        )

    def edit_form(self, subsection, **data):
        return SubsectionEditForm(
            instance=subsection, data={"body": subsection.body, **data}
        )

    def test_introduction_note_can_be_kept_or_turned_into_text(self):
        subsection = self.note(self.intro)
        self.assertTrue(self.edit_form(subsection, callout_style="note").is_valid())
        form = self.edit_form(subsection)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertFalse(form.cleaned_data["callout_box"])
        self.assertFalse(self.edit_form(subsection, callout_box="on").is_valid())

    def test_label_warning_shows_only_for_notes_without_a_label(self):
        for body, hidden in (
            ("**Note:** Keep the signed form.", True),
            ("Keep the signed form.", False),
        ):
            with self.subTest(body=body):
                subsection = self.note(self.intro, body=body)
                page = BeautifulSoup(
                    self.client.get(
                        reverse(
                            "nofos:subsection_edit",
                            args=[self.nofo.pk, self.intro.pk, subsection.pk],
                        )
                    ).content,
                    "html.parser",
                )
                warning = page.select_one("#note-label-warning")
                self.assertEqual(warning.has_attr("hidden"), hidden)
                self.assertFalse(page.select_one("#callout_style").has_attr("disabled"))
                self.assertTrue(page.select_one("#callout_box").has_attr("disabled"))
