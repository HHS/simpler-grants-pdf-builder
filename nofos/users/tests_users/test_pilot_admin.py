from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from users.forms import BloomUserChangeForm, BloomUserCreationForm
from users.models import BloomUser


class RetiredPilotAccessAdminTests(TestCase):
    """Readability Checker access no longer has a per-user permission (#1367)."""

    def setUp(self):
        self.admin = BloomUser.objects.create_superuser(
            email="admin@example.gov", password="test"
        )
        self.user = BloomUser.objects.create_user(
            email="viewer@example.gov", password=None, group="cdc"
        )
        self.client.force_login(self.admin)
        self.url = reverse("admin:users_bloomuser_change", args=[self.user.pk])

    def test_forms_and_admin_no_longer_offer_pilot_checkbox(self):
        for form in (BloomUserChangeForm(instance=self.user), BloomUserCreationForm()):
            self.assertNotIn("can_use_pdf_readability_pilot", form.fields)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Can use PDF readability pilot")
        self.assertContains(response, "Can save passive sentence comparisons")

    def test_submitting_old_field_grants_nothing(self):
        response = self.client.post(
            self.url,
            {
                "email": self.user.email,
                "full_name": "Viewer",
                "group": "cdc",
                "is_active": "on",
                "can_use_pdf_readability_pilot": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        user = BloomUser.objects.get(pk=self.user.pk)
        self.assertFalse(user.groups.exists())
        self.assertFalse(
            Permission.objects.filter(codename="use_pdf_readability_pilot").exists()
        )
