"""Conservative eligibility repair, using synthetic sources rather than NOFOs."""

from bs4 import BeautifulSoup
from compare.models import CompareDocument
from composer.models import ContentGuide
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from martor.templatetags.martortags import safe_markdown

from nofos.content_processing import (
    ELIGIBLE_ORGANIZATION_CATEGORIES,
    process_document_content,
    repair_eligibility_organization_lists,
)
from nofos.models import Nofo
from nofos.subsection_conflicts import version_token
from nofos.tests_nofos.test_word_lists import docx, level, paragraph

INTRO = "These types of *domestic organizations may apply:"
DOMESTIC = "“Domestic” means the 50 states and territories."
LABEL = "Additional information on eligibility"
RESTRICTION = "Individuals are not eligible applicants under this NOFO."
# Literal issue #1190 example, deliberately independent of the production vocabulary.
ISSUE_UNRESTRICTED = (
    "Unrestricted (i.e., open to any type of entity above), subject to any clarification "
    "in text field entitled ‘Additional Information on Eligibility’"
)
DOUBLE_QUOTED_UNRESTRICTED = (
    "Unrestricted (i.e., open to any type of entity above), subject to any clarification "
    "in text field entitled “Additional Information on Eligibility”"
)
PREFIX = (
    "<p>Opdiv: HRSA</p><p>Opportunity number: SYNTHETIC-ELIGIBILITY</p>"
    "<h1>Step 1: Review the opportunity</h1><h2>Eligibility</h2>"
    "<h3>Types of eligible organizations</h3>"
)


def html_source(categories=None, *, intro=INTRO, tail=None):
    categories = (
        categories
        if categories is not None
        else ("<p>State governments</p><p>Small businesses</p>")
    )
    tail = (
        tail
        if tail is not None
        else (f"<p>{DOMESTIC}</p><p><strong>{LABEL}</strong></p><p>{RESTRICTION}</p>")
    )
    return PREFIX + f"<p>{intro}</p>" + categories + tail


class EligibilityRepairTests(SimpleTestCase):
    def repair(self, html):
        soup = BeautifulSoup("<body>" + html + "</body>", "html.parser")
        repair_eligibility_organization_lists(soup)
        return soup

    def assert_noop(self, html):
        before = BeautifulSoup("<body>" + html + "</body>", "html.parser")
        self.assertEqual(str(self.repair(html)), str(before))

    def test_all_reviewed_categories_and_idempotence(self):
        categories = sorted(ELIGIBLE_ORGANIZATION_CATEGORIES)
        self.assertEqual(
            len(categories), 16
        )  # Fifteen types; two reviewed Unrestricted spellings.
        soup = self.repair(html_source("".join(f"<p>{x}</p>" for x in categories)))
        self.assertEqual([x.text for x in soup.ul.find_all("li")], categories)
        before = str(soup)
        repair_eligibility_organization_lists(soup)
        self.assertEqual(str(soup), before)

    def test_exact_issue_unrestricted_label_through_repair_and_shared_core(self):
        expected = ["State governments", ISSUE_UNRESTRICTED]
        html = html_source("".join(f"<p>{label}</p>" for label in expected))
        for soup in (self.repair(html), process_document_content(html).soup):
            with self.subTest(soup=str(soup)):
                self.assertIsNotNone(soup.ul)
                self.assertEqual(
                    [item.text for item in soup.ul.find_all("li")], expected
                )
                self.assertIsNone(soup.find("p", string=DOMESTIC).find_parent("li"))
                before = str(soup)
                repair_eligibility_organization_lists(soup)
                self.assertEqual(str(soup), before)

    def test_existing_double_quote_label_remains_supported(self):
        expected = ["State governments", DOUBLE_QUOTED_UNRESTRICTED]
        html = html_source("".join(f"<p>{label}</p>" for label in expected))
        self.assertEqual(
            [item.text for item in self.repair(html).ul.find_all("li")], expected
        )

    def test_unreviewed_unrestricted_quote_and_wording_variants_remain_noops(self):
        for label in (
            ISSUE_UNRESTRICTED.replace("‘", "'").replace("’", "'"),
            ISSUE_UNRESTRICTED.replace("’", "”"),
            ISSUE_UNRESTRICTED.replace("‘", "“"),
            ISSUE_UNRESTRICTED.replace(
                "Additional Information on Eligibility", "Eligibility information"
            ),
            ISSUE_UNRESTRICTED + ".",
        ):
            with self.subTest(label=label):
                self.assert_noop(html_source(f"<p>State governments</p><p>{label}</p>"))

    def test_explicit_intro_variants_and_comparison_only_normalization(self):
        for intro in (
            INTRO,
            "These types of domestic organizations may apply.",
            "The following types of domestic organizations may apply:",
            "The following domestic organizations are eligible to apply",
            " THE FOLLOWING\u00a0 TYPES of * domestic\n organizations MAY APPLY: ",
        ):
            with self.subTest(intro=intro):
                soup = self.repair(html_source(intro=intro))
                self.assertEqual(len(soup.ul.find_all("li")), 2)
                self.assertEqual(soup.h3.find_next_sibling("p").text, intro)

    def test_subsets_reordering_and_safe_boundaries(self):
        for categories in (
            ["Small businesses"],
            ["Private institutions of higher education", "County governments"],
        ):
            for tail in (
                "",
                "<h4>Details</h4><p>Unknown content</p>",
                "<h3>Next subsection</h3><p>Unknown content</p>",
                "<table><tr><td>Unknown content</td></tr></table>",
                f"<p>{DOMESTIC}</p><p>Unknown content</p>",
                f"<p><strong>{LABEL}</strong></p><p>{RESTRICTION}</p>",
            ):
                with self.subTest(categories=categories, tail=tail):
                    soup = self.repair(
                        html_source(
                            "<p> </p>".join(f"<p>{x}</p>" for x in categories),
                            tail=tail,
                        )
                    )
                    self.assertEqual(
                        [x.text for x in soup.ul.find_all("li")], categories
                    )
                    self.assertNotIn("Unknown content", soup.ul.text)

    def test_unknown_category_or_prose_never_produces_partial_list(self):
        for unknown in (
            "Regional public agencies",
            "Eligible organizations must be incorporated.",
            "Others (see text field entitled eligibility)",
            "State governments and others",
            "Domestic corporations",
            "Domestic organizations may not apply",
        ):
            for after in ("", "<p>Small businesses</p>"):
                with self.subTest(unknown=unknown, after=after):
                    self.assert_noop(
                        html_source(f"<p>County governments</p><p>{unknown}</p>{after}")
                    )

    def test_existing_and_mixed_lists_anywhere_in_subsection_are_noops(self):
        for existing in (
            "<ul><li>State governments</li></ul>",
            "<ol><li>State governments</li></ol>",
            "<p>State governments</p><ul><li>Small businesses</li></ul>",
            "<p>State governments</p>"
            + f"<p>{DOMESTIC}</p>"
            + "<p>Restriction:</p><ul><li>Keep this restriction</li></ul>",
        ):
            with self.subTest(existing=existing):
                self.assert_noop(html_source(existing))

    def test_missing_context_negative_intros_and_nonimmediate_categories(self):
        for intro in (
            "Foreign organizations may apply",
            "Domestic organizations may not apply",
            "The following individuals may apply",
            "Other applicants may apply",
            "These domestic organizations may apply",
            "These types of domestic organizations may apply later",
        ):
            self.assert_noop(html_source(intro=intro))
        for html in (
            html_source().replace("<h2>Eligibility</h2>", "<h2>Summary</h2>"),
            html_source().replace("<h3>Types of eligible organizations</h3>", ""),
            html_source().replace(
                "<h2>Eligibility</h2>", "<h2>Eligibility</h2><h2>Other</h2>"
            ),
            html_source("<p>Unrecognized opening</p><p>State governments</p>"),
            html_source("<p>State governments<img src='image.png'></p>"),
            html_source("<p>State governments</p><!-- unknown boundary -->"),
            html_source("<p>State governments<!-- unknown content --></p>"),
            html_source("<p>State governments</p>stray text"),
            html_source("<div><p>State governments</p></div>"),
            html_source("<p>State governments</p><div>Unknown boundary</div>"),
            html_source().replace("<h3>", "<h2>").replace("</h3>", "</h2>"),
        ):
            with self.subTest(html=html):
                self.assert_noop(html)

    def test_rich_content_attributes_and_blank_separators_are_not_rebuilt(self):
        categories = (
            '<p id="agency" class="source"><a id="bookmark"></a>'
            "<strong>State</strong> <em>governments</em></p><p> </p>"
            '<p><a href="https://example.org/eligibility">Small businesses</a></p>'
        )
        soup = self.repair(html_source(categories))
        self.assertEqual(soup.ul.li.attrs, {"id": "agency", "class": ["source"]})
        self.assertEqual(soup.ul.strong.text, "State")
        self.assertEqual(soup.ul.em.text, "governments")
        self.assertIsNotNone(soup.ul.find(id="bookmark"))
        self.assertEqual(
            soup.ul.find("a", href=True)["href"], "https://example.org/eligibility"
        )
        self.assertIsNotNone(soup.find("p", string=" "))
        self.assertIsNone(soup.find("p", string=DOMESTIC).find_parent("li"))


def word_source(*, native=False, categories=None):
    styles = "".join(
        f'<w:style w:type="paragraph" w:styleId="Heading{n}">'
        f'<w:name w:val="heading {n}"/></w:style>'
        for n in (1, 2, 3)
    )
    body = "".join(
        paragraph(x, num=None)
        for x in (
            "Opdiv: HRSA",
            "Opportunity number: SYNTHETIC-ELIGIBILITY",
        )
    )
    body += paragraph("Step 1: Review the opportunity", num=None, style="Heading1")
    body += paragraph("Eligibility", num=None, style="Heading2")
    body += paragraph("Types of eligible organizations", num=None, style="Heading3")
    body += paragraph(INTRO, num=None)
    for label in (
        categories
        if categories is not None
        else ("State governments", "Small businesses")
    ):
        body += paragraph(label, num="1" if native else None)
    body += "".join(paragraph(x, num=None) for x in (DOMESTIC, LABEL, RESTRICTION))
    return docx(body, styles=styles, levels=level(0, "bullet"))


@override_settings(DEBUG=False)
class EligibilityImportTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(
            email="eligibility-test@example.com",
            password="local-test-only",
            group="bloom",
            force_password_reset=False,
            is_composer_admin=True,
        )
        self.client.force_login(user)

    def upload(self, *, word=False, native=False, url=None, html=None, categories=None):
        source = (
            word_source(native=native, categories=categories).getvalue()
            if word
            else (html or html_source()).encode()
        )
        return self.client.post(
            url or reverse("nofos:nofo_import"),
            {
                "nofo-import": SimpleUploadedFile(
                    (
                        "synthetic-eligibility.docx"
                        if word
                        else "synthetic-eligibility.html"
                    ),
                    source,
                    content_type=(
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        if word
                        else "text/html"
                    ),
                )
            },
        )

    def saved(self, document):
        body = (
            document.sections.get()
            .subsections.get(name="Types of eligible organizations")
            .body
        )
        rendered = BeautifulSoup(safe_markdown(body), "html.parser")
        self.assertEqual(
            [x.get_text(strip=True) for x in rendered.ul.find_all("li")],
            ["State governments", "Small businesses"],
        )
        for text in (DOMESTIC, LABEL, RESTRICTION):
            self.assertIsNone(rendered.find("p", string=text).find_parent("li"))
        return body

    def test_actual_html_and_word_import_reimport_and_read_do_not_compound(self):
        for word, native in ((False, False), (True, False), (True, True)):
            with self.subTest(word=word, native=native):
                self.assertEqual(self.upload(word=word, native=native).status_code, 302)
                document = Nofo.objects.latest("created")
                before = self.saved(document)
                for _ in range(2):
                    response = self.upload(
                        word=word,
                        native=native,
                        url=reverse(
                            "nofos:nofo_import_overwrite", kwargs={"pk": document.pk}
                        ),
                    )
                    self.assertEqual(response.status_code, 302)
                    document.refresh_from_db()
                    self.assertEqual(self.saved(document), before)
                self.assertEqual(
                    self.client.get(
                        reverse("nofos:nofo_edit", args=[document.pk])
                    ).status_code,
                    200,
                )
                self.assertEqual(self.saved(document), before)

    def test_shared_composer_compare_import_paths(self):
        for route, model in (
            ("composer:composer_import", ContentGuide),
            ("compare:compare_import", CompareDocument),
        ):
            self.assertEqual(
                self.upload(word=True, url=reverse(route)).status_code, 302
            )
            self.saved(model.objects.get())

    def test_exact_issue_unrestricted_label_survives_html_word_import_and_reimport(
        self,
    ):
        expected = ["State governments", ISSUE_UNRESTRICTED]
        html = html_source("".join(f"<p>{label}</p>" for label in expected))
        for word in (False, True):
            with self.subTest(word=word):
                self.assertEqual(
                    self.upload(word=word, html=html, categories=expected).status_code,
                    302,
                )
                document = Nofo.objects.latest("created")
                original = None
                for reimport in (False, True):
                    if reimport:
                        response = self.upload(
                            word=word,
                            html=html,
                            categories=expected,
                            url=reverse(
                                "nofos:nofo_import_overwrite",
                                kwargs={"pk": document.pk},
                            ),
                        )
                        self.assertEqual(response.status_code, 302)
                    body = (
                        document.sections.get()
                        .subsections.get(name="Types of eligible organizations")
                        .body
                    )
                    rendered = BeautifulSoup(safe_markdown(body), "html.parser")
                    self.assertIsNotNone(rendered.ul)
                    self.assertEqual(
                        [item.text for item in rendered.ul.find_all("li")], expected
                    )
                    for text in (DOMESTIC, LABEL, RESTRICTION):
                        self.assertIsNone(
                            rendered.find("p", string=text).find_parent("li")
                        )
                    if original is None:
                        original = body
                    else:
                        self.assertEqual(body, original)

    def test_referenced_targets_links_and_emphasis_survive_actual_import(self):
        html = (
            html_source(
                '<p id="state"><strong>State</strong> <em>governments</em></p>'
                '<p><a href="https://example.org/eligibility">Small businesses</a></p>'
            )
            + '<p><a href="#state">Read category</a></p>'
        )
        self.assertEqual(self.upload(html=html).status_code, 302)
        document = Nofo.objects.latest("created")
        body = (
            document.sections.get()
            .subsections.get(name="Types of eligible organizations")
            .body
        )
        rendered = BeautifulSoup(safe_markdown(body), "html.parser")
        self.assertEqual(len(rendered.find_all(id="state")), 1)
        self.assertIsNotNone(rendered.find(id="state").find_parent("li"))
        self.assertEqual(rendered.find("a", href="#state").text, "Read category")
        self.assertEqual(rendered.ul.strong.text, "State")
        self.assertEqual(rendered.ul.em.text, "governments")
        self.assertIsNotNone(
            rendered.ul.find("a", href="https://example.org/eligibility")
        )

    def test_actual_unknown_category_import_and_ordinary_save_remain_unbulleted(self):
        html = html_source("<p>State governments</p><p>Regional agencies</p>")
        self.assertEqual(self.upload(html=html).status_code, 302)
        document = Nofo.objects.latest("created")
        subsection = document.sections.get().subsections.get(
            name="Types of eligible organizations"
        )
        self.assertIsNone(
            BeautifulSoup(safe_markdown(subsection.body), "html.parser").ul
        )
        plain_body = INTRO + "\n\nState governments\n\nSmall businesses\n\n" + DOMESTIC
        response = self.client.post(
            reverse(
                "nofos:subsection_edit",
                args=[document.pk, subsection.section_id, subsection.pk],
            ),
            {
                "name": subsection.name,
                "tag": subsection.tag,
                "body": plain_body,
                "edit_version": version_token(subsection),
                "html_class": subsection.html_class or "",
            },
        )
        self.assertEqual(response.status_code, 302)
        subsection.refresh_from_db()
        self.assertEqual(subsection.body, plain_body)
        self.assertIsNone(
            BeautifulSoup(safe_markdown(subsection.body), "html.parser").ul
        )
