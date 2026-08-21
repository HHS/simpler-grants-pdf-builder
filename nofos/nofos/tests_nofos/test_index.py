from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class NofoIndexViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="index-test@example.com",
            password="testpass123",
            group="bloom",
            force_password_reset=False,
        )
        self.client.login(email="index-test@example.com", password="testpass123")

    def test_import_action_appears_at_top_and_bottom_of_page(self):
        response = self.client.get(reverse("nofos:nofo_index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'href="{reverse("nofos:nofo_import")}"',
            count=2,
        )
        self.assertContains(response, "Import NOFO", count=2)
