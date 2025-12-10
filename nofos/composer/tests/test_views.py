import uuid

from composer.models import (
    ContentGuide,
    ContentGuideInstance,
    ContentGuideSection,
    ContentGuideSubsection,
)
from composer.views import ComposerSectionView
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

User = get_user_model()


class ComposerListViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="composer@example.com",
            password="testpass123",
            group="bloom",  # or whatever default group is fine
            is_staff=True,
            force_password_reset=False,
        )

        self.client.login(email="bloom@example.com", password="testpass123")

    def test_logged_in_user_sees_welcome_message(self):
        """Logged-in users should see the Composer welcome page with the correct H1 text."""
        self.client.login(email="composer@example.com", password="testpass123")
        url = reverse("composer:composer_index")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome to Composer", html=True)

    def test_anonymous_user_is_redirected_to_login(self):
        """Anonymous users should be redirected to the login page."""
        url = reverse("composer:composer_index")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("admin:login"), response.url)

    def test_no_content_guides(self):
        """When no draft or published content guides exist, the user should see the empty state"""
        self.client.login(email="composer@example.com", password="testpass123")
        url = reverse("composer:composer_index")
        response = self.client.get(url)
        self.assertContains(response, "No content guides available")
        # Create new always visible
        self.assertContains(response, "Create a new content guide")

    def test_draft_only(self):
        """When only draft content guides exist, only the draft table is visible"""
        ContentGuide.objects.create(
            title="Original Title.docx", opdiv="CDC", group="bloom", status="draft"
        )
        self.client.login(email="composer@example.com", password="testpass123")
        url = reverse("composer:composer_index")
        response = self.client.get(url)
        self.assertContains(response, "Edit draft content guides")
        self.assertNotContains(response, "Review published content guides")
        # Create new always visible
        self.assertContains(response, "Create a new content guide")

    def test_published_only(self):
        """When only published content guides exist, only the published table is visible"""
        ContentGuide.objects.create(
            title="Original Title.docx", opdiv="CDC", group="bloom", status="published"
        )
        self.client.login(email="composer@example.com", password="testpass123")
        url = reverse("composer:composer_index")
        response = self.client.get(url)
        self.assertNotContains(response, "Edit draft content guides")
        self.assertContains(response, "Review published content guides")
        # Create new always visible
        self.assertContains(response, "Create a new content guide")


class ComposerImportViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="importer@example.com",
            password="testpass123",
            group="bloom",
            is_staff=True,
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
            is_staff=True,
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
        self.assertEqual(response.status_code, 302)


class ComposerEditTitleViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            group="bloom",
            is_staff=True,
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
        self.assertEqual(response.status_code, 302)


class ComposerArchiveViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            force_password_reset=False,
            is_staff=True,
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
        self.assertIn(
            b"This Content Guide is archived and can&#x27;t be changed.",
            response.content,
        )

    def test_anonymous_user_forbidden(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)


class ComposerDocumentRedirectTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            force_password_reset=False,
            is_staff=True,
            group="bloom",
        )
        self.client.login(email="test@example.com", password="testpass123")
        # Base URL for the redirect route
        self.redirect_url_name = "composer:composer_document_redirect"

    def test_redirects_to_first_section(self):
        # Create a guide with two sections (ordered)
        guide = ContentGuide.objects.create(title="Guide A", opdiv="CDC", group="bloom")
        s1 = ContentGuideSection.objects.create(
            content_guide=guide, order=1, name="Section 1", html_id="sec-1"
        )
        ContentGuideSection.objects.create(
            content_guide=guide, order=2, name="Section 2", html_id="sec-2"
        )

        url = reverse(self.redirect_url_name, kwargs={"pk": guide.pk})
        response = self.client.get(url)

        expected = reverse(
            "composer:section_view", kwargs={"pk": guide.pk, "section_pk": s1.pk}
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, expected)

    def test_redirects_to_preview_when_published(self):
        # Create a published guide with sections
        guide = ContentGuide.objects.create(
            title="Published Guide", opdiv="CDC", group="bloom", status="published"
        )
        ContentGuideSection.objects.create(
            content_guide=guide, order=1, name="Section 1", html_id="sec-1"
        )

        url = reverse(self.redirect_url_name, kwargs={"pk": guide.pk})
        response = self.client.get(url)

        expected = reverse("composer:composer_preview", kwargs={"pk": guide.pk})

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
        self.assertIn(b"This content guide has no steps.", response.content)


class GroupSubsectionsTests(TestCase):
    def setUp(self):
        # Minimal parent objects so we can create valid subsections
        self.guide = ContentGuide.objects.create(
            title="Guide", opdiv="CDC", group="bloom"
        )
        self.section = ContentGuideSection.objects.create(
            content_guide=self.guide, order=1, name="Section 1", html_id="sec-1"
        )
        self.view = ComposerSectionView()

    def _make_subsection(
        self, name, tag=None, order=1, body="Generic body content", instructions=""
    ):
        """Helper to make a subsection instance (not saved content matters for grouping)."""
        return ContentGuideSubsection.objects.create(
            section=self.section,
            order=order,
            name=name,
            tag=tag or "",
            body=body,
            instructions=instructions,
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

    def test_header_item_with_empty_body_is_skipped(self):
        # s1 is a header (preset name); its body is empty → should NOT appear in items
        s1 = self._make_subsection("Funding details", tag="h4", order=1, body="")
        # A normal subsection after the header
        s2 = self._make_subsection(
            "Budget breakdown", tag="h5", order=2, body="Some text"
        )

        groups = self.view.group_subsections([s1, s2])

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["heading"], "Funding details")
        # Only s2 shows up because s1 (the header item) had no body
        self.assertEqual([x.pk for x in groups[0]["items"]], [s2.pk])

    def test_header_item_with_nonempty_body_is_included(self):
        # s1 is a header (preset name) with real body → should appear in items
        s1 = self._make_subsection(
            "Funding details", tag="h4", order=1, body="<p>Hello</p>"
        )
        s2 = self._make_subsection(
            "Budget breakdown", tag="h5", order=2, body="Some text"
        )

        groups = self.view.group_subsections([s1, s2])

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["heading"], "Funding details")
        # s1 included first, then s2
        self.assertEqual([x.pk for x in groups[0]["items"]], [s1.pk, s2.pk])

    def test_header_item_with_nonempty_instructions_is_included(self):
        # s1 is a header (preset name) with non-empty instructions → should appear in items
        s1 = self._make_subsection(
            "Funding details",
            tag="h4",
            order=1,
            body="",
            instructions="Please enter funding details in Canadian dollars",
        )

        s2 = self._make_subsection(
            "Budget breakdown", tag="h5", order=2, body="Some text"
        )

        groups = self.view.group_subsections([s1, s2])

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["heading"], "Funding details")
        # s1 included first, then s2
        self.assertEqual([x.pk for x in groups[0]["items"]], [s1.pk, s2.pk])


class ComposerSectionViewTests(TestCase):
    def setUp(self):
        # Auth user
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            group="bloom",
            is_staff=True,
            force_password_reset=False,
        )
        self.client.login(email="test@example.com", password="testpass123")

        # Guide + sections
        self.guide = ContentGuide.objects.create(
            title="Guide", opdiv="CDC", group="bloom"
        )
        self.sec1 = ContentGuideSection.objects.create(
            content_guide=self.guide,
            order=1,
            name="Understand the opportunity",
            html_id="s1",
        )
        self.sec2 = ContentGuideSection.objects.create(
            content_guide=self.guide, order=2, name="Get ready to apply", html_id="s2"
        )

        # Subsections for sec1 (ensure grouping behavior)
        self.subsection1 = ContentGuideSubsection.objects.create(
            section=self.sec1, order=1, name="Intro", tag="h4", body="Body 1"
        )
        # Preset header name → starts new group
        self.subsection2 = ContentGuideSubsection.objects.create(
            section=self.sec1, order=2, name="Funding details", tag="h4", body="Body 2"
        )
        # Not a header → belongs to previous group
        self.subsection3 = ContentGuideSubsection.objects.create(
            section=self.sec1, order=3, name="Budget table", tag="h5", body="Body 3"
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
        self.assertEqual([i.pk for i in grouped[0]["items"]], [self.subsection1.pk])

        # Group 2: heading = "Funding details", items = [ss2, ss3]
        self.assertEqual(grouped[1]["heading"], "Funding details")
        self.assertEqual(
            [i.pk for i in grouped[1]["items"]],
            [self.subsection2.pk, self.subsection3.pk],
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
        self.assertEqual(resp.status_code, 302)

    def test_404_when_section_not_in_document(self):
        # Make a section in a different guide and try to view with current guide pk
        other_guide = ContentGuide.objects.create(
            title="Other", opdiv="CDC", group="bloom"
        )
        stray_section = ContentGuideSection.objects.create(
            content_guide=other_guide, order=1, name="Stray", html_id="x"
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

    def test_works_with_content_guide_instance(self):
        """Test that ComposerSectionView works with ContentGuideInstance"""
        # Create a ContentGuideInstance
        instance = ContentGuideInstance.objects.create(
            title="My Draft NOFO",
            opdiv="CDC",
            group="bloom",
            parent=self.guide,
        )

        # Create sections for the instance
        instance_sec1 = ContentGuideSection.objects.create(
            content_guide_instance=instance,
            order=1,
            name="Instance Section 1",
            html_id="is1",
        )
        instance_sec2 = ContentGuideSection.objects.create(
            content_guide_instance=instance,
            order=2,
            name="Instance Section 2",
            html_id="is2",
        )

        # Create a subsection
        ContentGuideSubsection.objects.create(
            section=instance_sec1,
            order=1,
            name="Instance Subsection",
            tag="h4",
            body="Instance body",
        )

        # Test the URL with instance pk
        url = reverse(
            "composer:section_view",
            kwargs={"pk": instance.pk, "section_pk": instance_sec1.pk},
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["current_section"].pk, instance_sec1.pk)
        self.assertEqual(resp.context["document"].pk, instance.pk)

        # Verify prev/next work
        self.assertIsNone(resp.context["prev_sec"])
        self.assertIsNotNone(resp.context["next_sec"])
        self.assertEqual(resp.context["next_sec"].pk, instance_sec2.pk)

    def test_group_access_denied_for_wrong_group_instance(self):
        """Test that group access control works for ContentGuideInstance"""
        # Create a user in a different group
        other_user = User.objects.create_user(
            email="other@example.com",
            password="testpass123",
            group="hrsa",  # Different group
            force_password_reset=False,
        )

        # Create a ContentGuideInstance for CDC group
        instance = ContentGuideInstance.objects.create(
            title="CDC Draft NOFO",
            opdiv="CDC",
            group="cdc",  # Different from user's group
            parent=self.guide,
        )

        instance_sec = ContentGuideSection.objects.create(
            content_guide_instance=instance,
            order=1,
            name="Instance Section",
            html_id="is1",
        )

        # Login as the other user
        self.client.login(email="other@example.com", password="testpass123")

        url = reverse(
            "composer:section_view",
            kwargs={"pk": instance.pk, "section_pk": instance_sec.pk},
        )
        resp = self.client.get(url)
        # Should get 403 Forbidden
        self.assertEqual(resp.status_code, 403)

    def test_not_started_subsections_present_for_instance(self):
        """
        For a ContentGuideInstance, not_started_subsections should include only
        subsections where edit_mode != 'locked' and status == 'default'.
        """
        instance = ContentGuideInstance.objects.create(
            title="My Draft NOFO",
            opdiv="CDC",
            group="bloom",
            parent=self.guide,
        )

        instance_sec = ContentGuideSection.objects.create(
            content_guide_instance=instance,
            order=1,
            name="Instance Section",
            html_id="is1",
        )

        # s1: editable + default → should be included
        s1 = ContentGuideSubsection.objects.create(
            section=instance_sec,
            order=1,
            name="Editable default",
            tag="h4",
            body="Body",
            edit_mode="full",
            status="default",
        )

        # s2: locked + default → should be excluded
        s2 = ContentGuideSubsection.objects.create(
            section=instance_sec,
            order=2,
            name="Locked default",
            tag="h4",
            body="Body",
            edit_mode="locked",
            status="default",
        )

        # s3: editable but not default → should be excluded
        s3 = ContentGuideSubsection.objects.create(
            section=instance_sec,
            order=3,
            name="Editable viewed",
            tag="h4",
            body="Body with {variables}",
            edit_mode="variables",
            status="viewed",
        )

        url = reverse(
            "composer:section_view",
            kwargs={"pk": instance.pk, "section_pk": instance_sec.pk},
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        self.assertIn("not_started_subsections", resp.context)
        not_started = resp.context["not_started_subsections"]

        # Only s1 should be in the list
        self.assertEqual(len(not_started), 1)
        self.assertEqual(not_started[0].pk, s1.pk)

    def test_not_started_subsections_empty_for_instance_when_none_match(self):
        """
        For a ContentGuideInstance with subsections, not_started_subsections should be
        empty if no subsection matches (edit_mode != 'locked' and status == 'default').
        """
        instance = ContentGuideInstance.objects.create(
            title="My Other Draft NOFO",
            opdiv="CDC",
            group="bloom",
            parent=self.guide,
        )

        instance_sec = ContentGuideSection.objects.create(
            content_guide_instance=instance,
            order=1,
            name="Instance Section 2",
            html_id="is2",
        )

        # s1: locked + default → excluded (locked)
        ContentGuideSubsection.objects.create(
            section=instance_sec,
            order=1,
            name="Locked default",
            tag="h4",
            body="Body",
            edit_mode="locked",
            status="default",
        )

        # s2: editable but viewed → excluded (not default)
        ContentGuideSubsection.objects.create(
            section=instance_sec,
            order=2,
            name="Editable viewed",
            tag="h4",
            body="Body",
            edit_mode="full",
            status="viewed",
        )

        # s3: editable but done → excluded (not default)
        ContentGuideSubsection.objects.create(
            section=instance_sec,
            order=3,
            name="Editable done",
            tag="h4",
            body="Body with {variables}",
            edit_mode="variables",
            status="done",
        )

        url = reverse(
            "composer:section_view",
            kwargs={"pk": instance.pk, "section_pk": instance_sec.pk},
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        self.assertIn("not_started_subsections", resp.context)
        not_started = resp.context["not_started_subsections"]

        # We *do* have subsections, but none should qualify as "not started"
        self.assertEqual(len(not_started), 0)


class ComposerSectionEditViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            group="bloom",
            is_staff=True,
            force_password_reset=False,
        )
        self.client.login(email="test@example.com", password="testpass123")

        self.guide = ContentGuide.objects.create(
            title="Guide", opdiv="CDC", group="bloom"
        )
        self.section = ContentGuideSection.objects.create(
            content_guide=self.guide,
            order=1,
            name="Section 1",
            html_id="sec-1",
        )

        self.url = reverse(
            "composer:section_edit",
            kwargs={
                "pk": self.guide.pk,
                "section_pk": self.section.pk,
            },
        )

    def test_get_renders_for_logged_in_user(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        # context includes document + section
        self.assertEqual(resp.context["document"].pk, self.guide.pk)
        self.assertEqual(resp.context["section"].pk, self.section.pk)
        self.assertTrue(resp.context["include_scroll_to_top"])

    def test_anonymous_redirects_to_login_or_forbidden(self):
        self.client.logout()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)

    def test_404_section_not_in_document(self):
        """
        If the section_pk in the URL belongs to a different guide
        than pk, get_object should raise 404.
        """
        other_guide = ContentGuide.objects.create(
            title="Other", opdiv="CDC", group="bloom"
        )
        stray_section = ContentGuideSection.objects.create(
            content_guide=other_guide,
            order=1,
            name="Stray",
            html_id="sec-x",
        )

        bad_url = reverse(
            "composer:section_edit",
            kwargs={
                "pk": self.guide.pk,  # correct guide
                "section_pk": stray_section.pk,  # WRONG section (belongs to other_guide)
            },
        )
        resp = self.client.get(bad_url)
        self.assertEqual(resp.status_code, 404)

    def test_404_when_document_pk_mismatch(self):
        """
        If pk in the URL does not match the section's actual document.pk,
        get_object should raise 404.
        """
        other_guide = ContentGuide.objects.create(
            title="Other", opdiv="CDC", group="bloom"
        )

        bad_url = reverse(
            "composer:section_edit",
            kwargs={
                "pk": other_guide.pk,  # WRONG guide
                "section_pk": self.section.pk,  # section belongs to self.guide
            },
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
            is_staff=True,
            force_password_reset=False,
        )
        self.client.login(email="test@example.com", password="testpass123")

        # guide/sections/subsections
        self.guide = ContentGuide.objects.create(
            title="Guide", opdiv="CDC", group="bloom"
        )
        self.section = ContentGuideSection.objects.create(
            content_guide=self.guide, order=1, name="S1", html_id="s1"
        )
        self.subsection = ContentGuideSubsection.objects.create(
            section=self.section,
            order=1,
            name="SS1",
            tag="h3",
            body="Initial body",
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
        self.assertEqual(resp.status_code, 302)

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
            content_guide=self.guide, order=2, name="S2", html_id="s2"
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
            content_guide=other_guide, order=1, name="Stray", html_id="x"
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


class ComposerSubsectionCreateViewTests(TestCase):
    def setUp(self):
        # user + login
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            group="bloom",
            is_staff=True,
            force_password_reset=False,
        )
        self.client.login(email="test@example.com", password="testpass123")

        # guide/sections/subsections
        self.document = ContentGuide.objects.create(
            title="Guide", opdiv="CDC", group="bloom"
        )
        self.section = ContentGuideSection.objects.create(
            content_guide=self.document, order=1, name="S1", html_id="s1"
        )

        self.prev_subsection = ContentGuideSubsection.objects.create(
            section=self.section,
            order=1,
            name="SS1",
            tag="h3",
            body="Initial body",
            edit_mode="full",
            html_id="ss-1",
        )

        self.url = f"{reverse(
            "composer:subsection_create",
            kwargs={
                "pk": self.document.pk,
                "section_pk": self.section.pk,
            }
        )}?prev_subsection={self.prev_subsection.pk}"

    def test_get_renders_for_logged_in_user(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        # context includes document/section/subsection
        self.assertEqual(resp.context["document"].pk, self.document.pk)
        self.assertEqual(resp.context["section"].pk, self.section.pk)

    def test_anonymous_redirects_to_login(self):
        self.client.logout()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)

    def test_post_updates_and_redirects_with_anchor_prefers_html_id(self):
        payload = {
            "edit_mode": "variables",
            "body": "New **markdown** with {Variable}",
            "instructions": "Some instructions",
        }
        resp = self.client.post(self.url, data=payload, follow=False)

        # saved
        self.section.refresh_from_db()
        new_subsection = ContentGuideSubsection.objects.get(
            order=2,
            section=self.section,
        )
        self.assertEqual(new_subsection.edit_mode, "variables")
        self.assertIn("New **markdown**", new_subsection.body)
        self.assertIn("Some instructions", new_subsection.instructions)

        # redirected back to section with anchor "#<html_id>"
        expected_base = reverse(
            "composer:section_view", args=[self.document.pk, self.section.pk]
        )
        self.assertTrue(resp["Location"].startswith(expected_base))
        self.assertTrue(resp["Location"].endswith(f"#{new_subsection.html_id}"))

        # success message was added
        msgs = list(get_messages(resp.wsgi_request))
        self.assertTrue(any("Created new section:" in str(m) for m in msgs))

    def test_404_section_mismatch(self):
        other_document = ContentGuide.objects.create(
            title="Other", opdiv="CDC", group="bloom"
        )
        stray_section = ContentGuideSection.objects.create(
            content_guide=other_document, order=1, name="Other section", html_id="x"
        )

        bad_url = f"{reverse(
            'composer:subsection_create',
            kwargs={
                'pk': self.document.pk,        # correct doc
                'section_pk': stray_section.pk # WRONG section
            }
        )}?prev_subsection={self.prev_subsection.pk}"

        resp = self.client.get(bad_url)
        self.assertEqual(resp.status_code, 404)

    def test_404_document_mismatch(self):
        other_document = ContentGuide.objects.create(
            title="Other", opdiv="CDC", group="bloom"
        )

        bad_url = f"{reverse(
            'composer:subsection_create',
            kwargs={
                'pk': other_document.pk,       # WRONG doc
                'section_pk': self.section.pk  # correct section for REAL doc
            }
        )}?prev_subsection={self.prev_subsection.pk}"

        resp = self.client.get(bad_url)
        self.assertEqual(resp.status_code, 404)


class ComposerSubsectionDeleteViewTests(TestCase):
    def setUp(self):
        # user + login
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            group="bloom",
            is_staff=True,
            force_password_reset=False,
        )
        self.client.login(email="test@example.com", password="testpass123")

        # guide/sections/subsections
        self.document = ContentGuide.objects.create(
            title="Guide", opdiv="CDC", group="bloom"
        )
        self.section = ContentGuideSection.objects.create(
            content_guide=self.document, order=1, name="S1", html_id="s1"
        )

        self.subsection = ContentGuideSubsection.objects.create(
            section=self.section,
            order=1,
            name="SS1",
            tag="h3",
            body="Initial body",
            edit_mode="full",
            html_id="ss-1",
        )

        self.url = reverse(
            "composer:subsection_confirm_delete",
            kwargs={
                "pk": self.document.pk,
                "section_pk": self.section.pk,
                "subsection_pk": self.subsection.pk,
            },
        )

    def test_get_renders_for_logged_in_user(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        # context includes document/section/subsection
        self.assertEqual(resp.context["document"].pk, self.document.pk)
        self.assertEqual(resp.context["section"].pk, self.section.pk)
        self.assertEqual

    def test_anonymous_redirects_to_login(self):
        self.client.logout()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)

    def test_post_deletes_and_redirects(self):
        resp = self.client.post(self.url, follow=False)

        # deleted
        with self.assertRaises(ContentGuideSubsection.DoesNotExist):
            ContentGuideSubsection.objects.get(pk=self.subsection.pk)

        # redirected back to section without anchor
        expected_url = reverse(
            "composer:section_view", args=[self.document.pk, self.section.pk]
        )
        self.assertEqual(resp["Location"], expected_url)

        # success message was added
        msgs = list(get_messages(resp.wsgi_request))
        self.assertTrue(any("You deleted section:" in str(m) for m in msgs))

    def test_404_subsection_not_in_section(self):
        other_section = ContentGuideSection.objects.create(
            content_guide=self.document, order=2, name="S2", html_id="s2"
        )

        bad_url = reverse(
            "composer:subsection_confirm_delete",
            kwargs={
                "pk": self.document.pk,
                "section_pk": other_section.pk,  # WRONG section
                "subsection_pk": self.subsection.pk,
            },
        )
        resp = self.client.get(bad_url)
        self.assertEqual(resp.status_code, 404)

    def test_404_section_not_in_document(self):
        other_document = ContentGuide.objects.create(
            title="Other", opdiv="CDC", group="bloom"
        )
        stray_section = ContentGuideSection.objects.create(
            content_guide=other_document, order=1, name="Stray", html_id="x"
        )

        bad_url = reverse(
            "composer:subsection_confirm_delete",
            kwargs={
                "pk": self.document.pk,  # correct doc
                "section_pk": stray_section.pk,  # WRONG section for doc
                "subsection_pk": self.subsection.pk,
            },
        )
        resp = self.client.get(bad_url)
        self.assertEqual(resp.status_code, 404)

    def test_404_document_mismatch(self):
        other_document = ContentGuide.objects.create(
            title="Other", opdiv="CDC", group="bloom"
        )

        bad_url = reverse(
            "composer:subsection_confirm_delete",
            kwargs={
                "pk": other_document.pk,  # WRONG doc
                "section_pk": self.section.pk,  # correct section for REAL doc
                "subsection_pk": self.subsection.pk,
            },
        )
        resp = self.client.get(bad_url)
        self.assertEqual(resp.status_code, 404)


class ComposerSubsectionInstructionsEditViewTests(TestCase):
    def setUp(self):
        # user + login
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            group="bloom",
            is_staff=True,
            force_password_reset=False,
        )
        self.client.login(email="test@example.com", password="testpass123")

        # Document hierarchy: guide -> section -> subsection
        self.guide = ContentGuide.objects.create(
            title="Guide", opdiv="CDC", group="bloom"
        )
        self.section = ContentGuideSection.objects.create(
            content_guide=self.guide, order=1, name="S1", html_id="s1"
        )
        self.subsection = ContentGuideSubsection.objects.create(
            section=self.section,
            order=1,
            name="SS1",
            tag="h3",
            body="Initial body",
            instructions="Initial instructions",
            edit_mode="full",
            html_id="ss-1",
        )

        self.url = reverse(
            "composer:instructions_edit",
            kwargs={
                "pk": self.guide.pk,
                "section_pk": self.section.pk,
                "subsection_pk": self.subsection.pk,
            },
        )

    def test_get_renders_for_logged_in_user(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        # Context includes document + section + subsection
        self.assertEqual(resp.context["document"].pk, self.guide.pk)
        self.assertEqual(resp.context["section"].pk, self.section.pk)
        self.assertEqual(resp.context["subsection"].pk, self.subsection.pk)

    def test_anonymous_redirects_to_login(self):
        self.client.logout()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)

    def test_post_updates_instructions_and_redirects(self):
        payload = {
            "instructions": "Updated instructions!",
            "body": self.subsection.body,
            "edit_mode": self.subsection.edit_mode,
        }

        resp = self.client.post(self.url, data=payload, follow=False)

        self.subsection.refresh_from_db()
        self.assertEqual(self.subsection.instructions, "Updated instructions!")

        # redirected back to section with #anchor
        expected = reverse(
            "composer:section_view",
            args=[self.guide.pk, self.section.pk],
        )
        anchor = self.subsection.html_id
        self.assertTrue(resp["Location"].startswith(expected))
        self.assertTrue(resp["Location"].endswith(f"#{anchor}"))

        # success message was added
        msgs = list(get_messages(resp.wsgi_request))
        self.assertTrue(any("Updated instructions" in str(m) for m in msgs))

    def test_404_subsection_not_in_section(self):
        """
        section_pk does not match subsection.section.pk
        """
        other_section = ContentGuideSection.objects.create(
            content_guide=self.guide, order=2, name="S2", html_id="s2"
        )

        bad_url = reverse(
            "composer:instructions_edit",
            kwargs={
                "pk": self.guide.pk,
                "section_pk": other_section.pk,  # WRONG section
                "subsection_pk": self.subsection.pk,  # belongs to self.section
            },
        )
        resp = self.client.get(bad_url)
        self.assertEqual(resp.status_code, 404)

    def test_404_section_not_in_document(self):
        """
        section_pk belongs to a different document than pk in URL
        """
        other_guide = ContentGuide.objects.create(
            title="Other", opdiv="CDC", group="bloom"
        )
        stray_section = ContentGuideSection.objects.create(
            content_guide=other_guide, order=1, name="Stray", html_id="x"
        )

        bad_url = reverse(
            "composer:instructions_edit",
            kwargs={
                "pk": self.guide.pk,  # correct guide
                "section_pk": stray_section.pk,  # WRONG section
                "subsection_pk": self.subsection.pk,
            },
        )
        resp = self.client.get(bad_url)
        self.assertEqual(resp.status_code, 404)

    def test_404_document_mismatch(self):
        """
        pk in URL does not match subsection.section.get_document().pk
        """
        other_guide = ContentGuide.objects.create(
            title="Other", opdiv="CDC", group="bloom"
        )

        bad_url = reverse(
            "composer:instructions_edit",
            kwargs={
                "pk": other_guide.pk,  # WRONG document
                "section_pk": self.section.pk,
                "subsection_pk": self.subsection.pk,
            },
        )
        resp = self.client.get(bad_url)
        self.assertEqual(resp.status_code, 404)


class ComposerPreviewViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            group="bloom",
            is_staff=True,
            force_password_reset=False,
        )
        self.client.login(email="test@example.com", password="testpass123")

        self.guide = ContentGuide.objects.create(
            title="Test Guide", opdiv="CDC", group="bloom", status="draft"
        )
        self.section = ContentGuideSection.objects.create(
            content_guide=self.guide, order=1, name="Section 1", html_id="sec-1"
        )
        self.subsection = ContentGuideSubsection.objects.create(
            section=self.section,
            order=1,
            name="Subsection 1",
            tag="h3",
            body="Test body",
        )

        self.url = reverse("composer:composer_preview", kwargs={"pk": self.guide.pk})

    def test_get_renders_preview_page(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["document"].pk, self.guide.pk)
        self.assertTrue(resp.context["is_preview"])
        self.assertIsNotNone(resp.context["sections"])

    def test_anonymous_user_redirected(self):
        self.client.logout()
        resp = self.client.get(self.url)
        self.assertIn(resp.status_code, [302, 403])

    def test_post_unknown_action_returns_400(self):
        resp = self.client.post(self.url, {"action": "bogus"}, follow=False)
        self.assertEqual(resp.status_code, 400)

    def test_post_exit_action_redirects_with_message(self):
        resp = self.client.post(self.url, {"action": "exit"}, follow=False)

        # Redirects to index
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("composer:composer_index"))

        # Session variable set for success heading
        follow_resp = self.client.get(resp["Location"])
        self.assertEqual(
            follow_resp.context["success_heading"],
            "Your content guide was successfully saved",
        )

        # Success message was added
        msgs = list(get_messages(resp.wsgi_request))
        edit_link = reverse(
            "composer:composer_document_redirect", kwargs={"pk": self.guide.pk}
        )
        self.assertTrue(
            any(
                f"You saved: “<a href='{edit_link}'>{self.guide.title}</a>”" in str(m)
                for m in msgs
            )
        )

    def test_post_publish_action_updates_status(self):
        resp = self.client.post(self.url, {"action": "publish"}, follow=False)

        # Document status updated
        self.guide.refresh_from_db()
        self.assertEqual(self.guide.status, "published")

        # Redirects back to same page
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, self.url)

        # Session variable set
        follow_resp = self.client.get(resp["Location"])
        self.assertEqual(
            follow_resp.context["success_heading"],
            "Your content guide was successfully published",
        )

        # Success message was added
        msgs = list(get_messages(resp.wsgi_request))
        self.assertTrue(any("available for writers" in str(m) for m in msgs))

    def test_post_publish_action_errors_if_already_published(self):
        self.guide.status = "published"
        self.guide.save()

        resp = self.client.post(self.url, {"action": "publish"}, follow=False)

        # Stays on same page with error
        self.assertEqual(resp.status_code, 400)

    def test_sidenav_hidden_when_published(self):
        # Initially draft → sidenav shown
        resp = self.client.get(self.url)
        self.assertContains(resp, "Steps in this content guide")

        # Publish the guide
        self.guide.status = "published"
        self.guide.save()

        resp = self.client.get(self.url)
        self.assertNotContains(resp, "Steps in this content guide")

    def test_warning_when_archived__no_successor(self):
        # Not archived → no warning
        resp = self.client.get(self.url)
        self.assertNotContains(resp, "Archived content guide")

        # Archived → shows warning
        self.guide.archived = timezone.now()
        self.guide.save()

        resp = self.client.get(self.url)
        self.assertContains(resp, "Archived content guide")

    def test_warning_when_archived__with_successor(self):
        # Archived → shows warning
        self.guide.archived = timezone.now()
        self.guide.successor = ContentGuide.objects.create(
            title="New Guide", opdiv="CDC", group="bloom", status="draft"
        )
        self.guide.save()

        resp = self.client.get(self.url)
        self.assertContains(resp, "Past version of New Guide")


class ComposerUnpublishViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            group="bloom",
            is_staff=True,
            force_password_reset=False,
        )
        self.client.login(email="test@example.com", password="testpass123")

        # Create a published guide with sections and subsections
        self.guide = ContentGuide.objects.create(
            title="Published Guide", opdiv="CDC", group="bloom", status="published"
        )
        self.section = ContentGuideSection.objects.create(
            content_guide=self.guide, order=1, name="Section 1", html_id="sec-1"
        )
        self.subsection = ContentGuideSubsection.objects.create(
            section=self.section,
            order=1,
            name="Subsection 1",
            tag="h3",
            body="Test body",
            instructions="Test instructions",
        )

        self.url = reverse("composer:composer_unpublish", kwargs={"pk": self.guide.pk})

    def test_cannot_unpublish_draft_document(self):
        draft_guide = ContentGuide.objects.create(
            title="Draft Guide", opdiv="CDC", group="bloom", status="draft"
        )
        url = reverse("composer:composer_unpublish", kwargs={"pk": draft_guide.pk})

        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 400)
        self.assertIn(b"not yet published", resp.content)

    def test_post_creates_archived_duplicate_and_unpublishes(self):
        original_pk = self.guide.pk
        original_section_count = self.guide.sections.count()
        original_subsection_count = ContentGuideSubsection.objects.filter(
            section__content_guide=self.guide
        ).count()

        resp = self.client.post(self.url, follow=False)

        # Original guide is now draft and not archived
        self.guide.refresh_from_db()
        self.assertEqual(self.guide.status, "draft")
        self.assertIsNone(self.guide.archived)

        # Archived duplicate was created
        archived = ContentGuide.objects.filter(
            successor=self.guide, archived__isnull=False
        ).first()
        self.assertIsNotNone(archived)
        self.assertEqual(archived.title, self.guide.title)
        self.assertIsNotNone(archived.archived)

        # Archived duplicate has same structure
        archived_section_count = archived.sections.count()
        archived_subsection_count = ContentGuideSubsection.objects.filter(
            section__content_guide=archived
        ).count()
        self.assertEqual(archived_section_count, original_section_count)
        self.assertEqual(archived_subsection_count, original_subsection_count)

        # Redirected to preview page
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            resp.url, reverse("composer:composer_preview", kwargs={"pk": original_pk})
        )

    def test_archived_duplicate_preserves_data(self):
        ContentGuideSubsection.objects.create(
            section=self.section,
            order=2,
            name="Subsection 2",
            tag="h4",
            body="Second body",
            instructions="Second instructions",
        )

        self.client.post(self.url)

        # Get the archived copy
        archived = ContentGuide.objects.filter(
            successor=self.guide, archived__isnull=False
        ).first()
        archived_section = archived.sections.first()
        archived_subsections = list(archived_section.subsections.order_by("order"))

        # Verify first subsection
        self.assertEqual(archived_subsections[0].name, "Subsection 1")
        self.assertEqual(archived_subsections[0].body, "Test body")
        self.assertEqual(archived_subsections[0].instructions, "Test instructions")

        # Verify second subsection
        self.assertEqual(archived_subsections[1].name, "Subsection 2")
        self.assertEqual(archived_subsections[1].body, "Second body")
        self.assertEqual(archived_subsections[1].instructions, "Second instructions")

    def test_duplicate_not_created_if_something_fails(self):
        # Simulate failure by making the ContentGuideSubsection save raise an error
        original_bulk_create = ContentGuideSubsection.objects.bulk_create

        def failing_save(self, *args, **kwargs):
            raise Exception("Simulated subsection bulk_create failure")

        ContentGuideSubsection.objects.bulk_create = failing_save

        with self.assertRaises(Exception):
            self.client.post(self.url)

        # Ensure no archived duplicate was created
        archived = ContentGuide.objects.filter(
            successor=self.guide, archived__isnull=False
        ).first()
        self.assertIsNone(archived)

        # Restore original save method
        ContentGuideSubsection.objects.bulk_create = original_bulk_create

    def test_unpublish_repoints_instances_to_archived_duplicate(self):
        # Create an instance that points to the original (published) guide
        instance = ContentGuideInstance.objects.create(
            title="ContentGuideInstance 1",
            opdiv="CDC",
            group="bloom",
            parent=self.guide,
        )

        # Instance starts with parent = original guide
        self.assertEqual(instance.parent, self.guide)

        # Unpublish the guide
        resp = self.client.post(self.url, follow=False)
        self.assertEqual(resp.status_code, 302)

        # Get the archived duplicate created during unpublish
        archived = ContentGuide.objects.filter(
            successor=self.guide,
            archived__isnull=False,
        ).first()
        self.assertIsNotNone(
            archived, "Archived duplicate should exist after unpublish"
        )

        # Refresh instance from DB and confirm its parent now points to the archived guide
        instance.refresh_from_db()
        self.assertEqual(
            instance.parent,
            archived,
            "ContentGuideInstance.parent should point to the archived duplicate after unpublish",
        )

    def test_anonymous_redirects_to_login(self):
        self.client.logout()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)


class StaffMemberRequiredTests(TestCase):
    """Tests to verify that staff_member_required is properly enforced on composer views."""

    def setUp(self):
        # Create a non-staff user
        self.non_staff_user = User.objects.create_user(
            email="nonstaff@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
            is_staff=False,
        )

        # Create a staff user
        self.staff_user = User.objects.create_user(
            email="staff@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
            is_staff=True,
        )

        # Create a content guide with sections and subsections for testing
        self.guide = ContentGuide.objects.create(
            title="Test Guide", opdiv="CDC", group="bloom", status="draft"
        )
        self.section = ContentGuideSection.objects.create(
            content_guide=self.guide, name="Test Section", order=1
        )
        self.subsection = ContentGuideSubsection.objects.create(
            section=self.section,
            name="Test Subsection",
            order=1,
            body="Test body",
            tag="h4",
        )

    def test_composer_list_view_requires_staff(self):
        """ComposerListView should redirect non-staff users to admin login."""
        self.client.login(email="nonstaff@example.com", password="testpass123")
        url = reverse("composer:composer_index")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_composer_list_view_allows_staff(self):
        """ComposerListView should allow staff users."""
        self.client.login(email="staff@example.com", password="testpass123")
        url = reverse("composer:composer_index")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_composer_import_view_requires_staff(self):
        """ComposerImportView should redirect non-staff users to admin login."""
        self.client.login(email="nonstaff@example.com", password="testpass123")
        url = reverse("composer:composer_import")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_composer_import_view_allows_staff(self):
        """ComposerImportView should allow staff users."""
        self.client.login(email="staff@example.com", password="testpass123")
        url = reverse("composer:composer_import")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_composer_import_title_view_requires_staff(self):
        """ComposerImportTitleView should redirect non-staff users to admin login."""
        self.client.login(email="nonstaff@example.com", password="testpass123")
        url = reverse("composer:composer_import_title", kwargs={"pk": self.guide.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_composer_import_title_view_allows_staff(self):
        """ComposerImportTitleView should allow staff users."""
        self.client.login(email="staff@example.com", password="testpass123")
        url = reverse("composer:composer_import_title", kwargs={"pk": self.guide.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_composer_edit_title_view_requires_staff(self):
        """ComposerEditTitleView should redirect non-staff users to admin login."""
        self.client.login(email="nonstaff@example.com", password="testpass123")
        url = reverse("composer:composer_edit_title", kwargs={"pk": self.guide.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_composer_edit_title_view_allows_staff(self):
        """ComposerEditTitleView should allow staff users."""
        self.client.login(email="staff@example.com", password="testpass123")
        url = reverse("composer:composer_edit_title", kwargs={"pk": self.guide.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_composer_archive_view_requires_staff(self):
        """ComposerArchiveView should redirect non-staff users to admin login."""
        self.client.login(email="nonstaff@example.com", password="testpass123")
        url = reverse("composer:composer_archive", kwargs={"pk": self.guide.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_composer_archive_view_allows_staff(self):
        """ComposerArchiveView should allow staff users."""
        self.client.login(email="staff@example.com", password="testpass123")
        url = reverse("composer:composer_archive", kwargs={"pk": self.guide.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_composer_unpublish_view_requires_staff(self):
        """ComposerUnpublishView should redirect non-staff users to admin login."""
        # Set guide to published so we can unpublish it
        self.guide.status = "published"
        self.guide.save()

        self.client.login(email="nonstaff@example.com", password="testpass123")
        url = reverse("composer:composer_unpublish", kwargs={"pk": self.guide.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_composer_unpublish_view_allows_staff(self):
        """ComposerUnpublishView should allow staff users."""
        # Set guide to published so we can unpublish it
        self.guide.status = "published"
        self.guide.save()

        self.client.login(email="staff@example.com", password="testpass123")
        url = reverse("composer:composer_unpublish", kwargs={"pk": self.guide.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_composer_history_view_requires_staff(self):
        """ComposerHistoryView should redirect non-staff users to admin login."""
        self.client.login(email="nonstaff@example.com", password="testpass123")
        url = reverse("composer:composer_history", kwargs={"pk": self.guide.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_composer_history_view_allows_staff(self):
        """ComposerHistoryView should allow staff users."""
        self.client.login(email="staff@example.com", password="testpass123")
        url = reverse("composer:composer_history", kwargs={"pk": self.guide.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_composer_document_redirect_requires_staff(self):
        """composer_document_redirect should redirect non-staff users to admin login."""
        self.client.login(email="nonstaff@example.com", password="testpass123")
        url = reverse(
            "composer:composer_document_redirect", kwargs={"pk": self.guide.pk}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_composer_document_redirect_allows_staff(self):
        """composer_document_redirect should allow staff users."""
        self.client.login(email="staff@example.com", password="testpass123")
        url = reverse(
            "composer:composer_document_redirect", kwargs={"pk": self.guide.pk}
        )
        response = self.client.get(url)
        # Should redirect to section_view or composer_preview
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("/admin/login/", response.url)

    def test_composer_section_edit_view_requires_staff(self):
        """ComposerSectionEditView should redirect non-staff users to admin login."""
        self.client.login(email="nonstaff@example.com", password="testpass123")
        url = reverse(
            "composer:section_edit",
            kwargs={"pk": self.guide.pk, "section_pk": self.section.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_composer_section_edit_view_allows_staff(self):
        """ComposerSectionEditView should allow staff users."""
        self.client.login(email="staff@example.com", password="testpass123")
        url = reverse(
            "composer:section_edit",
            kwargs={"pk": self.guide.pk, "section_pk": self.section.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_composer_subsection_create_view_requires_staff(self):
        """ComposerSubsectionCreateView should redirect non-staff users to admin login."""
        self.client.login(email="nonstaff@example.com", password="testpass123")
        url = reverse(
            "composer:subsection_create",
            kwargs={"pk": self.guide.pk, "section_pk": self.section.pk},
        )
        url += f"?prev_subsection={self.subsection.pk}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_composer_subsection_create_view_allows_staff(self):
        """ComposerSubsectionCreateView should allow staff users."""
        self.client.login(email="staff@example.com", password="testpass123")
        url = reverse(
            "composer:subsection_create",
            kwargs={"pk": self.guide.pk, "section_pk": self.section.pk},
        )
        url += f"?prev_subsection={self.subsection.pk}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_composer_subsection_edit_view_requires_staff(self):
        """ComposerSubsectionEditView should redirect non-staff users to admin login."""
        self.client.login(email="nonstaff@example.com", password="testpass123")
        url = reverse(
            "composer:subsection_edit",
            kwargs={
                "pk": self.guide.pk,
                "section_pk": self.section.pk,
                "subsection_pk": self.subsection.pk,
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_composer_subsection_edit_view_allows_staff(self):
        """ComposerSubsectionEditView should allow staff users."""
        self.client.login(email="staff@example.com", password="testpass123")
        url = reverse(
            "composer:subsection_edit",
            kwargs={
                "pk": self.guide.pk,
                "section_pk": self.section.pk,
                "subsection_pk": self.subsection.pk,
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_composer_subsection_delete_view_requires_staff(self):
        """ComposerSubsectionDeleteView should redirect non-staff users to admin login."""
        self.client.login(email="nonstaff@example.com", password="testpass123")
        url = reverse(
            "composer:subsection_confirm_delete",
            kwargs={
                "pk": self.guide.pk,
                "section_pk": self.section.pk,
                "subsection_pk": self.subsection.pk,
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_composer_subsection_delete_view_allows_staff(self):
        """ComposerSubsectionDeleteView should allow staff users."""
        self.client.login(email="staff@example.com", password="testpass123")
        url = reverse(
            "composer:subsection_confirm_delete",
            kwargs={
                "pk": self.guide.pk,
                "section_pk": self.section.pk,
                "subsection_pk": self.subsection.pk,
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_composer_subsection_instructions_edit_view_requires_staff(self):
        """ComposerSubsectionInstructionsEditView should redirect non-staff users to admin login."""
        self.client.login(email="nonstaff@example.com", password="testpass123")
        url = reverse(
            "composer:instructions_edit",
            kwargs={
                "pk": self.guide.pk,
                "section_pk": self.section.pk,
                "subsection_pk": self.subsection.pk,
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_composer_subsection_instructions_edit_view_allows_staff(self):
        """ComposerSubsectionInstructionsEditView should allow staff users."""
        self.client.login(email="staff@example.com", password="testpass123")
        url = reverse(
            "composer:instructions_edit",
            kwargs={
                "pk": self.guide.pk,
                "section_pk": self.section.pk,
                "subsection_pk": self.subsection.pk,
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class ComposerPreviewViewStaffRequiredTests(TestCase):
    """Tests for the custom staff requirement logic in ComposerPreviewView."""

    def setUp(self):
        # Create a non-staff user
        self.non_staff_user = User.objects.create_user(
            email="nonstaff@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
            is_staff=False,
        )

        # Create a staff user
        self.staff_user = User.objects.create_user(
            email="staff@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
            is_staff=True,
        )

        # Create a published content guide
        self.published_guide = ContentGuide.objects.create(
            title="Published Guide",
            opdiv="CDC",
            group="bloom",
            status="published",
            archived=None,
        )

        # Create a draft content guide
        self.draft_guide = ContentGuide.objects.create(
            title="Draft Guide",
            opdiv="CDC",
            group="bloom",
            status="draft",
            archived=None,
        )

    def test_draft_guide_requires_staff(self):
        """Non-staff users should be redirected when accessing draft content guides."""
        self.client.login(email="nonstaff@example.com", password="testpass123")
        url = reverse("composer:composer_preview", kwargs={"pk": self.draft_guide.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_draft_guide_allows_staff(self):
        """Staff users should be able to access non-archived content guides."""
        self.client.login(email="staff@example.com", password="testpass123")
        url = reverse("composer:composer_preview", kwargs={"pk": self.draft_guide.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_published_guide_allows_non_staff(self):
        """Non-staff users should be able to access published content guides."""
        self.client.login(email="nonstaff@example.com", password="testpass123")
        url = reverse(
            "composer:composer_preview", kwargs={"pk": self.published_guide.pk}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_published_guide_allows_staff(self):
        """Staff users should be able to access published content guides."""
        self.client.login(email="staff@example.com", password="testpass123")
        url = reverse(
            "composer:composer_preview", kwargs={"pk": self.published_guide.pk}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_anonymous_user_redirected_to_login(self):
        """Anonymous users should be redirected to login page (LoginRequiredMixin)."""
        url = reverse(
            "composer:composer_preview", kwargs={"pk": self.published_guide.pk}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("users:login"), response.url)


class ComposerSectionViewStaffRequiredTests(TestCase):
    """Tests for the custom staff requirement logic in ComposerSectionView."""

    def setUp(self):
        # Create a non-staff user
        self.non_staff_user = User.objects.create_user(
            email="nonstaff@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
            is_staff=False,
        )

        # Create a staff user
        self.staff_user = User.objects.create_user(
            email="staff@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
            is_staff=True,
        )

        # Create a content guide with a section
        self.guide = ContentGuide.objects.create(
            title="Test Guide",
            opdiv="CDC",
            group="bloom",
            status="draft",
        )
        self.section = ContentGuideSection.objects.create(
            content_guide=self.guide, name="Test Section", order=1
        )

        # Create a content guide instance with a section
        self.instance = ContentGuideInstance.objects.create(
            parent=self.guide,
            opdiv="CDC",
            group="bloom",
        )
        self.instance_section = ContentGuideSection.objects.create(
            content_guide_instance=self.instance,
            name="Test instance section",
            order=1,
        )

    def test_section_view_requires_staff__if_ContentGuide(self):
        """Non-staff users should be redirected when accessing sections of content guides."""
        self.client.login(email="nonstaff@example.com", password="testpass123")
        url = reverse(
            "composer:section_view",
            kwargs={"pk": self.guide.pk, "section_pk": self.section.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("admin:login"), response.url)

        # Publish content guide and confirm we still cannot access
        self.guide.status = "published"
        self.guide.save()

        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("admin:login"), response.url)

    def test_section_view_allows_staff__if_ContentGuide(self):
        """Staff users should be able to access sections of content guides."""
        self.client.login(email="staff@example.com", password="testpass123")
        url = reverse(
            "composer:section_view",
            kwargs={"pk": self.guide.pk, "section_pk": self.section.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.guide.status = "published"
        self.guide.save()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_section_view_allows_non_staff__if_ContentGuideInstance(self):
        """Non-staff users should be able to access sections of content guide instances."""
        self.client.login(email="nonstaff@example.com", password="testpass123")
        url = reverse(
            "composer:writer_section_view",
            kwargs={"pk": self.instance.pk, "section_pk": self.instance_section.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class PreventIfContentGuideArchivedMixinTests(TestCase):
    """
    Tests for the PreventIfContentGuideArchivedMixin to ensure that all views
    using this mixin properly prevent access to archived ContentGuides.

    The mixin is applied to the following views:
    - ComposerEditTitleView
    - ComposerArchiveView
    - ComposerUnpublishView
    - ComposerSectionView
    - ComposerSectionEditView
    - ComposerSubsectionCreateView
    - ComposerSubsectionEditView
    - ComposerSubsectionDeleteView
    - ComposerSubsectionInstructionsEditView
    """

    def setUp(self):
        # Create a staff user for testing
        self.user = User.objects.create_user(
            email="staff@example.com",
            password="testpass123",
            force_password_reset=False,
            is_staff=True,
            group="bloom",
        )
        self.client.login(email="staff@example.com", password="testpass123")

        # Create a non-archived content guide
        self.content_guide = ContentGuide.objects.create(
            title="Test Content Guide",
            opdiv="CDC",
            group="bloom",
            status="draft",
        )

        # Create a section with subsections for testing
        self.section = ContentGuideSection.objects.create(
            content_guide=self.content_guide,
            name="Test Section",
            order=1,
        )

        self.subsection = ContentGuideSubsection.objects.create(
            section=self.section,
            name="Test Subsection",
            tag="h4",
            body="Test body content",
            order=1,
            html_id="test-subsection",
        )

        # Create another subsection for create tests
        self.subsection2 = ContentGuideSubsection.objects.create(
            section=self.section,
            name="Test Subsection 2",
            tag="h4",
            body="Test body content 2",
            order=2,
            html_id="test-subsection-2",
        )

    def test_composer_edit_title_view_prevents_archived(self):
        """ComposerEditTitleView should return 400 for archived content guide"""
        # Archive the content guide
        self.content_guide.archived = timezone.now()
        self.content_guide.save()

        url = reverse("composer:composer_edit_title", args=[self.content_guide.pk])

        # Test GET request
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            b"This Content Guide is archived and can&#x27;t be changed",
            response.content,
        )

        # Test POST request
        response = self.client.post(url, {"title": "New Title"})
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            b"This Content Guide is archived and can&#x27;t be changed",
            response.content,
        )

    def test_composer_archive_view_prevents_archived(self):
        """ComposerArchiveView should return 400 for archived content guide"""
        # Archive the content guide
        self.content_guide.archived = timezone.now()
        self.content_guide.save()

        url = reverse("composer:composer_archive", args=[self.content_guide.pk])

        # Test GET request
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            b"This Content Guide is archived and can&#x27;t be changed",
            response.content,
        )

        # Test POST request
        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            b"This Content Guide is archived and can&#x27;t be changed",
            response.content,
        )

    def test_composer_unpublish_view_prevents_archived(self):
        """ComposerUnpublishView should return 400 for archived content guide"""
        # Set content guide to published, then archive it
        self.content_guide.status = "published"
        self.content_guide.archived = timezone.now()
        self.content_guide.save()

        url = reverse("composer:composer_unpublish", args=[self.content_guide.pk])

        # Test GET request
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            b"This Content Guide is archived and can&#x27;t be changed",
            response.content,
        )

        # Test POST request
        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            b"This Content Guide is archived and can&#x27;t be changed",
            response.content,
        )

    def test_composer_section_view_prevents_archived(self):
        """ComposerSectionView should return 400 for archived content guide"""
        # Archive the content guide
        self.content_guide.archived = timezone.now()
        self.content_guide.save()

        url = reverse(
            "composer:section_view", args=[self.content_guide.pk, self.section.pk]
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            b"This Content Guide is archived and can&#x27;t be changed",
            response.content,
        )

    def test_composer_section_edit_view_prevents_archived(self):
        """ComposerSectionEditView should return 400 for archived content guide"""
        # Archive the content guide
        self.content_guide.archived = timezone.now()
        self.content_guide.save()

        url = reverse(
            "composer:section_edit", args=[self.content_guide.pk, self.section.pk]
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            b"This Content Guide is archived and can&#x27;t be changed",
            response.content,
        )

    def test_composer_subsection_create_view_prevents_archived(self):
        """ComposerSubsectionCreateView should return 400 for archived content guide"""
        # Archive the content guide
        self.content_guide.archived = timezone.now()
        self.content_guide.save()

        url = (
            reverse(
                "composer:subsection_create",
                args=[self.content_guide.pk, self.section.pk],
            )
            + f"?prev_subsection={self.subsection.pk}"
        )

        # Test GET request
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            b"This Content Guide is archived and can&#x27;t be changed",
            response.content,
        )

        # Test POST request
        response = self.client.post(
            url,
            {
                "name": "New Subsection",
                "body": "New body",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            b"This Content Guide is archived and can&#x27;t be changed",
            response.content,
        )

    def test_composer_subsection_edit_view_prevents_archived(self):
        """ComposerSubsectionEditView should return 400 for archived content guide"""
        # Archive the content guide
        self.content_guide.archived = timezone.now()
        self.content_guide.save()

        url = reverse(
            "composer:subsection_edit",
            args=[self.content_guide.pk, self.section.pk, self.subsection.pk],
        )

        # Test GET request
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            b"This Content Guide is archived and can&#x27;t be changed",
            response.content,
        )

        # Test POST request
        response = self.client.post(
            url,
            {
                "name": "Updated Subsection",
                "body": "Updated body",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            b"This Content Guide is archived and can&#x27;t be changed",
            response.content,
        )

    def test_composer_subsection_delete_view_prevents_archived(self):
        """ComposerSubsectionDeleteView should return 400 for archived content guide"""
        # Archive the content guide
        self.content_guide.archived = timezone.now()
        self.content_guide.save()

        url = reverse(
            "composer:subsection_confirm_delete",
            args=[self.content_guide.pk, self.section.pk, self.subsection.pk],
        )

        # Test GET request
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            b"This Content Guide is archived and can&#x27;t be changed",
            response.content,
        )

        # Test POST request
        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            b"This Content Guide is archived and can&#x27;t be changed",
            response.content,
        )

    def test_composer_subsection_instructions_edit_view_prevents_archived(self):
        """ComposerSubsectionInstructionsEditView should return 400 for archived content guide"""
        # Archive the content guide
        self.content_guide.archived = timezone.now()
        self.content_guide.save()

        url = reverse(
            "composer:instructions_edit",
            args=[self.content_guide.pk, self.section.pk, self.subsection.pk],
        )

        # Test GET request
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            b"This Content Guide is archived and can&#x27;t be changed",
            response.content,
        )

        # Test POST request
        response = self.client.post(
            url,
            {
                "instructions": "Updated instructions",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            b"This Content Guide is archived and can&#x27;t be changed",
            response.content,
        )

    def test_non_archived_content_guide_allows_access(self):
        """All views should allow access to non-archived content guides"""
        # Test ComposerEditTitleView
        url = reverse("composer:composer_edit_title", args=[self.content_guide.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Test ComposerArchiveView
        url = reverse("composer:composer_archive", args=[self.content_guide.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Test ComposerSectionView
        url = reverse(
            "composer:section_view", args=[self.content_guide.pk, self.section.pk]
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Test ComposerSectionEditView
        url = reverse(
            "composer:section_edit", args=[self.content_guide.pk, self.section.pk]
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Test ComposerSubsectionCreateView
        url = (
            reverse(
                "composer:subsection_create",
                args=[self.content_guide.pk, self.section.pk],
            )
            + f"?prev_subsection={self.subsection.pk}"
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Test ComposerSubsectionEditView
        url = reverse(
            "composer:subsection_edit",
            args=[self.content_guide.pk, self.section.pk, self.subsection.pk],
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Test ComposerSubsectionDeleteView
        url = reverse(
            "composer:subsection_confirm_delete",
            args=[self.content_guide.pk, self.section.pk, self.subsection.pk],
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Test ComposerSubsectionInstructionsEditView
        url = reverse(
            "composer:instructions_edit",
            args=[self.content_guide.pk, self.section.pk, self.subsection.pk],
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
