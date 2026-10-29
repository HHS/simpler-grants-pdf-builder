from unittest.mock import patch

from constance.test import override_config
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from users.models import BloomUser

from nofos.models import WordComparison
from nofos.word_comparisons import WordResultsForm

REPORT = {
    "profile": "word",
    "version": "synthetic-1",
    "metrics": {"passive_sentence_percentage": {"value": 3.8}},
    "scope": {"complete_sentence_count": 80, "passive_sentence_count": 3},
    "warnings": ["Synthetic conversion warning"],
}


@override_config(
    HHS_NOFO_WORD_COMPARISONS_ENABLED=True,
    HHS_NOFO_AUTHENTICATED_PDF_METRICS_PILOT_ENABLED=True,
)
class ComparisonTests(TestCase):
    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="reviewer@example.test",
            group="bloom",
            password="test",
            force_password_reset=False,
        )
        for codename in (
            "manage_word_comparisons",
            "use_pdf_readability_pilot",
            "view_builder_metrics",
        ):
            self.user.user_permissions.add(Permission.objects.get(codename=codename))
        self.client.force_login(self.user)

    def stage(self):
        before = WordComparison.objects.count()
        with patch("bloom_nofos.views.analyze_uploaded_pdf", return_value=REPORT):
            response = self.client.post(
                reverse("nofos:authenticated_pdf_readability"),
                {"pdf": SimpleUploadedFile("Synthetic.docx", b"synthetic")},
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Save for Word comparison")
        self.assertEqual(WordComparison.objects.count(), before)
        return response.context["comparison_run"]

    def save(self, token):
        return self.client.post(reverse("nofos:word_comparison_save"), {"run": token})

    def test_exact_run_idempotency_and_history(self):
        token = self.stage()
        response = self.save(token)
        self.assertEqual(response.status_code, 302)
        self.save(token)
        self.assertEqual(WordComparison.objects.count(), 1)
        record = WordComparison.objects.get()
        self.assertEqual(record.checker["scope"]["complete_sentence_count"], 80)
        self.assertEqual(len(record.fingerprint), 64)
        self.assertIsNone(record.difference)
        self.assertEqual(record.status, "Awaiting Word results")
        data = {
            "passive": 3.3,
            "sentence_count": 90,
            "measured_on": "2026-10-29",
            "same_copy": "on",
            "notes": "Synthetic review",
        }
        self.client.post(response.url, data)
        record.refresh_from_db()
        self.assertAlmostEqual(record.difference, 0.5)
        self.assertEqual(record.status, "Ready for review")
        self.client.post(response.url, {**data, "passive": 4.5, "reviewed": "on"})
        self.assertEqual(record.revisions.count(), 2)
        self.assertAlmostEqual(record.difference, -0.7)
        self.assertEqual(record.status, "Reviewed")
        self.assertEqual(record.passive, 3.8)
        self.assertContains(self.client.get(response.url), "90")
        self.save(self.stage())
        self.assertEqual(WordComparison.objects.count(), 2)

    def test_owner_tampering_and_permissions(self):
        token = self.stage()
        self.assertEqual(self.save(token + "tamper").status_code, 404)
        other = BloomUser.objects.create_user(
            email="other@example.test",
            password=None,
            group="bloom",
            force_password_reset=False,
        )
        other.user_permissions.add(
            Permission.objects.get(codename="manage_word_comparisons")
        )
        self.client.force_login(other)
        self.assertEqual(self.save(token).status_code, 404)
        self.client.logout()
        self.assertEqual(self.save(token).status_code, 302)
        self.client.force_login(self.user)
        self.user.user_permissions.remove(
            Permission.objects.get(codename="manage_word_comparisons")
        )
        self.assertEqual(self.save(token).status_code, 403)

    def test_disable_and_redirect(self):
        token = self.stage()
        with override_config(HHS_NOFO_WORD_COMPARISONS_ENABLED=False):
            self.assertEqual(self.save(token).status_code, 404)
            self.assertEqual(
                self.client.get(reverse("nofos:word_comparisons")).status_code, 404
            )
        response = self.client.get(
            "/nofos/metrics/readability-pilot?source=authenticated&page=2"
        )
        self.assertRedirects(
            response,
            reverse("nofos:builder_metrics_readability_pilot")
            + "?source=authenticated&page=2",
            status_code=301,
            fetch_redirect_response=False,
        )

    def test_list_version_details_and_read_only(self):
        self.save(self.stage())
        url = reverse("nofos:word_comparisons")
        self.assertContains(self.client.get(url), "Synthetic.docx")
        response = self.client.get(url)
        self.assertContains(response, "Saved results, newest first")
        self.assertContains(response, "Calculation version")
        self.assertContains(response, "Metrics vsynthetic-1")
        self.assertContains(response, "View details")
        self.assertNotContains(response, "Apply filters")
        self.assertNotContains(response, "<form")
        self.assertNotContains(response, 'aria-label="Comparison pages"')
        record = WordComparison.objects.get()
        self.user.user_permissions.remove(
            Permission.objects.get(codename="manage_word_comparisons")
        )
        self.assertEqual(
            self.client.post(
                reverse("nofos:word_comparison_detail", args=[record.pk]), {}
            ).status_code,
            403,
        )

    def test_validation_missing_zero_and_denominators(self):
        self.assertTrue(WordResultsForm({}).is_valid())
        self.assertFalse(WordResultsForm({"passive": 101}).is_valid())
        self.assertFalse(WordResultsForm({"passive": 0}).is_valid())
        self.assertFalse(WordResultsForm({"reviewed": "on"}).is_valid())
        self.assertTrue(
            WordResultsForm(
                {
                    "passive": 0,
                    "sentence_count": 10,
                    "measured_on": "2026-10-29",
                    "same_copy": "on",
                }
            ).is_valid()
        )

    def test_expiration_csrf_and_audit_exclusion(self):
        import time

        from django.test import Client
        from easyaudit.signals.model_signals import should_audit

        token = self.stage()
        with patch("django.core.signing.time.time", return_value=time.time() + 1801):
            self.assertEqual(self.save(token).status_code, 404)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.assertEqual(
            csrf_client.post(
                reverse("nofos:word_comparison_save"), {"run": token}
            ).status_code,
            403,
        )
        self.assertFalse(should_audit(WordComparison()))

    def test_unavailable_and_newest_first_pagination(self):
        from django.utils import timezone

        from nofos.models import WordComparisonRevision

        self.save(self.stage())
        for i in range(26):
            record = WordComparison.objects.create(
                filename=f"Synthetic {i}.docx",
                owner=self.user,
                fingerprint="b" * 64,
                analyzed_at=timezone.now(),
                version="other-version",
                checker=REPORT,
                passive=None if i == 25 else i,
            )
            WordComparisonRevision.objects.create(
                comparison=record,
                reviewer=self.user,
                passive=0,
                sentence_count=20,
                same_copy=True,
                measured_on="2026-10-29",
            )
        response = self.client.get(reverse("nofos:word_comparisons"))
        self.assertEqual(response.context["page"].paginator.count, 27)
        self.assertEqual(response.context["page"][0].filename, "Synthetic 25.docx")
        self.assertIsNone(response.context["page"][0].difference)
        self.assertContains(response, "?page=2")
        response = self.client.get(reverse("nofos:word_comparisons"), {"page": 2})
        self.assertEqual(response.context["page"][-1].filename, "Synthetic.docx")

    def test_admin_comparison_toggle_is_independent(self):
        from django.contrib.auth.models import Permission
        from users.forms import BloomUserChangeForm

        form = BloomUserChangeForm(instance=self.user)
        self.assertTrue(form.initial["can_manage_word_comparisons"])
        form.cleaned_data = {
            "can_view_metrics": False,
            "can_use_pdf_readability_pilot": False,
            "can_manage_word_comparisons": False,
        }
        form._save_m2m()
        self.assertFalse(
            self.user.user_permissions.filter(
                codename="manage_word_comparisons"
            ).exists()
        )
        form.cleaned_data["can_manage_word_comparisons"] = True
        form._save_m2m()
        self.assertTrue(
            self.user.user_permissions.filter(
                codename="manage_word_comparisons"
            ).exists()
        )
