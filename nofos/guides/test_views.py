import csv
import io
import json
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from guides.models import ContentGuide, ContentGuideSection, ContentGuideSubsection

from nofos.models import Nofo

User = get_user_model()


class ContentGuideListViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client.login(email="user@example.com", password="testpass123")

        self.guide1 = ContentGuide.objects.create(
            title="Older", group="bloom", opdiv="CDC"
        )
        self.guide2 = ContentGuide.objects.create(
            title="Newer", group="bloom", opdiv="CDC"
        )
        self.guide2.save()  # ensure updated is later

    def test_view_returns_200_for_logged_in_user(self):
        url = reverse("guides:guide_index")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_guides_are_ordered_by_updated_desc(self):
        url = reverse("guides:guide_index")
        response = self.client.get(url)
        guides = list(response.context["content_guides"])
        self.assertEqual(guides, sorted(guides, key=lambda g: g.updated, reverse=True))

    def test_redirects_anonymous_user(self):
        self.client.logout()
        url = reverse("guides:guide_index")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_archived_guides_are_excluded(self):
        # Archive one of the guides
        self.guide1.archived = timezone.now()
        self.guide1.save()

        url = reverse("guides:guide_index")
        response = self.client.get(url)
        guides = list(response.context["content_guides"])

        self.assertNotIn(self.guide1, guides)
        self.assertIn(self.guide2, guides)
        self.assertEqual(len(guides), 1)


class ContentGuideImportViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="importer@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client.login(email="importer@example.com", password="testpass123")
        self.url = reverse("guides:guide_import")

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


# Edit the title right after importing
class ContentGuideImportTitleViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            force_password_reset=False,
            group="bloom",
        )
        self.client.login(email="test@example.com", password="testpass123")

        self.guide = ContentGuide.objects.create(
            title="Original Title", opdiv="CDC", group="bloom"
        )
        self.url = reverse("guides:guide_import_title", kwargs={"pk": self.guide.pk})
        self.redirect_url = reverse(
            "guides:guide_compare", kwargs={"pk": self.guide.pk}
        )

    def test_view_returns_200_for_authorized_user(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_post_valid_data_updates_title(self):
        response = self.client.post(self.url, {"title": "Updated Title"})
        self.guide.refresh_from_db()
        self.assertEqual(self.guide.title, "Updated Title")
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
        self.assertNotEqual(response.status_code, 200)
        self.assertIn(response.status_code, [302, 403])


# Edit the title from the "edit" screen
class ContentGuideEditTitleViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            force_password_reset=False,
            group="bloom",
        )
        self.client.login(email="test@example.com", password="testpass123")

        self.guide = ContentGuide.objects.create(
            title="Original Title", opdiv="CDC", group="bloom"
        )
        self.url = reverse("guides:guide_edit_title", kwargs={"pk": self.guide.pk})
        self.redirect_url = reverse("guides:guide_edit", kwargs={"pk": self.guide.pk})

    def test_view_returns_200_for_authorized_user(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_post_valid_data_updates_title(self):
        response = self.client.post(self.url, {"title": "Updated Title"})
        self.guide.refresh_from_db()
        self.assertEqual(self.guide.title, "Updated Title")
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
        self.assertIn(response.status_code, [302, 403])


class ContentGuideArchiveViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            force_password_reset=False,
            group="bloom",
        )
        self.client.login(email="test@example.com", password="testpass123")

        self.guide = ContentGuide.objects.create(
            title="Test Content Guide",
            opdiv="CDC",
            group="bloom",
        )
        self.url = reverse("guides:guide_archive", args=[self.guide.id])

    def test_get_view_renders_confirmation_page(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Are you absolutely sure you want to delete “Test Content Guide”?",
        )

    def test_post_archives_guide(self):
        response = self.client.post(self.url)
        self.guide.refresh_from_db()
        self.assertIsNotNone(self.guide.archived)
        self.assertRedirects(response, reverse("guides:guide_index"))

    def test_cannot_archive_already_archived_guide(self):
        self.guide.archived = timezone.now()
        self.guide.save()

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"already archived", response.content)

    def test_anonymous_user_forbidden(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertIn(b"Permission denied", response.content)


class ContentGuideEditViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client.login(email="user@example.com", password="testpass123")

        self.guide = ContentGuide.objects.create(
            title="Test Content Guide",
            opdiv="CDC",
            group="bloom",
        )

        self.section1 = ContentGuideSection.objects.create(
            name="Introduction",
            html_id="intro",
            order=1,
            content_guide=self.guide,
        )
        self.section2 = ContentGuideSection.objects.create(
            name="Eligibility",
            html_id="eligibility",
            order=2,
            content_guide=self.guide,
        )

        self.url = reverse("guides:guide_edit", args=[self.guide.pk])

    def test_view_displays_guide_title(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"Configure Content Guide: “{self.guide.title}”")

    def test_view_displays_section_names(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.section1.name)
        self.assertContains(response, self.section2.name)

    def test_view_shows_archived_warning_if_guide_is_archived(self):
        self.guide.archived = timezone.now()
        self.guide.save()

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Archived Content Guide")

    def test_post_updates_subsections(self):
        """Test that POST request can handle multiple subsections at once"""
        # Create multiple subsections that need to be updated
        subsection1 = ContentGuideSubsection.objects.create(
            section=self.section1,
            name="Test Subsection 1",
            order=1,
            tag="h3",
            comparison_type="none",
        )
        subsection2 = ContentGuideSubsection.objects.create(
            section=self.section2,
            name="Test Subsection 2",
            order=1,
            tag="h3",
            comparison_type="body",
        )
        # Create a subsection that does not need to be updated
        subsection3 = ContentGuideSubsection.objects.create(
            section=self.section1,
            name="Test Subsection 3",
            order=2,
            tag="h3",
            comparison_type="body",
        )

        response = self.client.post(
            self.url,
            data=json.dumps(
                {
                    "subsections": {
                        str(subsection1.id): True,
                        str(subsection2.id): False,
                        str(subsection3.id): True,
                    }
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        # Check JSON response
        response_data = response.json()
        self.assertEqual(response_data["status"], "success")
        self.assertEqual(response_data["selections_count"], 3)
        self.assertEqual(response_data["updated_count"], 2)
        self.assertEqual(response_data["failed_subsection_ids"], [])

        subsection1.refresh_from_db()
        subsection2.refresh_from_db()
        subsection3.refresh_from_db()
        self.assertEqual(subsection1.comparison_type, "body")
        self.assertEqual(subsection2.comparison_type, "none")
        self.assertEqual(subsection3.comparison_type, "body")

    def test_post_with_invalid_subsection_ids_returns_partial_status(self):
        """Test that POST request handles invalid subsection IDs gracefully"""
        # Create one valid subsection
        subsection1 = ContentGuideSubsection.objects.create(
            section=self.section1,
            name="Valid Subsection",
            order=1,
            tag="h3",
            comparison_type="none",
        )

        # Use one valid ID and one invalid ID
        invalid_id = "99999"

        response = self.client.post(
            self.url,
            data=json.dumps(
                {
                    "subsections": {
                        str(subsection1.id): True,  # Valid subsection
                        invalid_id: False,  # Invalid subsection
                    }
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

        # Check JSON response for partial failure
        response_data = response.json()
        self.assertEqual(response_data["status"], "partial")
        self.assertEqual(response_data["selections_count"], 2)
        self.assertEqual(response_data["updated_count"], 1)
        self.assertEqual(response_data["failed_subsection_ids"], [invalid_id])
        self.assertIn("Some comparison selections failed", response_data["message"])

        # Verify valid subsection was updated
        subsection1.refresh_from_db()
        self.assertEqual(subsection1.comparison_type, "body")

    def test_post_with_all_invalid_subsection_ids_returns_fail_status(self):
        """Test that POST request with all invalid IDs returns fail status"""
        response = self.client.post(
            self.url,
            data=json.dumps(
                {
                    "subsections": {
                        "99999": True,  # Invalid subsection
                        "88888": False,  # Invalid subsection
                    }
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

        # Check JSON response for complete failure
        response_data = response.json()
        self.assertEqual(response_data["status"], "fail")
        self.assertEqual(response_data["selections_count"], 2)
        self.assertEqual(response_data["updated_count"], 0)
        self.assertEqual(
            set(response_data["failed_subsection_ids"]), {"99999", "88888"}
        )
        self.assertIn("All comparison selections failed", response_data["message"])

    def test_post_with_invalid_json_returns_error(self):
        """Test that POST request with invalid JSON returns proper error"""
        response = self.client.post(
            self.url,
            data="invalid json data",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertFalse(response_data["success"])
        self.assertEqual(response_data["message"], "Invalid JSON data.")


class ContentGuideSubsectionEditViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            force_password_reset=False,
            group="bloom",
        )
        self.client.login(email="test@example.com", password="testpass123")

        self.guide = ContentGuide.objects.create(
            title="Test Guide", group="bloom", opdiv="CDC"
        )
        self.section = ContentGuideSection.objects.create(
            name="Main Section", content_guide=self.guide, order=1
        )
        self.subsection = ContentGuideSubsection.objects.create(
            section=self.section,
            name="Test Subsection",
            order=1,
            tag="h3",
            comparison_type="none",
        )

        self.url = reverse(
            "guides:subsection_edit",
            kwargs={
                "pk": self.guide.pk,
                "section_pk": self.section.pk,
                "subsection_pk": self.subsection.pk,
            },
        )

    def test_get_view_returns_200_and_shows_subsection(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.subsection.name)

    def test_post_updates_comparison_type_and_diff_strings(self):
        response = self.client.post(
            self.url,
            {
                "comparison_type": "diff_strings",
                "diff_string_1": "must include this",
                "diff_string_2": "and maybe this",
            },
        )
        self.assertRedirects(
            response, reverse("guides:guide_edit", kwargs={"pk": self.guide.pk})
        )

        self.subsection.refresh_from_db()
        self.assertEqual(self.subsection.comparison_type, "diff_strings")
        self.assertEqual(
            self.subsection.diff_strings, ["must include this", "and maybe this"]
        )

    def test_post_with_blank_strings_sets_empty_list(self):
        response = self.client.post(
            self.url,
            {
                "comparison_type": "diff_strings",
                "diff_string_1": "",
                "diff_string_2": "",
            },
        )
        self.subsection.refresh_from_db()
        self.assertEqual(self.subsection.diff_strings, [])


class ContentGuideDiffCSVViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            force_password_reset=False,
            group="bloom",
        )
        self.client.login(email="test@example.com", password="testpass123")

        self.guide = ContentGuide.objects.create(
            title="Older", group="bloom", opdiv="CDC"
        )
        self.new_nofo = Nofo.objects.create(title="Newer", group="bloom", opdiv="CDC")

    def parse_csv(self, content):
        """Helper to parse CSV bytes into a list of rows"""
        return list(csv.reader(io.StringIO(content.decode("utf-8"))))

    @patch("guides.views.compare_nofos")
    @patch("guides.views.annotate_side_by_side_diffs")
    def test_csv_no_merged_subsections_add(self, mock_annotate, mock_compare):
        subsection = MagicMock()
        subsection.status = "ADD"
        subsection.old_name = ""
        subsection.new_name = "Summary added"
        subsection.old_value = ""
        subsection.new_value = "New body"

        comparison = [{"subsections": [subsection]}]
        mock_compare.return_value = comparison
        mock_annotate.return_value = comparison

        url = reverse(
            "guides:guide_compare_result_csv", args=[self.guide.pk, self.new_nofo.pk]
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn(
            f"content_guide_diff_{self.guide.pk}_{self.new_nofo.pk}.csv",
            response["Content-Disposition"],
        )

        rows = self.parse_csv(response.content)
        self.assertEqual(
            rows[0], ["Status", "Subsection name", "Old value", "New value"]
        )
        self.assertEqual(rows[1], ["ADD", "Summary added", "", "New body"])

    @patch("guides.views.compare_nofos")
    @patch("guides.views.annotate_side_by_side_diffs")
    def test_csv_no_merged_subsections_delete(self, mock_annotate, mock_compare):
        subsection = MagicMock()
        subsection.status = "DELETE"
        subsection.old_name = "Summary deleted"
        subsection.new_name = ""
        subsection.old_value = "Old body"
        subsection.new_value = ""

        comparison = [{"subsections": [subsection]}]
        mock_compare.return_value = comparison
        mock_annotate.return_value = comparison

        url = reverse(
            "guides:guide_compare_result_csv", args=[self.guide.pk, self.new_nofo.pk]
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn(
            f"content_guide_diff_{self.guide.pk}_{self.new_nofo.pk}.csv",
            response["Content-Disposition"],
        )

        rows = self.parse_csv(response.content)
        self.assertEqual(
            rows[0], ["Status", "Subsection name", "Old value", "New value"]
        )
        self.assertEqual(rows[1], ["DELETE", "Summary deleted", "Old body", ""])

    @patch("guides.views.compare_nofos")
    @patch("guides.views.annotate_side_by_side_diffs")
    def test_csv_no_merged_subsections_update(self, mock_annotate, mock_compare):
        subsection = MagicMock()
        subsection.status = "UPDATE"
        subsection.old_name = "Summary"
        subsection.new_name = "Summary"
        subsection.old_value = "Old body"
        subsection.new_value = "New body"

        comparison = [{"subsections": [subsection]}]
        mock_compare.return_value = comparison
        mock_annotate.return_value = comparison

        url = reverse(
            "guides:guide_compare_result_csv", args=[self.guide.pk, self.new_nofo.pk]
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn(
            f"content_guide_diff_{self.guide.pk}_{self.new_nofo.pk}.csv",
            response["Content-Disposition"],
        )

        rows = self.parse_csv(response.content)
        self.assertEqual(
            rows[0], ["Status", "Subsection name", "Old value", "New value"]
        )
        self.assertEqual(rows[1], ["UPDATE", "Summary", "Old body", "New body"])

    @patch("guides.views.compare_nofos")
    @patch("guides.views.annotate_side_by_side_diffs")
    def test_csv_with_merged_subsections(self, mock_annotate, mock_compare):
        subsection = MagicMock()
        subsection.status = "UPDATE"
        subsection.old_name = "Summary"
        subsection.new_name = "Updated Summary"
        subsection.old_value = "Old body"
        subsection.new_value = "New body"

        comparison = [{"subsections": [subsection]}]
        mock_compare.return_value = comparison
        mock_annotate.return_value = comparison

        url = reverse(
            "guides:guide_compare_result_csv", args=[self.guide.pk, self.new_nofo.pk]
        )
        response = self.client.get(url)

        rows = self.parse_csv(response.content)
        self.assertEqual(
            rows[0],
            [
                "Status",
                "Subsection name",
                "Old value",
                "New subsection name",
                "New value",
            ],
        )
        self.assertEqual(
            rows[1], ["UPDATE", "Summary", "Old body", "Updated Summary", "New body"]
        )
