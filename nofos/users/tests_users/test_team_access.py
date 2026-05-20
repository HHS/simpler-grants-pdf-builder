from django.test import TestCase
from django.urls import reverse
from users.models import BloomUser


class BloomUserTeamOpdivAdminAccessTests(TestCase):
    def setUp(self):
        self.hrsa_user = BloomUser.objects.create_user(
            email="hrsa-user@example.com",
            password="testpass123",
            full_name="HRSA User",
            group="hrsa",
            force_password_reset=False,
        )

        self.hrsa_opdiv_admin = BloomUser.objects.create_user(
            email="hrsa-admin@example.com",
            password="testpass123",
            full_name="HRSA Admin",
            group="hrsa",
            is_opdiv_admin=True,
            force_password_reset=False,
        )

        self.acf_user = BloomUser.objects.create_user(
            email="acf-user@example.com",
            password="testpass123",
            full_name="ACF User",
            group="acf",
            force_password_reset=False,
        )

        self.superuser = BloomUser.objects.create_user(
            email="superuser@example.com",
            password="testpass123",
            full_name="Super User",
            group="bloom",
            is_superuser=True,
            force_password_reset=False,
        )

    def assert_accessible(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def assert_not_accessible(self, url):
        response = self.client.get(url)
        self.assertIn(response.status_code, [403, 404])

    def regular_team_urls(self, user):
        return [
            reverse("users:user_team_detail", args=[user.pk]),
            reverse("users:user_team_delete", args=[user.pk]),
            reverse("users:user_team_edit_name", args=[user.pk]),
            reverse("users:user_team_edit_opdiv_admin", args=[user.pk]),
            reverse("users:user_team_reset_password", args=[user.pk]),
        ]

    def admin_only_team_urls(self, user):
        return [
            reverse("users:user_team_edit_group", args=[user.pk]),
            reverse("users:user_team_edit_superuser", args=[user.pk]),
        ]

    def all_object_team_urls(self, user):
        return self.regular_team_urls(user) + self.admin_only_team_urls(user)

    def test_regular_user_cannot_access_team_list_or_create_page(self):
        self.client.force_login(self.hrsa_user)

        urls = [
            reverse("users:user_team"),
            reverse("users:user_team_create"),
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assert_not_accessible(url)

    def test_opdiv_admin_can_access_team_list_and_create_page(self):
        self.client.force_login(self.hrsa_opdiv_admin)

        urls = [
            reverse("users:user_team"),
            reverse("users:user_team_create"),
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assert_accessible(url)

    def test_opdiv_admin_can_access_allowed_pages_for_same_group_user(self):
        self.client.force_login(self.hrsa_opdiv_admin)

        for url in self.regular_team_urls(self.hrsa_user):
            with self.subTest(url=url):
                self.assert_accessible(url)

    # opdiv admins shouldn't ever be able to edit "group" or "superuser" status
    def test_opdiv_admin_cannot_access_superuser_only_pages_for_same_group_user(self):
        self.client.force_login(self.hrsa_opdiv_admin)

        for url in self.admin_only_team_urls(self.hrsa_user):
            with self.subTest(url=url):
                self.assert_not_accessible(url)

    # opdiv admins shouldn't ever be able to see other groups' users
    def test_opdiv_admin_cannot_access_pages_for_other_group_user(self):
        self.client.force_login(self.hrsa_opdiv_admin)

        for url in self.all_object_team_urls(self.acf_user):
            with self.subTest(url=url):
                self.assert_not_accessible(url)

    # opdiv admins shouldn't ever be able to see superusers
    def test_opdiv_admin_cannot_access_pages_for_superuser(self):
        self.client.force_login(self.hrsa_opdiv_admin)

        for url in self.all_object_team_urls(self.superuser):
            with self.subTest(url=url):
                self.assert_not_accessible(url)

    def test_opdiv_admin_cannot_access_pages_for_themselves(self):
        self.client.force_login(self.hrsa_opdiv_admin)

        for url in self.all_object_team_urls(self.hrsa_opdiv_admin):
            with self.subTest(url=url):
                self.assert_not_accessible(url)
