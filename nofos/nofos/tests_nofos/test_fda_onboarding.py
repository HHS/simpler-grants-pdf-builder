from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.models import Nofo
from nofos.tests_nofos.test_introductory_page import introductory_docx


class FDAOnboardingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        for group in ("bloom", "fda", "cdc"):
            user = BloomUser.objects.create_user(
                email=f"{group}@example.test",
                password="Synthetic-test-password-27!",
                group=group,
                is_superuser=group == "bloom",
                is_staff=group == "bloom",
                force_password_reset=False,
            )
            setattr(cls, group, user)

    def test_superuser_can_create_fda_user_who_can_sign_in(self):
        self.client.force_login(self.bloom)
        password = "Another-synthetic-password-27!"
        email = "fda-new@example.test"
        response = self.client.post(
            reverse("users:user_team_create"),
            {
                "email": email,
                "full_name": "Synthetic FDA editor",
                "group": "fda",
                "password1": password,
                "password2": password,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(BloomUser.objects.get(email=email).group, "fda")
        self.client.logout()
        self.assertTrue(self.client.login(username=email, password=password))

    def test_word_import_uses_editor_group_and_preserves_access_boundaries(self):
        self.client.force_login(self.fda)
        response = self.client.post(
            reverse("nofos:nofo_import"),
            {
                "nofo-import": SimpleUploadedFile(
                    "synthetic.docx",
                    introductory_docx(number="RFA-FD-26-001"),
                    content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        self.assertEqual(response.status_code, 302)
        imported = Nofo.objects.get()
        self.assertEqual(imported.group, "fda")
        separate = Nofo.objects.create(group="cdc", title="CDC notice", opdiv="CDC")
        index = reverse("nofos:nofo_index")
        imported_view = reverse("nofos:nofo_view", args=[imported.pk])
        separate_view = reverse("nofos:nofo_view", args=[separate.pk])
        peer = BloomUser.objects.create_user(
            email="fda-peer@example.test",
            password=None,
            group="fda",
            force_password_reset=False,
        )

        self.client.force_login(peer)
        self.assertQuerySetEqual(
            self.client.get(index).context["nofo_list"], [imported]
        )
        self.assertEqual(self.client.get(imported_view).status_code, 200)
        self.assertEqual(self.client.get(separate_view).status_code, 403)

        self.client.force_login(self.cdc)
        self.assertNotIn(imported, self.client.get(index).context["nofo_list"])
        self.assertEqual(self.client.get(imported_view).status_code, 403)

        self.client.force_login(self.bloom)
        self.assertEqual(self.client.get(imported_view).status_code, 200)
