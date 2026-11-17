from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.models import Nofo, Section, Subsection
from nofos.tests_nofos.test_metadata_block_import import DOCX_CONTENT_TYPE, metadata_docx


class SamhsaBybContract(TestCase):
    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="pilot@example.com",
            password="synthetic-test",
            group="bloom",
            force_password_reset=False,
        )
        self.client.force_login(self.user)

    def upload(self, *, opdiv):
        return SimpleUploadedFile(
            "synthetic.docx",
            metadata_docx(opdiv=opdiv),
            content_type=DOCX_CONTENT_TYPE,
        )

    def test_new_word_import(self):
        for group, opdiv, expected in (
            ("samhsa", "HHS", "era"),
            ("bloom", "SAMHSA", "era"),
            ("bloom", "Substance Abuse and Mental Health Services Administration", "era"),
            ("bloom", "HHS", "full"),
        ):
            with self.subTest(group=group, opdiv=opdiv):
                self.user.group = group
                self.user.save(update_fields=["group"])
                existing = set(Nofo.objects.values_list("pk", flat=True))
                response = self.client.post(
                    reverse("nofos:nofo_import"),
                    {"nofo-import": self.upload(opdiv=opdiv)},
                )
                self.assertEqual(response.status_code, 302)
                nofo = Nofo.objects.exclude(pk__in=existing).get()
                self.assertEqual(nofo.before_you_begin, expected)

    def test_word_reimport(self):
        for group, opdiv, old_number, expected in (
            ("samhsa", "HHS", "TEST-1096", "era"),
            ("bloom", "SAMHSA", "OLD-1096", "era"),
            ("bloom", "HHS", "TEST-1096", "sole_source"),
        ):
            with self.subTest(group=group, opdiv=opdiv, old_number=old_number):
                nofo = Nofo.objects.create(
                    title="Synthetic saved draft",
                    number=old_number,
                    opdiv="HHS",
                    group=group,
                    status="draft",
                    before_you_begin="sole_source",
                )
                section = Section.objects.create(nofo=nofo, name="Original", order=1)
                Subsection.objects.create(section=section, name="", body="Old body", order=1)
                response = self.client.post(
                    reverse("nofos:nofo_import_overwrite", kwargs={"pk": nofo.pk}),
                    {"nofo-import": self.upload(opdiv=opdiv)},
                )
                self.assertEqual(response.status_code, 302)
                if old_number != "TEST-1096":
                    confirm_url = reverse(
                        "nofos:nofo_import_confirm_overwrite", kwargs={"pk": nofo.pk}
                    )
                    self.assertRedirects(response, confirm_url, fetch_redirect_response=False)
                    nofo.refresh_from_db()
                    self.assertEqual(nofo.before_you_begin, "sole_source")
                    response = self.client.post(confirm_url)
                    self.assertEqual(response.status_code, 302)
                nofo.refresh_from_db()
                self.assertEqual(nofo.number, "TEST-1096")
                self.assertEqual(
                    Nofo.objects.get(successor=nofo).before_you_begin, "sole_source"
                )
                self.assertEqual(nofo.before_you_begin, expected)
