from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from nofos.models import Nofo, Section, Subsection

User = get_user_model()


class SubsectionEditTemplateTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client.login(email="test@example.com", password="testpass123")

        self.nofo = Nofo.objects.create(
            title="Test NOFO", group="bloom", opdiv="HRSA", modifications=timezone.now()
        )
        self.modifications_section = Section.objects.create(
            nofo=self.nofo, name="Modifications", html_id="modifications", order=1
        )

    def test_modifications_block_renders_for_first_subsection(self):
        subsection = Subsection.objects.create(
            section=self.modifications_section,
            name="Test Subsection",
            order=1,
            tag="h3",
        )

        response = self.client.get(
            reverse(
                "nofos:subsection_edit",
                args=[self.nofo.id, self.modifications_section.id, subsection.id],
            )
        )
        self.assertContains(response, "Modifications date")
        self.assertContains(response, "Edit modifications table")

    def test_modifications_block_does_not_render_if_order_is_not_1(self):
        subsection = Subsection.objects.create(
            section=self.modifications_section,
            name="Another Subsection",
            order=2,
            tag="h3",
        )

        response = self.client.get(
            reverse(
                "nofos:subsection_edit",
                args=[self.nofo.id, self.modifications_section.id, subsection.id],
            )
        )
        self.assertNotContains(response, "Modifications date")

    def test_modifications_block_does_not_render_if_section_name_differs(self):
        other_section = Section.objects.create(
            nofo=self.nofo, name="Other Section", html_id="other", order=2
        )
        subsection = Subsection.objects.create(
            section=other_section, name="Test Subsection", order=1, tag="h3"
        )

        response = self.client.get(
            reverse(
                "nofos:subsection_edit",
                args=[self.nofo.id, other_section.id, subsection.id],
            )
        )
        self.assertNotContains(response, "Modifications date")

    def test_modifications_block_does_not_render_if_no_modification_date(self):
        self.nofo.modifications = None
        self.nofo.save()

        subsection = Subsection.objects.create(
            section=self.modifications_section,
            name="Test Subsection",
            order=1,
            tag="h3",
        )

        response = self.client.get(
            reverse(
                "nofos:subsection_edit",
                args=[self.nofo.id, self.modifications_section.id, subsection.id],
            )
        )

        self.assertNotContains(response, "Modifications date")


class SubsectionCalloutEditingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="callouts@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client.login(email="callouts@example.com", password="testpass123")

        self.nofo = Nofo.objects.create(
            title="Callout editing NOFO",
            short_name="callout-editing",
            number="TEST-CALLOUT-001",
            group="bloom",
            opdiv="HRSA",
            theme="portrait-hrsa-white",
        )
        self.section = Section.objects.create(
            nofo=self.nofo,
            name="Step 2: Review",
            html_id="step-2-review",
            order=2,
        )

    def edit_url(self, subsection):
        return reverse(
            "nofos:subsection_edit",
            args=[self.nofo.id, self.section.id, subsection.id],
        )

    def post_subsection(self, subsection, *, callout_box, **overrides):
        data = {
            "name": subsection.name,
            "tag": subsection.tag,
            "body": subsection.body,
            "html_class": subsection.html_class,
        }
        data.update(overrides)
        if callout_box:
            data["callout_box"] = "on"
        return self.client.post(self.edit_url(subsection), data)

    def test_edit_page_exposes_current_callout_state(self):
        regular = Subsection.objects.create(
            section=self.section,
            name="Regular subsection",
            tag="h3",
            order=1,
            body="Regular content",
        )
        callout = Subsection.objects.create(
            section=self.section,
            name="Existing callout",
            tag="h3",
            order=2,
            body="Callout content",
            callout_box=True,
        )

        regular_response = self.client.get(self.edit_url(regular))
        self.assertContains(regular_response, "Is callout box?")
        self.assertContains(
            regular_response,
            "Callout boxes",
        )
        self.assertContains(
            regular_response,
            "use an accent color to call attention to important content.",
        )
        self.assertNotContains(
            regular_response,
            "Best for short, high-priority content",
        )
        self.assertNotContains(
            regular_response,
            "Re-importing this NOFO replaces this setting",
        )
        content = regular_response.content.decode()
        self.assertLess(
            content.index("Heading level"), content.index("Is callout box?")
        )
        self.assertLess(
            content.index("Is callout box?"), content.index("Add a page break")
        )
        self.assertNotContains(
            regular_response,
            'name="callout_box" checked',
        )

        callout_response = self.client.get(self.edit_url(callout))
        self.assertContains(
            callout_response,
            'name="callout_box" checked',
        )

    def test_regular_subsection_can_be_changed_to_callout_without_other_changes(self):
        subsection = Subsection.objects.create(
            section=self.section,
            name="Program details",
            tag="h3",
            order=3,
            body="Program details body",
            html_class="page-break-before",
        )
        original_html_id = subsection.html_id

        response = self.post_subsection(subsection, callout_box=True)

        self.assertEqual(response.status_code, 302)
        subsection.refresh_from_db()
        self.assertTrue(subsection.callout_box)
        self.assertEqual(subsection.name, "Program details")
        self.assertEqual(subsection.tag, "h3")
        self.assertEqual(subsection.body, "Program details body")
        self.assertEqual(subsection.order, 3)
        self.assertEqual(subsection.html_id, original_html_id)
        self.assertEqual(subsection.html_class, "page-break-before")

    def test_callout_can_be_changed_to_regular_subsection(self):
        subsection = Subsection.objects.create(
            section=self.section,
            name="Program details",
            tag="h3",
            order=1,
            body="Program details body",
            callout_box=True,
        )

        response = self.post_subsection(subsection, callout_box=False)

        self.assertEqual(response.status_code, 302)
        subsection.refresh_from_db()
        self.assertFalse(subsection.callout_box)

    def test_unnamed_subsection_supports_both_callout_transitions(self):
        subsection = Subsection.objects.create(
            section=self.section,
            name="",
            tag="",
            order=1,
            body="Unnamed subsection body",
        )

        response = self.post_subsection(subsection, callout_box=True)
        self.assertEqual(response.status_code, 302)
        subsection.refresh_from_db()
        self.assertTrue(subsection.callout_box)

        response = self.post_subsection(subsection, callout_box=False)
        self.assertEqual(response.status_code, 302)
        subsection.refresh_from_db()
        self.assertFalse(subsection.callout_box)

    def test_editing_other_fields_preserves_checked_callout_state(self):
        subsection = Subsection.objects.create(
            section=self.section,
            name="Existing callout",
            tag="h3",
            order=1,
            body="Original body",
            callout_box=True,
        )

        response = self.post_subsection(
            subsection,
            callout_box=True,
            body="Updated body",
        )

        self.assertEqual(response.status_code, 302)
        subsection.refresh_from_db()
        self.assertTrue(subsection.callout_box)
        self.assertEqual(subsection.body, "Updated body")


class SubsectionCalloutRenderingTests(TestCase):
    marker = "UNIQUE-CALLOUT-RENDER-MARKER"

    def setUp(self):
        User.objects.create_user(
            email="callout-rendering@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client.login(
            email="callout-rendering@example.com",
            password="testpass123",
        )
        self.nofo = Nofo.objects.create(
            title="Callout rendering NOFO",
            short_name="callout-rendering",
            number="TEST-CALLOUT-002",
            group="bloom",
            opdiv="HRSA",
            agency="Test agency",
            theme="portrait-hrsa-white",
        )
        self.section = Section.objects.create(
            nofo=self.nofo,
            name="Step 1: Review the Opportunity",
            html_id="step-1-review-the-opportunity",
            order=1,
        )
        Subsection.objects.create(
            section=self.section,
            name="Basic information",
            tag="h2",
            order=1,
            body="Basic information body",
        )
        self.subsection = Subsection.objects.create(
            section=self.section,
            name="Key facts",
            tag="h3",
            order=2,
            body=self.marker,
            html_class="page-break-before",
            callout_box=True,
        )

    def rendered_nofo(self):
        return self.client.get(reverse("nofos:nofo_view", args=[self.nofo.id]))

    def test_recognized_step_one_callout_renders_once_in_portrait_right_column(self):
        response = self.rendered_nofo()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode().count(self.marker), 1)
        self.assertContains(response, "section--content--right-col")
        self.assertContains(
            response,
            f'href="#{self.subsection.html_id}"',
        )
        self.assertContains(
            response,
            f'id="{self.subsection.html_id}"',
        )
        self.assertContains(response, "callout-box page-break-before")

    def test_recognized_step_one_callout_renders_once_inline_in_landscape(self):
        self.nofo.theme = "landscape-cdc-blue"
        self.nofo.save()

        response = self.rendered_nofo()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode().count(self.marker), 1)
        self.assertNotContains(response, "section--content--right-col")
        self.assertContains(response, "callout-box page-break-before")

    def test_regular_subsection_renders_once_inline_with_same_toc_anchor(self):
        self.subsection.callout_box = False
        self.subsection.save()

        response = self.rendered_nofo()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode().count(self.marker), 1)
        self.assertNotContains(response, "section--content--right-col")
        self.assertContains(
            response,
            f'href="#{self.subsection.html_id}"',
        )
        self.assertContains(
            response,
            f'id="{self.subsection.html_id}"',
        )

    def test_word_export_reflects_selected_callout_state(self):
        export_url = reverse("nofos:nofo_export", args=[self.nofo.id])

        callout_response = self.client.get(export_url)
        self.assertEqual(callout_response.status_code, 200)
        self.assertContains(callout_response, '<table class="callout-box">')
        self.assertEqual(callout_response.content.decode().count(self.marker), 1)

        self.subsection.callout_box = False
        self.subsection.save()

        regular_response = self.client.get(export_url)
        self.assertEqual(regular_response.status_code, 200)
        self.assertNotContains(regular_response, '<table class="callout-box">')
        self.assertEqual(regular_response.content.decode().count(self.marker), 1)


class SubsectionHeadingEditingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="headings@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client.login(email="headings@example.com", password="testpass123")

        self.nofo = Nofo.objects.create(
            title="Heading editing NOFO",
            short_name="heading-editing",
            number="TEST-HEADING-001",
            group="bloom",
            opdiv="HRSA",
            agency="Test agency",
            theme="portrait-hrsa-white",
        )
        self.section = Section.objects.create(
            nofo=self.nofo,
            name="Step 2: Review",
            html_id="step-2-review",
            order=2,
        )

    def edit_url(self, subsection):
        return reverse(
            "nofos:subsection_edit",
            args=[self.nofo.id, self.section.id, subsection.id],
        )

    def post_subsection(self, subsection, *, has_heading, **overrides):
        data = {
            "body": subsection.body,
            "html_class": subsection.html_class,
            "callout_box": str(subsection.callout_box),
            "heading_control_present": "True",
        }
        if has_heading:
            data.update(
                {
                    "has_heading": "on",
                    "name": subsection.name,
                    "tag": subsection.tag or "h3",
                }
            )
        data.update(overrides)
        return self.client.post(self.edit_url(subsection), data)

    def test_edit_page_uses_existing_control_patterns_for_heading_state(self):
        headed = Subsection.objects.create(
            section=self.section,
            name="Program details",
            tag="h3",
            order=1,
            body="Program content",
        )
        headingless = Subsection.objects.create(
            section=self.section,
            name="",
            tag="",
            order=2,
            body="Headingless content",
        )

        headed_response = self.client.get(self.edit_url(headed))
        self.assertContains(headed_response, "Include a subsection heading")
        self.assertContains(
            headed_response,
            "Display a heading above this subsection’s content.",
        )
        self.assertTrue(headed_response.context["form"]["has_heading"].value())
        content = headed_response.content.decode()
        self.assertLess(
            content.index("Include a subsection heading"),
            content.index("Subsection name"),
        )
        self.assertLess(
            content.index("Heading level"), content.index("Is callout box?")
        )
        self.assertLess(
            content.index("Is callout box?"), content.index("Add a page break")
        )

        headingless_response = self.client.get(self.edit_url(headingless))
        self.assertFalse(headingless_response.context["form"]["has_heading"].value())

    def test_headingless_subsection_can_gain_heading(self):
        subsection = Subsection.objects.create(
            section=self.section,
            name="",
            tag="",
            order=1,
            body="Keep this body",
            html_class="page-break-before",
            callout_box=True,
        )

        response = self.post_subsection(
            subsection,
            has_heading=True,
            name="Application process",
            tag="h3",
        )

        self.assertEqual(response.status_code, 302)
        subsection.refresh_from_db()
        self.assertEqual(subsection.name, "Application process")
        self.assertEqual(subsection.tag, "h3")
        self.assertTrue(subsection.html_id)
        self.assertEqual(subsection.body, "Keep this body")
        self.assertEqual(subsection.html_class, "page-break-before")
        self.assertTrue(subsection.callout_box)

    def test_headed_subsection_can_remove_heading_and_keep_anchor(self):
        subsection = Subsection.objects.create(
            section=self.section,
            name="Application process",
            tag="h3",
            order=1,
            body="Keep this body",
            html_class="page-break-before",
            callout_box=True,
        )
        original_html_id = subsection.html_id

        response = self.post_subsection(subsection, has_heading=False)

        self.assertEqual(response.status_code, 302)
        subsection.refresh_from_db()
        self.assertEqual(subsection.name, "")
        self.assertEqual(subsection.tag, "")
        self.assertEqual(subsection.html_id, original_html_id)
        self.assertEqual(subsection.body, "Keep this body")
        self.assertEqual(subsection.html_class, "page-break-before")
        self.assertTrue(subsection.callout_box)

    def test_adding_heading_requires_name(self):
        subsection = Subsection.objects.create(
            section=self.section,
            name="",
            tag="",
            order=1,
            body="Keep this body",
        )

        response = self.post_subsection(
            subsection,
            has_heading=True,
            name="",
            tag="h3",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Subsection name can’t be empty.")
        subsection.refresh_from_db()
        self.assertEqual(subsection.name, "")
        self.assertEqual(subsection.tag, "")

    def test_existing_heading_can_still_be_renamed_and_releveled(self):
        subsection = Subsection.objects.create(
            section=self.section,
            name="Application process",
            tag="h3",
            order=1,
            body="Keep this body",
        )
        original_html_id = subsection.html_id

        response = self.post_subsection(
            subsection,
            has_heading=True,
            name="Submission process",
            tag="h4",
        )

        self.assertEqual(response.status_code, 302)
        subsection.refresh_from_db()
        self.assertEqual(subsection.name, "Submission process")
        self.assertEqual(subsection.tag, "h4")
        self.assertEqual(subsection.html_id, original_html_id)

    def test_legacy_submission_without_heading_control_preserves_heading(self):
        subsection = Subsection.objects.create(
            section=self.section,
            name="Application process",
            tag="h3",
            order=1,
            body="Original body",
        )

        response = self.client.post(
            self.edit_url(subsection),
            {
                "body": "Updated body",
                "html_class": "",
                "callout_box": "False",
            },
        )

        self.assertEqual(response.status_code, 302)
        subsection.refresh_from_db()
        self.assertEqual(subsection.name, "Application process")
        self.assertEqual(subsection.tag, "h3")
        self.assertEqual(subsection.body, "Updated body")

    def test_legacy_submission_keeps_existing_heading_validation(self):
        subsection = Subsection.objects.create(
            section=self.section,
            name="Application process",
            tag="h3",
            order=1,
            body="Original body",
        )

        response = self.client.post(
            self.edit_url(subsection),
            {
                "name": "",
                "tag": "h3",
                "body": "Updated body",
                "html_class": "",
                "callout_box": "False",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Subsection name can’t be empty.")
        subsection.refresh_from_db()
        self.assertEqual(subsection.name, "Application process")
        self.assertEqual(subsection.tag, "h3")
        self.assertEqual(subsection.body, "Original body")


class SubsectionHeadingRenderingTests(TestCase):
    marker = "UNIQUE-HEADING-TRANSITION-MARKER"

    def setUp(self):
        User.objects.create_user(
            email="heading-rendering@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client.login(
            email="heading-rendering@example.com",
            password="testpass123",
        )
        self.nofo = Nofo.objects.create(
            title="Heading rendering NOFO",
            short_name="heading-rendering",
            number="TEST-HEADING-002",
            group="bloom",
            opdiv="HRSA",
            agency="Test agency",
            theme="portrait-hrsa-white",
        )
        self.section = Section.objects.create(
            nofo=self.nofo,
            name="Step 2: Review",
            html_id="step-2-review",
            order=2,
        )
        self.subsection = Subsection.objects.create(
            section=self.section,
            name="Application process",
            tag="h3",
            order=1,
            body=self.marker,
        )

    def test_removing_heading_removes_toc_entry_but_keeps_html_anchor(self):
        html_id = self.subsection.html_id
        view_url = reverse("nofos:nofo_view", args=[self.nofo.id])

        headed_response = self.client.get(view_url)
        self.assertContains(headed_response, f'href="#{html_id}"')
        self.assertContains(headed_response, f'<h3 id="{html_id}"')

        self.subsection.name = ""
        self.subsection.tag = ""
        self.subsection.save()

        headingless_response = self.client.get(view_url)
        self.assertNotContains(headingless_response, f'href="#{html_id}"')
        self.assertContains(
            headingless_response,
            f'<span id="{html_id}" aria-hidden="true"></span>',
        )
        self.assertEqual(
            headingless_response.content.decode().count(f'id="{html_id}"'),
            1,
        )
        self.assertEqual(
            headingless_response.content.decode().count(self.marker),
            1,
        )

    def test_first_subsection_heading_and_anchor_render_once(self):
        first_section = Section.objects.create(
            nofo=self.nofo,
            name="Step 1: Prepare",
            html_id="step-1-prepare",
            order=1,
        )
        first_subsection = Subsection.objects.create(
            section=first_section,
            name="Records retention",
            tag="h3",
            order=1,
            body="FIRST-SUBSECTION-BODY",
            html_class="page-break-before",
        )

        response = self.client.get(reverse("nofos:nofo_view", args=[self.nofo.id]))
        content = response.content.decode()

        self.assertEqual(content.count(f'id="{first_subsection.html_id}"'), 1)
        self.assertEqual(content.count(">Records retention</h3>"), 1)
        self.assertEqual(content.count("FIRST-SUBSECTION-BODY"), 1)
        self.assertEqual(content.count("page-break--hr--container"), 1)
        self.assertLess(
            content.index("page-break--hr--container"),
            content.index(">Records retention</h3>"),
        )

    def test_headingless_appendix_table_remains_direct_content_child(self):
        first_section = Section.objects.create(
            nofo=self.nofo,
            name="Step 1: Prepare",
            html_id="step-1-prepare",
            order=1,
        )
        Subsection.objects.create(
            section=first_section,
            name="Basic information",
            tag="h3",
            order=1,
        )
        for order in range(3, 8):
            Section.objects.create(
                nofo=self.nofo,
                name=f"Section {order}",
                html_id=f"section-{order}",
                order=order,
            )
        appendix = Section.objects.create(
            nofo=self.nofo,
            name="Appendix",
            html_id="appendix",
            order=8,
        )
        Subsection.objects.create(
            section=appendix,
            name="",
            tag="",
            order=1,
            body="| Column |\n| --- |\n| Value |",
        )

        response = self.client.get(reverse("nofos:nofo_view", args=[self.nofo.id]))
        soup = BeautifulSoup(response.content, "html.parser")
        appendix_element = soup.find("section", id="section--appendix")
        content_element = appendix_element.find(
            "div",
            class_="section--content",
            recursive=False,
        )

        self.assertIn("section--appendix", appendix_element.get("class", []))
        self.assertIsNotNone(content_element.find("table", recursive=False))

    def test_word_export_keeps_anchor_when_heading_is_removed(self):
        html_id = self.subsection.html_id
        self.subsection.name = ""
        self.subsection.tag = ""
        self.subsection.save()

        response = self.client.get(reverse("nofos:nofo_export", args=[self.nofo.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'<div id="{html_id}"')
        self.assertEqual(response.content.decode().count(self.marker), 1)

    def test_word_export_keeps_anchor_for_headingless_callout(self):
        html_id = self.subsection.html_id
        self.subsection.name = ""
        self.subsection.tag = ""
        self.subsection.callout_box = True
        self.subsection.save()

        response = self.client.get(reverse("nofos:nofo_export", args=[self.nofo.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<table class="callout-box">')
        self.assertContains(response, f'<div id="{html_id}"')
        self.assertEqual(response.content.decode().count(self.marker), 1)

    def test_word_export_keeps_anchor_for_empty_headingless_subsection(self):
        html_id = self.subsection.html_id
        self.subsection.name = ""
        self.subsection.tag = ""
        self.subsection.body = ""
        self.subsection.save()

        response = self.client.get(reverse("nofos:nofo_export", args=[self.nofo.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'<div id="{html_id}"')
