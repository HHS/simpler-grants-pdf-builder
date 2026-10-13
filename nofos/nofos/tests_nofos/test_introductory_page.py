"""Synthetic Word destinations and isolated old/new registration families."""

from io import BytesIO
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

from bs4 import BeautifulSoup
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.introductory_page import (
    capture_introductory_page,
    introductory_family_from_soup,
)
from nofos.models import Nofo
from nofos.nofo import decompose_before_you_begin_section, suggest_nofo_before_you_begin
from nofos.views import duplicate_nofo


def introductory_docx(
    name="Before You Get Started",
    bookmark="_Toc12345",
    number="HRSA-27-001",
    split_heading=False,
):
    """A real minimal DOCX with Heading 2 plus a Word internal bookmark link."""
    stream = BytesIO()
    heading_runs = f"<w:r><w:t>{name}</w:t></w:r>"
    if split_heading:
        heading_runs = '<w:r><w:t xml:space="preserve">Before You Get </w:t></w:r><w:r><w:rPr><w:b/></w:rPr><w:t>Star</w:t></w:r><w:r><w:t>ted</w:t></w:r>'
    with ZipFile(stream, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>',
        )
        archive.writestr(
            "_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        )
        archive.writestr(
            "word/_rels/document.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>',
        )
        archive.writestr(
            "word/styles.xml",
            '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/></w:style><w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/></w:style></w:styles>',
        )
        archive.writestr(
            "word/document.xml",
            f"""<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:bookmarkStart w:id="1" w:name="{bookmark}"/>{heading_runs}<w:bookmarkEnd w:id="1"/></w:p>
<w:p><w:r><w:t>Distinctive source text MUST NOT publish.</w:t></w:r></w:p>
<w:p><w:r><w:t>To register:</w:t></w:r></w:p>
<w:p><w:r><w:t>Another source instruction.</w:t></w:r></w:p>
<w:p><w:r><w:t>Opportunity Number: {number}</w:t></w:r></w:p>
<w:p><w:r><w:t>Opdiv: HRSA</w:t></w:r></w:p>
<w:p><w:r><w:t>Opportunity Name: Synthetic introductory page review</w:t></w:r></w:p>
<w:p><w:r><w:t>Application Deadline: October 30, 2027</w:t></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>Step 1: Review the Opportunity</w:t></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="Heading3"/></w:pPr><w:r><w:t>Basic information</w:t></w:r></w:p>
<w:p><w:r><w:t>Synthetic program information.</w:t></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>Step 2: Get Ready to Apply</w:t></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="Heading3"/></w:pPr><w:r><w:t>Registration</w:t></w:r></w:p>
<w:p><w:r><w:t xml:space="preserve">See </w:t></w:r><w:hyperlink w:anchor="{bookmark}"><w:r><w:t>{name}</w:t></w:r></w:hyperlink><w:r><w:t xml:space="preserve"> to learn how.</w:t></w:r></w:p>
</w:body></w:document>""",
        )
    return stream.getvalue()


class IntroductoryDestinationTests(SimpleTestCase):
    def test_unique_heading_capture_survives_serialization_and_bounded_consumption(
        self,
    ):
        for name, family in [
            (" Before   You Get Started ", "get_started"),
            ("Before You Begin", "legacy"),
        ]:
            with self.subTest(name=name):
                soup = capture_introductory_page(
                    BeautifulSoup(
                        f'<h2><a id="_Toc123"></a>{name}</h2><p>Source prose</p><h3>Get registered</h3><p>To register:</p><p>Discard this too</p><p>Opdiv: HRSA</p><h2>Appendix</h2><p>Retain appendix</p><p>See <a href="#_Toc123">{name}</a> to learn how.</p>',
                        "html.parser",
                    )
                )
                decompose_before_you_begin_section(soup)
                reparsed = BeautifulSoup(str(soup), "html.parser")
                self.assertEqual(introductory_family_from_soup(reparsed), family)
                self.assertNotIn("Source prose", str(soup))
                self.assertNotIn("Discard this too", str(soup))
                self.assertIn("Opdiv: HRSA", str(soup))
                self.assertIn("Retain appendix", str(soup))
                self.assertEqual(soup.a["href"], "#section--before-you-begin")
                self.assertEqual(soup.a.text, name)

    def test_conflicting_or_duplicate_headings_keep_legacy_and_unlink_consumed_targets(
        self,
    ):
        for second in ["Before You Begin", "Before You Get Started"]:
            soup = capture_introductory_page(
                BeautifulSoup(
                    f'<h2 id="new">Before You Get Started</h2><h2 id="old">{second}</h2><h2>Step 1</h2><p><a href="#new">Authored label</a></p>',
                    "html.parser",
                )
            )
            self.assertEqual(introductory_family_from_soup(soup), "")
            self.assertIsNone(soup.find("a", href="#new"))
            self.assertIn("Authored label", str(soup))

    def test_capture_remaps_actual_destination_independently_of_page_setting(self):
        soup = capture_introductory_page(
            BeautifulSoup(
                '<h2 id="intro">Before You Get Started</h2><h2>Step 1</h2><p><a href="#intro">Before You Get Started</a><a href="https://example.com">Before You Get Started</a><a href="#missing">Missing</a></p>',
                "html.parser",
            ),
        )
        self.assertIsNotNone(soup.find("a", href="#section--before-you-begin"))
        self.assertIsNotNone(soup.find("a", href="https://example.com"))
        self.assertIsNotNone(soup.find("a", href="#missing"))

    def test_nonheading_text_does_not_select_family(self):
        soup = capture_introductory_page(
            BeautifulSoup("<p>Before You Get Started</p><h2>Step 1</h2>", "html.parser")
        )
        self.assertEqual(introductory_family_from_soup(soup), "")

    def test_heading_levels_and_case_are_structural_not_link_text_guesses(self):
        for level in range(1, 7):
            soup = capture_introductory_page(
                BeautifulSoup(
                    f'<h{level}>bEfOrE  yOu GET started</h{level}><p><a href="#absent">Before You Get Started</a></p>',
                    "html.parser",
                )
            )
            self.assertEqual(introductory_family_from_soup(soup), "get_started")
            self.assertEqual(soup.a["href"], "#absent")

    def test_inline_word_run_split_does_not_invent_heading_whitespace(self):
        soup = capture_introductory_page(
            BeautifulSoup(
                '<h2 id="intro">Before You Get <strong>Star</strong>ted</h2><h2>Step 1</h2><p><a href="#intro">Before You Get Started</a></p>',
                "html.parser",
            )
        )
        self.assertEqual(introductory_family_from_soup(soup), "get_started")
        self.assertEqual(soup.a["href"], "#section--before-you-begin")
        decompose_before_you_begin_section(soup)
        self.assertIsNone(soup.find(id="intro"))

    def test_duplicate_id_is_not_remapped_to_generated_destination(self):
        soup = capture_introductory_page(
            BeautifulSoup(
                '<h2 id="duplicate">Before You Get Started</h2><h2 id="duplicate">Step 1</h2><p><a href="#duplicate">Text</a></p>',
                "html.parser",
            )
        )
        self.assertIsNone(soup.find("a", href=True))

    def test_lower_metadata_and_note_headings_preserve_content(self):
        for boundary in [
            "<h3>Metadata</h3><p>OpDiv: HRSA</p><p>Opportunity number: HRSA-27-001</p>",
            "<h4>Endnotes</h4><p>Retain citation</p>",
        ]:
            soup = capture_introductory_page(
                BeautifulSoup(
                    f"<h2>Before You Get Started</h2><p>Consume source</p>{boundary}",
                    "html.parser",
                )
            )
            decompose_before_you_begin_section(soup)
            self.assertNotIn("Consume source", str(soup))
            for paragraph in BeautifulSoup(boundary, "html.parser").find_all("p"):
                self.assertIn(paragraph.text, str(soup))

    def test_defaults_family_and_variant_are_independent(self):
        for family, group, theme, variant in [
            ("legacy", "nih", "portrait-hrsa-white", "hrsa"),
            ("get_started", "nih", "portrait-hrsa-white", "full"),
            ("get_started", "nih", "portrait-cdc-blue", "era"),
            ("get_started", "bloom", "portrait-nih-white", "full"),
        ]:
            self.assertEqual(
                suggest_nofo_before_you_begin(group, theme, family), variant
            )


class IntroductoryImportTests(TestCase):
    def test_normal_word_export_has_generated_targets_only_for_explicit_families(self):
        for family in ["legacy", "get_started", ""]:
            nofo = Nofo.objects.create(
                title="Synthetic export",
                introductory_page_family=family,
                group="bloom",
                opdiv="HHS",
            )
            html = self.client.get(
                reverse("nofos:nofo_export", kwargs={"pk": nofo.pk})
            ).content.decode()
            self.assertEqual('id="section--before-you-begin"' in html, bool(family))
            if family:
                self.assertIn(nofo.introductory_page_title, html)

    def test_disabled_page_render_preserves_stored_authored_prose(self):
        from nofos.templatetags.introductory_page_links import introductory_page_links

        nofo = Nofo(before_you_begin="none")
        html = '<p>See <a href="#section--before-you-begin">Before You Get Started</a> to learn how. <a href="https://example.com">Other</a></p>'
        rendered = introductory_page_links(html, nofo)
        self.assertNotIn('href="#section--before-you-begin"', rendered)
        self.assertIn(
            "Before You Get Started to learn how.",
            BeautifulSoup(rendered, "html.parser").text,
        )
        self.assertIn('href="https://example.com"', rendered)
        self.assertIn('href="#section--before-you-begin"', html)

    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="intro-review@example.com",
            password=None,
            group="bloom",
            force_password_reset=False,
        )
        self.client.force_login(self.user)

    def upload(
        self,
        url,
        name="Before You Get Started",
        bookmark="_Toc12345",
        number="HRSA-27-001",
    ):
        return self.client.post(
            url,
            {
                "nofo-import": SimpleUploadedFile(
                    "synthetic-intro.docx",
                    introductory_docx(name, bookmark, number),
                    content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

    def test_real_word_heading_and_named_bookmarks_import_into_generated_page(self):
        for name in ["Before You Begin", "Before You Get Started"]:
            for bookmark in ["_Toc12345", "MyIntroductoryPage"]:
                with self.subTest(name=name, bookmark=bookmark):
                    response = self.upload(reverse("nofos:nofo_import"), name, bookmark)
                    self.assertEqual(response.status_code, 302)
                    nofo = Nofo.objects.latest("created")
                    self.assertEqual(
                        nofo.introductory_page_family,
                        "get_started" if "Started" in name else "legacy",
                    )
                    self.assertEqual(
                        nofo.before_you_begin, "full" if "Started" in name else "hrsa"
                    )
                    body = " ".join(
                        nofo.sections.values_list("name", flat=True)
                    ) + " ".join(
                        s.body
                        for section in nofo.sections.all()
                        for s in section.subsections.all()
                    )
                    self.assertNotIn("Distinctive source", body)
                    self.assertIn("#section--before-you-begin", body)
                    self.assertIn(name, body)

    def test_new_family_preserves_saved_variant_on_confirmed_reimport_and_duplication(
        self,
    ):
        self.upload(reverse("nofos:nofo_import"), "Before You Begin")
        nofo = Nofo.objects.latest("created")
        for variant in ["full", "era", "hrsa", "sole_source", "none"]:
            nofo.before_you_begin = variant
            nofo.save()
            response = self.upload(
                reverse("nofos:nofo_import_overwrite", kwargs={"pk": nofo.pk}),
                number="HRSA-27-002",
            )
            self.assertEqual(response.status_code, 302)
            if response.url.endswith("confirm-overwrite") or "confirm" in response.url:
                response = self.client.post(response.url)
            nofo.refresh_from_db()
            self.assertEqual(nofo.introductory_page_family, "get_started")
            self.assertEqual(nofo.before_you_begin, variant)
            copied = duplicate_nofo(nofo)
            self.assertEqual(copied.introductory_page_family, "get_started")
            self.assertEqual(copied.before_you_begin, variant)

    def test_disabled_reimport_keeps_link_for_later_reenable(self):
        for name in ("Before You Begin", "Before You Get Started"):
            with self.subTest(name=name):
                self.upload(reverse("nofos:nofo_import"), name)
                nofo = Nofo.objects.latest("created")
                nofo.before_you_begin = "none"
                nofo.save()
                response = self.upload(
                    reverse("nofos:nofo_import_overwrite", kwargs={"pk": nofo.pk}), name
                )
                self.assertEqual(response.status_code, 302)
                nofo.refresh_from_db()
                bodies = " ".join(
                    s.body
                    for section in nofo.sections.all()
                    for s in section.subsections.all()
                )
                self.assertIn("#section--before-you-begin", bodies)
                url = reverse("nofos:nofo_view", kwargs={"pk": nofo.pk})
                soup = BeautifulSoup(self.client.get(url).content, "html.parser")
                self.assertIsNone(soup.find("a", href="#section--before-you-begin"))
                nofo.before_you_begin = "full"
                nofo.save()
                soup = BeautifulSoup(self.client.get(url).content, "html.parser")
                self.assertIsNotNone(
                    soup.find("a", href="#section--before-you-begin", string=name)
                )
                self.assertIsNotNone(soup.find(id="section--before-you-begin"))

    def test_generated_introductory_links_are_not_reported_broken_when_enabled(self):
        from nofos.nofo import find_broken_links

        self.upload(reverse("nofos:nofo_import"))
        nofo = Nofo.objects.latest("created")
        self.assertEqual(find_broken_links(nofo), [])
        subsection = nofo.sections.last().subsections.last()
        subsection.body += "\n\n[Missing destination](#unrelated-missing)"
        subsection.save()
        self.assertEqual(
            [link["link_href"] for link in find_broken_links(nofo)],
            ["#unrelated-missing"],
        )
        nofo.before_you_begin = "none"
        nofo.save()
        self.assertEqual(
            [link["link_href"] for link in find_broken_links(nofo)],
            ["#unrelated-missing"],
        )
        subsection.refresh_from_db()
        self.assertIn("#section--before-you-begin", subsection.body)
        self.assertIn("Before You Get Started", subsection.body)
        nofo.before_you_begin = "full"
        nofo.save()
        self.assertEqual(
            [link["link_href"] for link in find_broken_links(nofo)],
            ["#unrelated-missing"],
        )
        self.assertIn("#section--before-you-begin", subsection.body)

    def test_failed_reimport_restores_saved_family_variant_and_content(self):
        self.upload(reverse("nofos:nofo_import"), "Before You Begin")
        nofo = Nofo.objects.latest("created")
        names = list(nofo.sections.values_list("name", flat=True))
        with patch(
            "nofos.views.add_headings_to_document",
            side_effect=ValueError("synthetic failure"),
        ):
            self.upload(reverse("nofos:nofo_import_overwrite", kwargs={"pk": nofo.pk}))
        nofo.refresh_from_db()
        self.assertEqual(nofo.introductory_page_family, "legacy")
        self.assertEqual(nofo.before_you_begin, "hrsa")
        self.assertEqual(list(nofo.sections.values_list("name", flat=True)), names)

    def test_actual_word_split_heading_runs_keep_family_and_link(self):
        response = self.client.post(
            reverse("nofos:nofo_import"),
            {
                "nofo-import": SimpleUploadedFile(
                    "synthetic-split.docx",
                    introductory_docx(split_heading=True),
                    content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        self.assertEqual(response.status_code, 302)
        nofo = Nofo.objects.latest("created")
        self.assertEqual(nofo.introductory_page_family, "get_started")
        bodies = " ".join(
            s.body for section in nofo.sections.all() for s in section.subsections.all()
        )
        self.assertIn("#section--before-you-begin", bodies)

    def test_isolated_new_registration_variants_and_legacy_body(self):
        for variant in ["full", "era", "sole_source", "hrsa"]:
            nofo = Nofo(
                before_you_begin=variant,
                introductory_page_family="get_started",
                application_deadline="October 30, 2027",
            )
            rendered = render_to_string(
                "includes/byb_page.html",
                {
                    "nofo": nofo,
                    "step_2_section": {"name": "Step 2", "html_id": "step-2"},
                },
            )
            soup = BeautifulSoup(rendered, "html.parser")
            self.assertEqual(soup.h2.text, "Before you get started")
            self.assertEqual(
                [h.text for h in soup.find_all("h4")],
                ["SAM.gov"]
                + ([] if variant == "sole_source" else ["Grants.gov"])
                + (["eRA Commons"] if variant == "era" else [])
                + ["Apply by the application due date"],
            )
            self.assertEqual([h.text for h in soup.find_all("h3")], ["Get registered"])
            self.assertIsNone(soup.find("a", href="#step-2"))
            self.assertNotIn("STEP 2 SECTION MISSING", rendered)
            self.assertNotIn("Application and funding requirements", rendered)
            self.assertIn("October 30, 2027", rendered)
            self.assertIn("Alt + Left Arrow", rendered)
            nofo.introductory_page_family = "legacy"
            legacy = render_to_string("includes/byb_page.html", {"nofo": nofo})
            self.assertIn("Before you begin", legacy)
            self.assertNotIn("Get registered", legacy)
