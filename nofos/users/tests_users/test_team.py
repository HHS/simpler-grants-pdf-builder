from django.test import TestCase
from django.urls import reverse
from users.models import BloomUser


class BloomTeamViewTests(TestCase):
    def setUp(self):
        self.url = reverse("users:user_team")

        self.superuser = BloomUser.objects.create_user(
            email="admin@example.com",
            password="testpass123",
            full_name="Admin User",
            group="bloom",
            is_staff=True,
            is_superuser=True,
            force_password_reset=False,
        )

        self.regular_user = BloomUser.objects.create_user(
            email="user@example.com",
            password="testpass123",
            full_name="Regular User",
            group="acf",
            force_password_reset=False,
        )

    def test_anonymous_user_gets_403(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_non_superuser_gets_403(self):
        self.client.force_login(self.regular_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_superuser_can_view_team_page(self):
        self.client.force_login(self.superuser)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "All users")
        self.assertContains(response, "admin@example.com")
        self.assertContains(response, "user@example.com")
        self.assertContains(response, "Admin User")
        self.assertContains(response, "Regular User")
        self.assertContains(response, "ACF: Administration for Children and Families")
        self.assertContains(response, "Bloomworks")

    def test_team_page_uses_uswds_sortable_columns_for_email_and_group(self):
        self.client.force_login(self.superuser)

        response = self.client.get(self.url)

        self.assertContains(
            response,
            '<th data-sortable scope="col" role="columnheader">Email address</th>',
            html=True,
        )
        self.assertContains(
            response,
            '<th data-sortable scope="col" role="columnheader">Group</th>',
            html=True,
        )
        self.assertNotContains(response, '<th data-sortable scope="col">Name</th>')
        self.assertNotContains(response, '<th data-sortable scope="col">Superuser</th>')
