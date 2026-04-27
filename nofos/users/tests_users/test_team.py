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
        self.assertContains(response, "Regular User")
        self.assertContains(response, "ACF: Administration for Children and Families")

        # the current user is not visible in the "team" table
        self.assertNotContains(response, "Admin User")
        self.assertNotContains(response, "Bloomworks")

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


class BloomUserTeamCreateViewTests(TestCase):
    def setUp(self):
        self.url = reverse("users:user_team_create")

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

    def test_superuser_can_view_create_user_page(self):
        self.client.force_login(self.superuser)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add user")
        self.assertContains(response, "Email address")
        self.assertContains(response, "Full name")
        self.assertContains(response, "Group")
        self.assertContains(response, "Password")
        self.assertContains(response, "Is Superuser")

    def test_superuser_can_create_regular_user(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            self.url,
            {
                "email": "new@example.com",
                "full_name": "New User",
                "group": "acf",
                "password1": "testpass123",
                "password2": "testpass123",
            },
        )

        self.assertRedirects(response, reverse("users:user_team"))

        user = BloomUser.objects.get(email="new@example.com")
        self.assertEqual(user.full_name, "New User")
        self.assertEqual(user.group, "acf")
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)
        self.assertTrue(user.is_active)
        self.assertTrue(user.force_password_reset)
        self.assertIsNone(user.login_gov_user_id)
        self.assertTrue(user.check_password("testpass123"))

    def test_superuser_can_create_superuser_in_bloom_group(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            self.url,
            {
                "email": "new-admin@example.com",
                "full_name": "New Admin",
                "group": "bloom",
                "password1": "testpass123",
                "password2": "testpass123",
                "is_superuser": "on",
            },
        )

        self.assertRedirects(response, reverse("users:user_team"))

        user = BloomUser.objects.get(email="new-admin@example.com")
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_active)
        self.assertTrue(user.force_password_reset)

    def test_cannot_create_superuser_outside_bloom_group(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            self.url,
            {
                "email": "bad-admin@example.com",
                "full_name": "Bad Admin",
                "group": "acf",
                "password1": "testpass123",
                "password2": "testpass123",
                "is_superuser": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Only users in the &#x27;bloom&#x27; group can be staff or superusers.",
        )
        self.assertFalse(
            BloomUser.objects.filter(email="bad-admin@example.com").exists()
        )


class BloomUserTeamDeleteViewTests(TestCase):
    def setUp(self):
        self.superuser = BloomUser.objects.create_user(
            email="admin@example.com",
            password="testpass123",
            full_name="Admin User",
            group="bloom",
            is_staff=True,
            is_superuser=True,
            force_password_reset=False,
        )

        self.other_superuser = BloomUser.objects.create_user(
            email="other-admin@example.com",
            password="testpass123",
            full_name="Other Admin",
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

        self.url = reverse("users:user_team_delete", args=[self.regular_user.pk])

    def test_anonymous_user_gets_403(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_non_superuser_gets_403(self):
        self.client.force_login(self.regular_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)

    def test_superuser_can_view_delete_confirmation_page(self):
        self.client.force_login(self.superuser)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Delete user")
        self.assertContains(response, "user@example.com")
        self.assertContains(response, "Yes, delete user")
        self.assertContains(
            response,
            "Never mind, I don’t want to delete this user",
        )

    def test_superuser_can_delete_user(self):
        self.client.force_login(self.superuser)

        response = self.client.post(self.url)

        self.assertRedirects(response, reverse("users:user_team"))
        self.assertFalse(BloomUser.objects.filter(email="user@example.com").exists())

    def test_superuser_cannot_delete_self(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse("users:user_team_delete", args=[self.superuser.pk])
        )

        self.assertRedirects(response, reverse("users:user_team"))
        self.assertTrue(BloomUser.objects.filter(email="admin@example.com").exists())

    def test_superuser_cannot_delete_last_superuser(self):
        self.other_superuser.delete()
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse("users:user_team_delete", args=[self.superuser.pk])
        )

        self.assertRedirects(response, reverse("users:user_team"))
        self.assertTrue(BloomUser.objects.filter(email="admin@example.com").exists())
