from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from guides.models import ContentGuide

User = get_user_model()


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
