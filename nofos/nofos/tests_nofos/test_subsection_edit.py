from django.contrib.auth import get_user_model
from django.test import (
    TestCase,
    TransactionTestCase,
    override_settings,
    skipUnlessDBFeature,
)
from django.urls import reverse
from django.utils import timezone

from nofos.models import Nofo, Section, Subsection
from nofos.views import CALLOUT_WORD_WARNING_EXEMPT_NAMES

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
            "edit_version": self.client.get(self.edit_url(subsection))
            .context["form"]["edit_version"]
            .value(),
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

    def make_warning_subsection(self, **overrides):
        values = {
            "section": self.section,
            "name": "Required format",
            "tag": "h3",
            "order": 1,
            "body": "word " * 101,
            "callout_box": True,
        }
        values.update(overrides)
        return Subsection.objects.create(**values)

    @override_settings(CALLOUT_WORD_WARNING_THRESHOLD=100)
    def test_warning_threshold_boundary_and_empty_content(self):
        subsection = self.make_warning_subsection()
        for count in [0, 99, 100, 101]:
            with self.subTest(count=count):
                subsection.body = "word " * count
                subsection.save()
                response = self.client.get(self.edit_url(subsection))
                self.assertEqual(
                    response.context["show_callout_word_warning"], count > 100
                )
                self.assertContains(response, 'data-word-threshold="100"')
                self.assertContains(response, 'aria-live="polite"')
                warning = (
                    response.content.decode()
                    .split('id="callout-word-warning"')[1]
                    .split(">", 1)[0]
                )
                self.assertEqual("hidden" in warning, count <= 100)

    @override_settings(CALLOUT_WORD_WARNING_THRESHOLD=2)
    def test_warning_uses_configured_threshold_and_whitespace_count(self):
        subsection = self.make_warning_subsection(
            body="  First\n\nsecond\tthird\u00a0 "
        )
        response = self.client.get(self.edit_url(subsection))
        self.assertTrue(response.context["show_callout_word_warning"])
        self.assertContains(response, 'data-word-threshold="2"')

    def test_long_regular_subsection_has_no_warning(self):
        subsection = self.make_warning_subsection(callout_box=False)
        response = self.client.get(self.edit_url(subsection))
        self.assertFalse(response.context["show_callout_word_warning"])

    def test_unnamed_long_callout_has_warning(self):
        subsection = self.make_warning_subsection(name="", tag="")
        response = self.client.get(self.edit_url(subsection))
        self.assertTrue(response.context["show_callout_word_warning"])

    def test_long_callout_can_still_be_saved(self):
        subsection = self.make_warning_subsection(body="Short content")
        body = " ".join(["word"] * 101)
        response = self.post_subsection(subsection, callout_box=True, body=body)
        self.assertEqual(response.status_code, 302)
        subsection.refresh_from_db()
        self.assertEqual(subsection.body, body)
        self.assertTrue(subsection.callout_box)

    def test_invalid_form_uses_submitted_body_and_callout_state(self):
        subsection = self.make_warning_subsection(body="Short", callout_box=False)
        response = self.post_subsection(
            subsection, callout_box=True, name="", body="word " * 101
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["show_callout_word_warning"])
        subsection.refresh_from_db()
        self.assertEqual(subsection.body, "Short")
        self.assertFalse(subsection.callout_box)

    def test_invalid_form_can_hide_previous_warning(self):
        subsection = self.make_warning_subsection()
        for callout_box, body in [(False, subsection.body), (True, "Short")]:
            with self.subTest(callout_box=callout_box):
                response = self.post_subsection(
                    subsection, callout_box=callout_box, name="", body=body
                )
                self.assertEqual(response.status_code, 200)
                self.assertFalse(response.context["show_callout_word_warning"])

    def test_key_facts_and_key_dates_names_are_exempt_from_warning(self):
        for order, name in enumerate(CALLOUT_WORD_WARNING_EXEMPT_NAMES):
            with self.subTest(name=name):
                subsection = self.make_warning_subsection(name=name, order=order)
                response = self.client.get(self.edit_url(subsection))
                self.assertFalse(response.context["show_callout_word_warning"])

    def test_whitespace_padded_exempt_name_still_matches(self):
        subsection = self.make_warning_subsection(name="  Key facts  ")
        response = self.client.get(self.edit_url(subsection))
        self.assertFalse(response.context["show_callout_word_warning"])

    def test_similarly_named_subsections_still_warn(self):
        names = ["key facts", "KEY FACTS", "Key Fact", "Key facts and figures"]
        for order, name in enumerate(names):
            with self.subTest(name=name):
                subsection = self.make_warning_subsection(name=name, order=order)
                response = self.client.get(self.edit_url(subsection))
                self.assertTrue(response.context["show_callout_word_warning"])


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


class SubsectionConflictTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="conflicts@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client.force_login(self.user)
        self.nofo = Nofo.objects.create(
            title="Conflict test", group="bloom", opdiv="HRSA"
        )
        self.section = Section.objects.create(
            nofo=self.nofo, name="Applications", order=1
        )
        self.subsection = Subsection.objects.create(
            section=self.section,
            name="Requirements",
            tag="h3",
            order=1,
            body="Original content",
        )
        self.url = reverse(
            "nofos:subsection_edit",
            args=[self.nofo.pk, self.section.pk, self.subsection.pk],
        )

    def opened_form(self):
        from nofos.subsection_conflicts import saved_values

        self.subsection.refresh_from_db()
        data = saved_values(self.subsection)
        data["edit_version"] = (
            self.client.get(self.url).context["form"]["edit_version"].value()
        )
        # HTML checkboxes submit nothing when unchecked.
        if not data.pop("callout_box"):
            return data
        data["callout_box"] = "on"
        return data

    def test_two_tabs_preserve_newer_save_and_unsaved_fields(self):
        tab_a, tab_b = self.opened_form(), self.opened_form()
        tab_a["body"] = "Fixed links and caption"
        self.assertEqual(self.client.post(self.url, tab_a).status_code, 302)
        tab_b.update(
            name="Unsaved name",
            tag="h4",
            callout_box="on",
            html_class="page-break-before",
            body="My draft <script>alert(1)</script>",
        )
        response = self.client.post(self.url, tab_b)
        self.assertEqual(response.status_code, 409)
        self.subsection.refresh_from_db()
        self.assertEqual(self.subsection.body, tab_a["body"])
        self.assertEqual(self.subsection.name, "Requirements")
        self.assertEqual(response.context["unsaved"]["name"], "Unsaved name")
        self.assertEqual(response.context["unsaved"]["tag"], "h4")
        self.assertTrue(response.context["unsaved"]["callout_box"])
        self.assertEqual(response.context["unsaved"]["html_class"], "page-break-before")
        self.assertContains(response, "&lt;script&gt;", status_code=409)
        self.assertNotContains(response, "<script>alert(1)</script>", status_code=409)
        self.assertContains(response, "Review and combine changes", status_code=409)
        self.assertContains(response, "Discard my changes and return", status_code=409)
        self.assertNotContains(response, 'name="edit_version"', status_code=409)

    def conflict(self):
        data = self.opened_form()
        Subsection.objects.filter(pk=self.subsection.pk).update(
            body="Latest saved content"
        )
        data["body"] = "Unsaved draft"
        return self.client.post(self.url, data)

    def review(self, conflict):
        return self.client.post(
            self.url, {"action": "review", "recovery": conflict.context["recovery"]}
        )

    def test_review_starts_with_latest_and_save_combined(self):
        conflict = self.conflict()
        response = self.review(conflict)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertEqual(form["body"].value(), "Latest saved content")
        self.assertEqual(response.context["preserved_unsaved"]["body"], "Unsaved draft")
        self.assertContains(response, "Save combined version")
        self.subsection.refresh_from_db()
        self.assertEqual(self.subsection.body, "Latest saved content")
        data = self.opened_form()
        data.update(
            body="Latest saved content plus my changes",
            edit_version=form["edit_version"].value(),
            recovery=form["recovery"].value(),
        )
        self.assertEqual(self.client.post(self.url, data).status_code, 302)
        self.subsection.refresh_from_db()
        self.assertEqual(self.subsection.body, data["body"])

    def test_another_change_during_review_requires_review_again(self):
        response = self.review(self.conflict())
        token = response.context["form"]["edit_version"].value()
        data = self.opened_form()
        data.update(edit_version=token, body="Combined draft")
        Subsection.objects.filter(pk=self.subsection.pk).update(
            body="Another person's new edit"
        )
        conflict = self.client.post(self.url, data)
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.context["unsaved"]["body"], "Combined draft")
        self.assertEqual(
            conflict.context["latest"]["body"], "Another person's new edit"
        )

    def test_review_reads_changes_saved_after_conflict_screen(self):
        conflict = self.conflict()
        Subsection.objects.filter(pk=self.subsection.pk).update(body="Even newer text")
        response = self.review(conflict)
        self.assertEqual(response.context["form"]["body"].value(), "Even newer text")

    def test_missing_predeployment_token_preserves_work(self):
        data = self.opened_form()
        del data["edit_version"]
        data["body"] = "Work typed before deployment"
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 409)
        self.assertContains(
            response,
            "The editor was updated while this page was open.",
            status_code=409,
        )
        self.assertEqual(response.context["unsaved"]["body"], data["body"])
        self.subsection.refresh_from_db()
        self.assertEqual(self.subsection.body, "Original content")
        self.assertEqual(self.review(response).status_code, 200)

    def test_unrelated_subsection_and_nofo_metadata_do_not_conflict(self):
        data = self.opened_form()
        Subsection.objects.create(
            section=self.section, order=2, body="Other subsection"
        )
        self.nofo.title = "Changed title"
        self.nofo.save()
        data["body"] = "Safe change"
        self.assertEqual(self.client.post(self.url, data).status_code, 302)

    def test_each_editable_field_is_protected(self):
        for field, value in {
            "name": "New name",
            "tag": "h4",
            "callout_box": True,
            "html_class": "page-break-before",
            "body": "New body",
        }.items():
            with self.subTest(field=field):
                data = self.opened_form()
                Subsection.objects.filter(pk=self.subsection.pk).update(
                    **{field: value}
                )
                response = self.client.post(self.url, data)
                self.assertEqual(response.status_code, 409)
                self.subsection.refresh_from_db()
                self.assertEqual(getattr(self.subsection, field), value)

    def test_identical_stale_submission_returns_without_conflict(self):
        data = self.opened_form()
        Subsection.objects.filter(pk=self.subsection.pk).update(body="Already saved")
        data["body"] = "Already saved"
        self.assertEqual(self.client.post(self.url, data).status_code, 302)

    def test_invalid_token_cannot_save(self):
        data = self.opened_form()
        data.update(edit_version="tampered", body="Must not save")
        self.assertEqual(self.client.post(self.url, data).status_code, 409)
        self.subsection.refresh_from_db()
        self.assertEqual(self.subsection.body, "Original content")

    def test_token_from_another_subsection_cannot_save(self):
        from nofos.subsection_conflicts import version_token

        other = Subsection.objects.create(
            section=self.section,
            order=2,
            name="Requirements",
            tag="h3",
            body="Original content",
        )
        data = self.opened_form()
        data["edit_version"] = version_token(other)
        self.assertEqual(self.client.post(self.url, data).status_code, 409)

    def test_tampered_recovery_is_rejected(self):
        self.assertEqual(
            self.client.post(
                self.url, {"action": "review", "recovery": "tampered"}
            ).status_code,
            400,
        )

    def test_discard_returns_without_a_write(self):
        response = self.conflict()
        self.assertEqual(
            self.client.get(response.context["return_url"]).status_code, 200
        )
        self.subsection.refresh_from_db()
        self.assertEqual(self.subsection.body, "Latest saved content")

    def test_validation_error_does_not_refresh_version_or_lose_reference(self):
        response = self.review(self.conflict())
        form = response.context["form"]
        data = self.opened_form()
        data.update(
            name="",
            tag="h3",
            body="Combined draft",
            edit_version=form["edit_version"].value(),
            recovery=form["recovery"].value(),
        )
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"]["body"].value(), "Combined draft")
        self.assertEqual(
            response.context["form"]["edit_version"].value(), data["edit_version"]
        )
        self.assertEqual(response.context["preserved_unsaved"]["body"], "Unsaved draft")

    def test_non_form_fields_changed_since_open_are_preserved(self):
        data = self.opened_form()
        Subsection.objects.filter(pk=self.subsection.pk).update(
            order=3, policy_language_status="intact"
        )
        data["body"] = "New content"
        self.assertEqual(self.client.post(self.url, data).status_code, 302)
        self.subsection.refresh_from_db()
        self.assertEqual(self.subsection.order, 3)
        self.assertEqual(self.subsection.policy_language_status, "intact")


class SubsectionConcurrentSaveTests(TransactionTestCase):
    setUp = SubsectionConflictTests.setUp
    opened_form = SubsectionConflictTests.opened_form

    @skipUnlessDBFeature("has_select_for_update")
    def test_simultaneous_validated_forms_only_allow_one_save(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from unittest.mock import patch

        from django.db import close_old_connections
        from django.test import Client

        from nofos.forms import SubsectionEditForm

        data = self.opened_form()
        clients = [Client(), Client()]
        for client in clients:
            client.force_login(self.user)
        barrier = Barrier(2)
        original_is_valid = SubsectionEditForm.is_valid

        def validate_together(form):
            valid = original_is_valid(form)
            barrier.wait(timeout=10)
            return valid

        def save(index):
            close_old_connections()
            try:
                response = clients[index].post(
                    self.url, {**data, "body": f"Tab {index}"}
                )
                return response.status_code, index
            finally:
                close_old_connections()

        with patch.object(SubsectionEditForm, "is_valid", validate_together):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(save, [0, 1]))
        self.assertEqual(sorted(status for status, _ in results), [302, 409])
        winner = next(index for status, index in results if status == 302)
        self.subsection.refresh_from_db()
        self.assertEqual(self.subsection.body, f"Tab {winner}")
