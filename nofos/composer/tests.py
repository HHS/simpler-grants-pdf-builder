from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import ContentGuide, ContentGuideSection, ContentGuideSubsection
from .views import ComposerSectionView

User = get_user_model()


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
