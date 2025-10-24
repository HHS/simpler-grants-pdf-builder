import uuid

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import ComposerSubsectionEditForm
from .models import ContentGuide, ContentGuideSection, ContentGuideSubsection
from .views import ComposerSectionView

User = get_user_model()

# --- TEST MODELS -------------------------------------------------------


class ExtractVariablesTests(TestCase):
    def setUp(self):
        self.guide = ContentGuide.objects.create(
            title="Guide", opdiv="CDC", group="bloom"
        )
        self.section = ContentGuideSection.objects.create(
            document=self.guide, order=1, name="Section 1", html_id="sec-1"
        )

    def _mk(self, body: str):
        return ContentGuideSubsection.objects.create(
            section=self.section,
            order=1,
            name="Sub 1",
            tag="h3",
            body=body,
            edit_mode="full",
            enabled=True,
        )

    def test_no_variables_returns_empty_list(self):
        ss = self._mk("No placeholders here.")
        self.assertEqual(ss.extract_variables(), [])

    def test_simple_string_variable(self):
        ss = self._mk("Please provide {Project name} for the application.")
        vars_ = ss.extract_variables()
        self.assertEqual(
            vars_,
            [
                {"key": "project_name", "type": "string", "label": "Project name"},
            ],
        )

    def test_list_variable_type(self):
        ss = self._mk("Add tags: {List: Tags}")
        vars_ = ss.extract_variables()
        self.assertEqual(
            vars_,
            [
                {"key": "tags", "type": "list", "label": "Tags"},
            ],
        )

    def test_duplicate_labels_are_deduped(self):
        ss = self._mk("Enter {Project name} and confirm {Project name}")
        vars_ = ss.extract_variables()
        self.assertEqual(
            vars_[0], {"key": "project_name", "type": "string", "label": "Project name"}
        )
        self.assertEqual(
            vars_[1],
            {"key": "project_name_2", "type": "string", "label": "Project name"},
        )

    def test_escaped_opening_brace_does_not_create_variable(self):
        ss = self._mk(r"Literal \{not a variable} and real {Variable}")
        vars_ = ss.extract_variables()
        self.assertEqual(
            vars_,
            [
                {"key": "variable", "type": "string", "label": "Variable"},
            ],
        )

    def test_empty_or_whitespace_label_falls_back_to_key_var(self):
        ss = self._mk("Weird case: {   }")
        vars_ = ss.extract_variables()
        self.assertEqual(
            vars_,
            [
                {
                    "key": "var",
                    "type": "string",
                    "label": "",
                },  # label trimmed to empty → key fallback
            ],
        )

    def test_text_override_parameter_is_used_instead_of_instance_body(self):
        ss = self._mk("Old body without vars")
        override = "New body with a {Fresh var}"
        vars_ = ss.extract_variables(text=override)
        self.assertEqual(
            vars_,
            [
                {"key": "fresh_var", "type": "string", "label": "Fresh var"},
            ],
        )


# --- TEST FORMS ----------------------------------------------------------


class SubsectionEditFormVariablesTests(TestCase):
    def setUp(self):
        self.guide = ContentGuide.objects.create(title="G", opdiv="CDC", group="bloom")
        self.section = ContentGuideSection.objects.create(
            document=self.guide, order=1, name="S"
        )
        self.ss = ContentGuideSubsection.objects.create(
            section=self.section,
            order=1,
            name="Intro",
            tag="h4",
            body="Initial body",
            edit_mode="full",
        )

    def test_variables_validation_uses_posted_body(self):
        form = ComposerSubsectionEditForm(
            data={"edit_mode": "variables", "body": "Has {Variable} now"},
            instance=self.ss,
        )
        self.assertTrue(form.is_valid(), form.errors.as_json())

    def test_variables_validation_errors_when_no_vars(self):
        form = ComposerSubsectionEditForm(
            data={"edit_mode": "variables", "body": "No placeholders here"},
            instance=self.ss,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("edit_mode", form.errors)


# --- TEST VIEWS -------------------------------------------------------


class ComposerListViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="composer@example.com",
            password="testpass123",
            group="bloom",  # or whatever default group is fine
            force_password_reset=False,
        )

        self.client.login(email="bloom@example.com", password="testpass123")

    def test_logged_in_user_sees_welcome_message(self):
        """Logged-in users should see the Composer welcome page with the correct H1 text."""
        self.client.login(email="composer@example.com", password="testpass123")
        url = reverse("composer:composer_index")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome to Composer!", html=True)

    def test_anonymous_user_is_redirected_to_login(self):
        """Anonymous users should be redirected to the login page."""
        url = reverse("composer:composer_index")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("users:login"), response.url)


class ComposerImportViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="importer@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client.login(email="importer@example.com", password="testpass123")
        self.url = reverse("composer:composer_import")

    def test_view_renders_import_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<form")

    def test_view_requires_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertIn(response.status_code, [302, 403])

    def test_post_with_invalid_file_returns_400(self):
        fake_doc = SimpleUploadedFile("bad.txt", b"not a Word file")
        response = self.client.post(self.url, {"file": fake_doc})

        # redirect back to import page and show an error
        self.assertEqual(response.status_code, 302)
        follow_response = self.client.get(response["Location"])
        self.assertEqual(follow_response.status_code, 200)
        self.assertContains(follow_response, "Error: Oops! No fos uploaded.")

    def test_post_missing_file_returns_400(self):
        response = self.client.post(self.url, {})  # no file at all

        # redirect back to import page and show an error
        self.assertEqual(response.status_code, 302)
        follow_response = self.client.get(response["Location"])
        self.assertEqual(follow_response.status_code, 200)
        self.assertContains(follow_response, "Error: Oops! No fos uploaded.")


class ComposerImportTitleViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client.login(email="test@example.com", password="testpass123")

        self.document = ContentGuide.objects.create(
            title="Original Title.docx", opdiv="CDC", group="bloom"
        )
        self.url = reverse(
            "composer:composer_import_title", kwargs={"pk": self.document.pk}
        )
        self.redirect_url = reverse("composer:composer_index")

    def test_view_returns_200_for_authorized_user(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_post_valid_data_updates_title(self):
        response = self.client.post(self.url, {"title": "Updated Title Import"})
        self.document.refresh_from_db()
        self.assertEqual(self.document.title, "Updated Title Import")
        self.assertRedirects(response, self.redirect_url)

    def test_post_invalid_data_shows_errors(self):
        response = self.client.post(self.url, {"title": ""})  # empty title = invalid
        self.assertEqual(response.status_code, 200)

        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)
        self.assertIn("This field is required.", form.errors["title"])

    def test_unauthorized_user_redirected(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)


class CompareEditTitleViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client.login(email="test@example.com", password="testpass123")

        self.document = ContentGuide.objects.create(
            title="Original Title.docx", opdiv="CDC", group="bloom"
        )
        self.url = reverse(
            "composer:composer_edit_title", kwargs={"pk": self.document.pk}
        )
        self.redirect_url = reverse("composer:composer_index")

    def test_view_returns_200_for_authorized_user(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_post_valid_data_updates_title(self):
        response = self.client.post(self.url, {"title": "Updated Title Edit"})
        self.document.refresh_from_db()
        self.assertEqual(self.document.title, "Updated Title Edit")
        self.assertRedirects(response, self.redirect_url)

    def test_post_invalid_data_shows_errors(self):
        response = self.client.post(self.url, {"title": ""})  # empty title = invalid
        self.assertEqual(response.status_code, 200)

        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)
        self.assertIn("This field is required.", form.errors["title"])

    def test_unauthorized_user_redirected(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)


class ComposerArchiveViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            force_password_reset=False,
            group="bloom",
        )
        self.client.login(email="test@example.com", password="testpass123")

        self.document = ContentGuide.objects.create(
            title="Test Content Guide",
            opdiv="CDC",
            group="bloom",
        )
        self.url = reverse("composer:composer_archive", args=[self.document.id])

    def test_get_view_renders_confirmation_page(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Are you absolutely sure you want to delete “Test Content Guide”?",
        )

    def test_post_archives_composer_doc(self):
        response = self.client.post(self.url)
        self.document.refresh_from_db()
        self.assertIsNotNone(self.document.archived)
        self.assertRedirects(response, reverse("composer:composer_index"))

    def test_cannot_archive_already_archived_composer_doc(self):
        self.document.archived = timezone.now()
        self.document.save()

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"already archived", response.content)

    def test_anonymous_user_forbidden(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertIn(b"Permission denied", response.content)


class ComposerDocumentRedirectTests(TestCase):
    def setUp(self):
        # Base URL for the redirect route
        self.redirect_url_name = "composer:composer_document_redirect"

    def test_redirects_to_first_section(self):
        # Create a guide with two sections (ordered)
        guide = ContentGuide.objects.create(title="Guide A", opdiv="CDC", group="bloom")
        s1 = ContentGuideSection.objects.create(
            document=guide, order=1, name="Section 1", html_id="sec-1"
        )
        ContentGuideSection.objects.create(
            document=guide, order=2, name="Section 2", html_id="sec-2"
        )

        url = reverse(self.redirect_url_name, kwargs={"pk": guide.pk})
        response = self.client.get(url)

        expected = reverse(
            "composer:section_view", kwargs={"pk": guide.pk, "section_pk": s1.pk}
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, expected)

    def test_returns_404_when_guide_missing(self):
        # Use a random UUID by creating one guide and using a different pk
        url = reverse(
            self.redirect_url_name,
            kwargs={"pk": "11111111-1111-1111-1111-111111111111"},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"Content Guide not found.", response.content)

    def test_returns_404_when_no_sections(self):
        guide = ContentGuide.objects.create(
            title="Empty Guide", opdiv="CDC", group="bloom"
        )
        url = reverse(self.redirect_url_name, kwargs={"pk": guide.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"This content guide has no sections.", response.content)


class GroupSubsectionsTests(TestCase):
    def setUp(self):
        # Minimal parent objects so we can create valid subsections
        self.guide = ContentGuide.objects.create(
            title="Guide", opdiv="CDC", group="bloom"
        )
        self.section = ContentGuideSection.objects.create(
            document=self.guide, order=1, name="Section 1", html_id="sec-1"
        )
        self.view = ComposerSectionView()

    def _make_subsection(self, name, tag=None, order=1):
        """Helper to make a subsection instance (not saved content matters for grouping)."""
        return ContentGuideSubsection.objects.create(
            section=self.section,
            order=order,
            name=name,
            tag=tag or "",
            body="",
            enabled=True,
        )

    def test_empty_list_returns_empty_groups(self):
        groups = self.view.group_subsections([])
        self.assertEqual(groups, [])

    def test_first_item_not_a_header_starts_its_own_group(self):
        # s1 is not in preset headers and has no h2/h3 tag → becomes first group's heading
        s1 = self._make_subsection("Intro", tag="h5", order=1)
        # s2 matches a preset header name → starts new group
        s2 = self._make_subsection("Funding details", tag="h5", order=2)
        # s3 is a normal item → belongs to s2's group
        s3 = self._make_subsection("Line items", tag="h5", order=3)

        groups = self.view.group_subsections([s1, s2, s3])

        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]["heading"], "Intro")
        self.assertEqual([x.pk for x in groups[0]["items"]], [s1.pk])

        self.assertEqual(groups[1]["heading"], "Funding details")
        self.assertEqual([x.pk for x in groups[1]["items"]], [s2.pk, s3.pk])

    def test_header_created_by_tag_h2_or_h3(self):
        # s1 is header because tag=h3 (even though name not in preset headers)
        s1 = self._make_subsection("Overview", tag="h3", order=1)
        # s2 is header because tag=h2
        s2 = self._make_subsection("Deep dive", tag="h2", order=2)
        # s3 follows s2 and is not a header → stays in s2's group
        s3 = self._make_subsection("Details list", tag="h5", order=3)

        groups = self.view.group_subsections([s1, s2, s3])

        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]["heading"], "Overview")
        self.assertEqual([x.pk for x in groups[0]["items"]], [s1.pk])

        self.assertEqual(groups[1]["heading"], "Deep dive")
        self.assertEqual([x.pk for x in groups[1]["items"]], [s2.pk, s3.pk])

    def test_consecutive_headers_each_start_their_own_group(self):
        # Two headers in a row → two groups, each includes the header item itself
        s1 = self._make_subsection("Funding details", tag="h4", order=1)
        s2 = self._make_subsection("Eligibility", tag="h4", order=2)
        groups = self.view.group_subsections([s1, s2])

        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]["heading"], "Funding details")
        self.assertEqual([x.pk for x in groups[0]["items"]], [s1.pk])

        self.assertEqual(groups[1]["heading"], "Eligibility")
        self.assertEqual([x.pk for x in groups[1]["items"]], [s2.pk])

    def test_none_or_empty_name_is_tolerated(self):
        # First item has no name and is not a header → catch-all creates a group with that (None) heading
        s1 = self._make_subsection(name="", tag="", order=1)
        s2 = self._make_subsection(
            "Basic information", tag="h4", order=2
        )  # preset header starts new group

        groups = self.view.group_subsections([s1, s2])

        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]["heading"], "")
        self.assertEqual([x.pk for x in groups[0]["items"]], [s1.pk])

        self.assertEqual(groups[1]["heading"], "Basic information")
        self.assertEqual([x.pk for x in groups[1]["items"]], [s2.pk])

    def test_order_is_preserved_within_groups(self):
        s1 = self._make_subsection("Funding details", tag="h4", order=1)
        s2 = self._make_subsection("Budget table", tag="h4", order=2)
        s3 = self._make_subsection("Notes", tag="h5", order=3)

        groups = self.view.group_subsections([s1, s3, s2])  # out-of-order input list

        # The function preserves the iteration order you pass in,
        # so items should be [s1, s3, s2] inside the group.
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["heading"], "Funding details")
        self.assertEqual([x.pk for x in groups[0]["items"]], [s1.pk, s3.pk, s2.pk])


class ComposerSectionViewTests(TestCase):
    def setUp(self):
        # Auth user
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client.login(email="test@example.com", password="testpass123")

        # Guide + sections
        self.guide = ContentGuide.objects.create(
            title="Guide", opdiv="CDC", group="bloom"
        )
        self.sec1 = ContentGuideSection.objects.create(
            document=self.guide,
            order=1,
            name="Understand the opportunity",
            html_id="s1",
        )
        self.sec2 = ContentGuideSection.objects.create(
            document=self.guide, order=2, name="Get ready to apply", html_id="s2"
        )

        # Subsections for sec1 (ensure grouping behavior)
        self.ss1 = ContentGuideSubsection.objects.create(
            section=self.sec1,
            order=1,
            name="Intro",
            tag="h4",
            body="Body 1",
            enabled=True,
        )
        # Preset header name → starts new group
        self.ss2 = ContentGuideSubsection.objects.create(
            section=self.sec1,
            order=2,
            name="Funding details",
            tag="h4",
            body="Body 2",
            enabled=True,
        )
        # Not a header → belongs to previous group
        self.ss3 = ContentGuideSubsection.objects.create(
            section=self.sec1,
            order=3,
            name="Budget table",
            tag="h5",
            body="Body 3",
            enabled=True,
        )
        # Disabled → should appear anyway
        self.ss4_disabled = ContentGuideSubsection.objects.create(
            section=self.sec1,
            order=4,
            name="(Disabled)",
            tag="h4",
            body="x",
            enabled=False,
        )

        self.url_sec1 = reverse(
            "composer:section_view",
            kwargs={"pk": self.guide.pk, "section_pk": self.sec1.pk},
        )
        self.url_sec2 = reverse(
            "composer:section_view",
            kwargs={"pk": self.guide.pk, "section_pk": self.sec2.pk},
        )

    def test_renders_200_and_groups_subsections(self):
        resp = self.client.get(self.url_sec1)
        self.assertEqual(resp.status_code, 200)

        grouped = resp.context["grouped_subsections"]
        self.assertEqual(len(grouped), 2)

        # Group 1: heading = "Intro", items = [ss1]
        self.assertEqual(grouped[0]["heading"], "Intro")
        self.assertEqual([i.pk for i in grouped[0]["items"]], [self.ss1.pk])

        # Group 2: heading = "Funding details", items = [ss2, ss3]
        self.assertEqual(grouped[1]["heading"], "Funding details")
        self.assertEqual(
            [i.pk for i in grouped[1]["items"]],
            [self.ss2.pk, self.ss3.pk, self.ss4_disabled.pk],
        )

    def test_prev_next_sections_in_context_first_section(self):
        resp = self.client.get(self.url_sec1)
        self.assertIsNone(resp.context["prev_sec"])
        self.assertIsNotNone(resp.context["next_sec"])
        self.assertEqual(resp.context["next_sec"].pk, self.sec2.pk)

    def test_prev_next_sections_in_context_second_section(self):
        resp = self.client.get(self.url_sec2)
        self.assertIsNone(resp.context["next_sec"])
        self.assertIsNotNone(resp.context["prev_sec"])
        self.assertEqual(resp.context["prev_sec"].pk, self.sec1.pk)

    def test_anonymous_user_is_forbidden(self):
        self.client.logout()
        resp = self.client.get(self.url_sec1)
        self.assertEqual(resp.status_code, 403)

    def test_404_when_section_not_in_document(self):
        # Make a section in a different guide and try to view with current guide pk
        other_guide = ContentGuide.objects.create(
            title="Other", opdiv="CDC", group="bloom"
        )
        stray_section = ContentGuideSection.objects.create(
            document=other_guide, order=1, name="Stray", html_id="x"
        )
        bad_url = reverse(
            "composer:section_view",
            kwargs={"pk": self.guide.pk, "section_pk": stray_section.pk},
        )
        resp = self.client.get(bad_url)
        self.assertEqual(resp.status_code, 404)

    def test_404_when_guide_missing(self):
        bad_url = reverse(
            "composer:section_view",
            kwargs={"pk": uuid.uuid4(), "section_pk": self.sec1.pk},
        )
        resp = self.client.get(bad_url)
        self.assertEqual(resp.status_code, 404)


class ComposerSubsectionEditViewTests(TestCase):
    def setUp(self):
        # user + login
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client.login(email="test@example.com", password="testpass123")

        # guide/sections/subsections
        self.guide = ContentGuide.objects.create(
            title="Guide", opdiv="CDC", group="bloom"
        )
        self.section = ContentGuideSection.objects.create(
            document=self.guide, order=1, name="S1", html_id="s1"
        )
        self.subsection = ContentGuideSubsection.objects.create(
            section=self.section,
            order=1,
            name="SS1",
            tag="h3",
            body="Initial body",
            enabled=True,
            edit_mode="full",
            html_id="ss-1",
        )

        self.url = reverse(
            "composer:subsection_edit",
            kwargs={
                "pk": self.guide.pk,
                "section_pk": self.section.pk,
                "subsection_pk": self.subsection.pk,
            },
        )

    def test_get_renders_for_logged_in_user(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        # context includes document/section/subsection
        self.assertEqual(resp.context["document"].pk, self.guide.pk)
        self.assertEqual(resp.context["section"].pk, self.section.pk)
        self.assertEqual(resp.context["subsection"].pk, self.subsection.pk)

    def test_anonymous_redirects_to_login(self):
        self.client.logout()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_post_updates_and_redirects_with_anchor_prefers_html_id(self):
        payload = {
            "edit_mode": "variables",
            "body": "New **markdown** with {Variable}",
        }
        resp = self.client.post(self.url, data=payload, follow=False)

        # saved
        self.subsection.refresh_from_db()
        self.assertEqual(self.subsection.edit_mode, "variables")
        self.assertIn("New **markdown**", self.subsection.body)

        # redirected back to section with anchor "#<html_id>"
        expected_base = reverse(
            "composer:section_view", args=[self.guide.pk, self.section.pk]
        )
        self.assertTrue(resp["Location"].startswith(expected_base))
        self.assertTrue(resp["Location"].endswith(f"#{self.subsection.html_id}"))

        # success message was added
        msgs = list(get_messages(resp.wsgi_request))
        self.assertTrue(any("Updated section:" in str(m) for m in msgs))

    def test_404_when_subsection_not_in_section(self):
        other_section = ContentGuideSection.objects.create(
            document=self.guide, order=2, name="S2", html_id="s2"
        )
        bad_url = reverse(
            "composer:subsection_edit",
            kwargs={
                "pk": self.guide.pk,
                "section_pk": other_section.pk,
                "subsection_pk": self.subsection.pk,
            },
        )
        resp = self.client.get(bad_url)
        self.assertEqual(resp.status_code, 404)

    def test_404_when_section_not_in_guide(self):
        other_guide = ContentGuide.objects.create(
            title="Other", opdiv="CDC", group="bloom"
        )
        stray_section = ContentGuideSection.objects.create(
            document=other_guide, order=1, name="Stray", html_id="x"
        )
        bad_url = reverse(
            "composer:subsection_edit",
            kwargs={
                "pk": self.guide.pk,
                "section_pk": stray_section.pk,
                "subsection_pk": self.subsection.pk,
            },
        )
        resp = self.client.get(bad_url)
        self.assertEqual(resp.status_code, 404)

    def test_invalid_edit_mode_returns_errors(self):
        payload = {"edit_mode": "not-a-choice", "body": "x"}
        resp = self.client.post(self.url, data=payload)
        # stays on page with errors
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Select a valid choice", status_code=200)
