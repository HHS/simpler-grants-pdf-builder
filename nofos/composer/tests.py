from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import ContentGuide

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
