from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from guides.models import ContentGuide

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

    def test_view_returns_200_for_authorized_user(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_post_valid_data_updates_title(self):
        response = self.client.post(self.url, {"title": "Updated Title"})
        self.guide.refresh_from_db()
        self.assertEqual(self.guide.title, "Updated Title")
        self.assertRedirects(response, reverse("guides:guide_index"))

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
