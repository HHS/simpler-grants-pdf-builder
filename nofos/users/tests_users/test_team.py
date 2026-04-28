from django.test import TestCase
from django.urls import reverse
from users.models import BloomUser


class BloomUserTeamBaseTests(TestCase):
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

        self.bloom_user = BloomUser.objects.create_user(
            email="bloom-user@example.com",
            password="testpass123",
            full_name="Bloom User",
            group="bloom",
            force_password_reset=False,
        )

        self.regular_user = BloomUser.objects.create_user(
            email="user@example.com",
            password="testpass123",
            full_name="Regular User",
            group="acf",
            force_password_reset=False,
        )

    def assert_superuser_required(self, url):
        self.client.logout()

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        self.client.force_login(self.regular_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        self.client.logout()


class BloomTeamViewTests(BloomUserTeamBaseTests):
    def setUp(self):
        super().setUp()
        self.url = reverse("users:user_team")

    def test_superuser_required(self):
        self.assert_superuser_required(self.url)

    def test_superuser_can_view_team_page(self):
        self.client.force_login(self.superuser)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "All users")
        self.assertContains(response, "user@example.com")
        self.assertContains(response, "Regular User")
        self.assertContains(response, "ACF: Administration for Children and Families")

        # the current user is not visible in the "team" table
        self.assertNotContains(response, 'data-sort-value="admin@example.com"')
        self.assertNotContains(response, "Admin User")

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


class BloomUserTeamCreateViewTests(BloomUserTeamBaseTests):
    def setUp(self):
        super().setUp()
        self.url = reverse("users:user_team_create")

    def test_superuser_required(self):
        self.assert_superuser_required(self.url)

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


class BloomUserTeamDeleteViewTests(BloomUserTeamBaseTests):
    def setUp(self):
        super().setUp()
        self.url = reverse("users:user_team_delete", args=[self.regular_user.pk])

    def test_superuser_required(self):
        self.assert_superuser_required(self.url)

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


class BloomUserTeamDetailViewTests(BloomUserTeamBaseTests):
    def test_superuser_required(self):
        url = reverse("users:user_team_detail", args=[self.regular_user.pk])

        self.assert_superuser_required(url)

    def test_superuser_can_view_user_detail_page(self):
        self.client.force_login(self.superuser)

        response = self.client.get(
            reverse("users:user_team_detail", args=[self.regular_user.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "user@example.com")
        self.assertContains(response, "Regular User")
        self.assertContains(response, "ACF: Administration for Children and Families")
        self.assertContains(response, "Change group")
        self.assertContains(response, "Reset password")

    def test_superuser_row_only_shows_for_bloom_users(self):
        self.client.force_login(self.superuser)

        bloom_response = self.client.get(
            reverse("users:user_team_detail", args=[self.bloom_user.pk])
        )
        regular_response = self.client.get(
            reverse("users:user_team_detail", args=[self.regular_user.pk])
        )

        self.assertContains(bloom_response, "Is Superuser")
        self.assertContains(bloom_response, "Change Superuser status")
        self.assertNotContains(regular_response, "Is Superuser")
        self.assertNotContains(regular_response, "Change Superuser status")


class BloomUserTeamNameEditViewTests(BloomUserTeamBaseTests):
    def test_superuser_required(self):
        url = reverse("users:user_team_edit_name", args=[self.regular_user.pk])

        self.assert_superuser_required(url)

    def test_superuser_can_view_name_edit_page(self):
        self.client.force_login(self.superuser)

        response = self.client.get(
            reverse("users:user_team_edit_name", args=[self.regular_user.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Change user name")
        self.assertContains(response, "Full name")

    def test_superuser_can_change_user_name(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse("users:user_team_edit_name", args=[self.regular_user.pk]),
            {
                "full_name": "Updated User",
            },
        )

        self.assertRedirects(
            response,
            reverse("users:user_team_detail", args=[self.regular_user.pk]),
        )

        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.full_name, "Updated User")


class BloomUserTeamGroupEditViewTests(BloomUserTeamBaseTests):
    def test_superuser_required(self):
        url = reverse("users:user_team_edit_group", args=[self.regular_user.pk])

        self.assert_superuser_required(url)

    def test_superuser_can_view_group_edit_page(self):
        self.client.force_login(self.superuser)

        response = self.client.get(
            reverse("users:user_team_edit_group", args=[self.regular_user.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Change user group")
        self.assertContains(response, "Group")

    def test_superuser_can_change_regular_user_group(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse("users:user_team_edit_group", args=[self.regular_user.pk]),
            {
                "group": "cdc",
            },
        )

        self.assertRedirects(
            response,
            reverse("users:user_team_detail", args=[self.regular_user.pk]),
        )

        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.group, "cdc")

    def test_cannot_change_superuser_to_non_bloom_group(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse("users:user_team_edit_group", args=[self.other_superuser.pk]),
            {
                "group": "acf",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Remove Superuser status before changing this user to a non-Bloom group.",
        )

        self.other_superuser.refresh_from_db()
        self.assertEqual(self.other_superuser.group, "bloom")
        self.assertTrue(self.other_superuser.is_superuser)
        self.assertTrue(self.other_superuser.is_staff)


class BloomUserTeamSuperuserEditViewTests(BloomUserTeamBaseTests):
    def test_superuser_required(self):
        url = reverse("users:user_team_edit_superuser", args=[self.bloom_user.pk])

        self.assert_superuser_required(url)

    def test_superuser_can_view_superuser_edit_page_for_bloom_user(self):
        self.client.force_login(self.superuser)

        response = self.client.get(
            reverse("users:user_team_edit_superuser", args=[self.bloom_user.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Change Superuser status")
        self.assertContains(response, "Is Superuser")

    def test_non_bloom_user_cannot_access_superuser_edit_page(self):
        self.client.force_login(self.superuser)

        response = self.client.get(
            reverse("users:user_team_edit_superuser", args=[self.regular_user.pk])
        )

        self.assertRedirects(
            response,
            reverse("users:user_team_detail", args=[self.regular_user.pk]),
        )

    def test_superuser_can_make_bloom_user_a_superuser(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse("users:user_team_edit_superuser", args=[self.bloom_user.pk]),
            {
                "is_superuser": "on",
            },
        )

        self.assertRedirects(
            response,
            reverse("users:user_team_detail", args=[self.bloom_user.pk]),
        )

        self.bloom_user.refresh_from_db()
        self.assertTrue(self.bloom_user.is_superuser)
        self.assertTrue(self.bloom_user.is_staff)

    def test_superuser_can_remove_superuser_status_from_another_user(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse("users:user_team_edit_superuser", args=[self.other_superuser.pk]),
            {},
        )

        self.assertRedirects(
            response,
            reverse("users:user_team_detail", args=[self.other_superuser.pk]),
        )

        self.other_superuser.refresh_from_db()
        self.assertFalse(self.other_superuser.is_superuser)
        self.assertFalse(self.other_superuser.is_staff)

    def test_superuser_cannot_remove_superuser_status_from_self(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse("users:user_team_edit_superuser", args=[self.superuser.pk]),
            {},
        )

        self.assertRedirects(
            response,
            reverse("users:user_team_detail", args=[self.superuser.pk]),
        )

        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.is_superuser)
        self.assertTrue(self.superuser.is_staff)


class BloomUserTeamPasswordResetViewTests(BloomUserTeamBaseTests):
    def test_superuser_required(self):
        url = reverse("users:user_team_reset_password", args=[self.bloom_user.pk])

        self.assert_superuser_required(url)

    def test_superuser_can_view_password_reset_page(self):
        self.client.force_login(self.superuser)

        response = self.client.get(
            reverse("users:user_team_reset_password", args=[self.regular_user.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reset user password")
        self.assertContains(response, "user@example.com")

    def test_superuser_can_reset_another_users_password(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse("users:user_team_reset_password", args=[self.regular_user.pk]),
            {
                "new_password1": "a-very-good-password-12345",
                "new_password2": "a-very-good-password-12345",
            },
        )

        self.assertRedirects(
            response,
            reverse("users:user_team_detail", args=[self.regular_user.pk]),
        )

        self.regular_user.refresh_from_db()
        self.assertTrue(self.regular_user.check_password("a-very-good-password-12345"))
        self.assertTrue(self.regular_user.force_password_reset)

    def test_superuser_cannot_reset_own_password_from_team_page(self):
        self.client.force_login(self.superuser)

        response = self.client.get(
            reverse("users:user_team_reset_password", args=[self.superuser.pk])
        )

        self.assertRedirects(
            response,
            reverse("users:user_team_detail", args=[self.superuser.pk]),
        )
