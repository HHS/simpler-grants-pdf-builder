from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse
from users.forms import BloomUserChangeForm
from users.models import BloomUser


class MetricsAdminTests(TestCase):
    def setUp(self):
        self.admin = BloomUser.objects.create_superuser(
            email="admin@example.gov", password="test"
        )
        self.user = BloomUser.objects.create_user(
            email="viewer@example.gov", password=None, group="cdc"
        )
        self.client.force_login(self.admin)
        self.url = reverse("admin:users_bloomuser_change", args=[self.user.pk])
        self.data = {
            "email": self.user.email,
            "full_name": "Viewer",
            "group": "cdc",
            "is_active": "on",
        }

    def test_admin_grants_and_revokes_access_preserving_other_groups(self):
        unrelated = Group.objects.create(name="Other role")
        self.user.groups.add(unrelated)
        response = self.client.post(self.url, {**self.data, "can_view_metrics": "on"})
        self.assertEqual(response.status_code, 302)
        user = BloomUser.objects.get(pk=self.user.pk)
        self.assertTrue(user.has_perm("nofos.view_builder_metrics"))
        self.assertTrue(BloomUserChangeForm(instance=user).initial["can_view_metrics"])
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 302)
        user = BloomUser.objects.get(pk=self.user.pk)
        self.assertFalse(user.has_perm("nofos.view_builder_metrics"))
        self.assertTrue(user.groups.filter(pk=unrelated.pk).exists())
        self.assertEqual(user.group, "cdc")

    def test_create_user_with_metrics_access(self):
        response = self.client.post(
            reverse("admin:users_bloomuser_add"),
            {
                **self.data,
                "email": "new@example.gov",
                "can_view_metrics": "on",
                "password1": "New-complex-password-529!",
                "password2": "New-complex-password-529!",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            BloomUser.objects.get(email="new@example.gov").has_perm(
                "nofos.view_builder_metrics"
            )
        )

    def test_separate_permission_is_explained_and_preserved(self):
        permission = Permission.objects.get(
            content_type__app_label="nofos", codename="view_builder_metrics"
        )
        self.user.user_permissions.add(permission)
        response = self.client.get(self.url)
        self.assertContains(
            response, "Unchecking this box will not remove that separate access."
        )
        self.client.post(self.url, self.data)
        self.assertTrue(
            BloomUser.objects.get(pk=self.user.pk).has_perm(
                "nofos.view_builder_metrics"
            )
        )

    def test_non_admin_cannot_grant_access(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {**self.data, "can_view_metrics": "on"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            BloomUser.objects.get(pk=self.user.pk).has_perm(
                "nofos.view_builder_metrics"
            )
        )
