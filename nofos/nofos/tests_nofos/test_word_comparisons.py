from datetime import timedelta
from unittest.mock import patch

from constance.test import override_config
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from users.models import BloomUser

from nofos.models import WordComparison
from nofos.word_comparisons import WordResultsForm, difference_trend

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
        count = WordComparison.objects.count()
        with patch("bloom_nofos.views.analyze_uploaded_pdf", return_value=REPORT):
            response = self.client.post(
                reverse("nofos:authenticated_pdf_readability"),
                {"pdf": SimpleUploadedFile("Synthetic.docx", b"synthetic")},
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "Microsoft Word for Windows passive sentences (%)"
        )
        self.assertContains(response, 'type="number"')
        self.assertEqual(WordComparison.objects.count(), count)
        return response.context["comparison_run"]

    def save(self, token, passive=3.3):
        return self.client.post(
            reverse("nofos:word_comparison_save"), {"run": token, "passive": passive}
        )

    def test_inline_save_exact_run_idempotent_and_distinct(self):
        token = self.stage()
        response = self.save(token)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Comparison saved")
        self.assertTemplateUsed(response, "includes/alerts.html")
        self.assertNotContains(response, "usa-alert--slim")
        self.assertContains(response, "usa-alert--fixed")
        self.assertContains(response, '<h4 class="usa-alert__heading')
        self.assertContains(response, "Readability report")
        self.assertContains(response, "View passive sentence comparisons")
        self.assertNotContains(response, 'name="passive"')
        self.assertNotContains(response, "sentence count")
        self.save(token, passive=9)
        self.assertEqual(WordComparison.objects.count(), 1)
        record = WordComparison.objects.get()
        self.assertAlmostEqual(record.difference, 0.5)
        self.assertEqual(record.word_passive, 3.3)
        self.assertEqual(record.passive, 3.8)
        self.assertEqual(record.owner, self.user)
        self.assertEqual(len(record.fingerprint), 64)
        self.assertEqual(record.checker["scope"]["complete_sentence_count"], 80)
        self.save(self.stage())
        self.assertEqual(WordComparison.objects.count(), 2)

    def test_invalid_preserves_report_and_does_not_save(self):
        token = self.stage()
        for passive in ("", -1, 101, "nan", "inf", "not a number"):
            response = self.save(token, passive)
            self.assertEqual(response.status_code, 400)
            self.assertContains(response, "Readability report", status_code=400)
            self.assertEqual(response.context["comparison_run"], token)
            self.assertTemplateUsed(response, "includes/_text_input.html")
            self.assertContains(response, 'id="passive--error"', status_code=400)
            self.assertContains(response, 'aria-invalid="true"', status_code=400)
            self.assertContains(response, "comparison-save-response", status_code=400)
        self.assertFalse(WordComparison.objects.exists())
        self.assertTrue(WordResultsForm({"passive": 0}).is_valid())
        response = self.save(token, 0)
        self.assertEqual(response.status_code, 200)

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

    def test_disable_and_legacy_redirect(self):
        token = self.stage()
        from bs4 import BeautifulSoup

        usage = self.client.get(reverse("nofos:builder_metrics_readability_pilot"))
        nav = BeautifulSoup(usage.content, "html.parser").select_one(
            "nav.metrics-other-pages"
        )
        self.assertEqual(len(nav.find_all("a")), 1)
        self.assertEqual(nav.a.get_text(strip=True), "Passive sentence comparisons")
        self.assertEqual(nav.a["href"], reverse("nofos:word_comparisons"))
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

    def test_expiration_csrf_and_audit_exclusion(self):
        import time

        from easyaudit.signals.model_signals import should_audit

        token = self.stage()
        with patch("django.core.signing.time.time", return_value=time.time() + 1801):
            self.assertEqual(self.save(token).status_code, 404)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(
            client.post(
                reverse("nofos:word_comparison_save"),
                {"run": token, "passive": 3},
                HTTP_ACCEPT="application/json",
            ).status_code,
            403,
        )
        self.assertFalse(should_audit(WordComparison()))

    def test_list_version_and_newest_first_pagination(self):
        for i in range(27):
            WordComparison.objects.create(
                filename=f"Synthetic {i}.docx",
                owner=self.user,
                fingerprint="a" * 64,
                analyzed_at=timezone.now(),
                version="synthetic-1",
                checker=REPORT,
                passive=i,
                word_passive=2,
            )
        response = self.client.get(reverse("nofos:word_comparisons"))
        self.assertEqual(response.context["page"].paginator.count, 27)
        self.assertEqual(response.context["page"][0].filename, "Synthetic 26.docx")
        self.assertContains(response, "Saved results, newest first")
        self.assertContains(response, "Metrics vsynthetic-1")
        self.assertContains(response, "View details")
        self.assertNotContains(response, "<form")
        self.assertNotContains(response, "Status</th>")
        self.assertEqual(len(response.context["trend"]["points"]), 27)
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(response.content, "html.parser")
        self.assertEqual(soup.h1.get_text(strip=True), "Passive sentence comparisons")
        back_link = soup.select_one(".back-link a")
        self.assertEqual(
            back_link.get_text(strip=True), "Back to Readability Checker usage"
        )
        self.assertEqual(
            back_link["href"], reverse("nofos:builder_metrics_readability_pilot")
        )
        self.assertNotContains(response, "Usage overview")
        chart_data = soup.select_one("details.metrics-data-details")
        self.assertIsNone(chart_data.find("table"))
        self.assertEqual(len(chart_data.find_all("dt")), 27)
        self.assertContains(response, "?page=2")
        self.user.user_permissions.remove(
            Permission.objects.get(codename="view_builder_metrics")
        )
        self.assertEqual(
            self.client.get(reverse("nofos:word_comparisons")).status_code, 403
        )

    def test_trend_signed_missing_zero_single_and_empty(self):
        self.assertEqual(difference_trend([]), {"points": []})
        records = []
        for i, passive in enumerate((None, 0, 3, 1)):
            record = WordComparison.objects.create(
                filename=f"Sample {i}",
                owner=self.user,
                fingerprint="b" * 64,
                analyzed_at=timezone.now(),
                version="synthetic",
                checker=REPORT,
                passive=passive,
                word_passive=1,
            )
            record.saved_at = timezone.now() + timedelta(days=i)
            records.append(record)
        trend = difference_trend(reversed(records))
        self.assertEqual([p["difference"] for p in trend["points"]], [-1, 2, 0])
        self.assertLess(trend["points"][0]["x"], trend["points"][1]["x"])
        self.assertGreater(trend["points"][0]["y"], trend["zero_y"])
        self.assertLess(trend["points"][1]["y"], trend["zero_y"])
        self.assertEqual(difference_trend([records[3]])["points"][0]["x"], 325)

    def test_save_permission_does_not_grant_metrics_visibility(self):
        self.user.user_permissions.remove(
            Permission.objects.get(codename="view_builder_metrics")
        )
        response = self.save(self.stage())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Comparison saved")
        self.assertNotContains(response, "View passive sentence comparisons")
        self.assertEqual(
            self.client.get(reverse("nofos:word_comparisons")).status_code, 403
        )

    def test_admin_toggle_remains_independent(self):
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

    def test_background_save_validation_idempotency_and_no_flash_leak(self):
        token = self.stage()
        url = reverse("nofos:word_comparison_save")
        invalid = self.client.post(
            url, {"run": token, "passive": 101}, HTTP_ACCEPT="application/json"
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("Make sure", invalid.json()["errors"]["passive"][0]["message"])
        self.assertFalse(WordComparison.objects.exists())
        response = self.client.post(
            url, {"run": token, "passive": 3.3}, HTTP_ACCEPT="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["saved"])
        self.assertIn("usa-alert--slim", response.json()["html"])
        self.assertNotIn("usa-alert--fixed", response.json()["html"])
        self.assertNotIn("<script", response.json()["html"])
        self.assertNotIn("run", response.json())
        self.assertNotIn("filename", response.json())
        repeat = self.client.post(
            url, {"run": token, "passive": 9}, HTTP_ACCEPT="application/json"
        )
        self.assertEqual(repeat.json()["word_passive"], 3.3)
        self.assertEqual(WordComparison.objects.count(), 1)
        from django.contrib.messages import get_messages

        next_page = self.client.get(reverse("nofos:word_comparisons"))
        self.assertEqual(list(get_messages(next_page.wsgi_request)), [])

    def test_background_save_still_checks_permissions_and_expiry(self):
        import time

        token = self.stage()
        url = reverse("nofos:word_comparison_save")
        with patch("django.core.signing.time.time", return_value=time.time() + 1801):
            self.assertEqual(
                self.client.post(
                    url, {"run": token, "passive": 3}, HTTP_ACCEPT="application/json"
                ).status_code,
                404,
            )
        with override_config(HHS_NOFO_WORD_COMPARISONS_ENABLED=False):
            self.assertEqual(
                self.client.post(
                    url, {"run": token, "passive": 3}, HTTP_ACCEPT="application/json"
                ).status_code,
                404,
            )
        self.assertEqual(
            self.client.post(
                url,
                {"run": token + "tamper", "passive": 3},
                HTTP_ACCEPT="application/json",
            ).status_code,
            404,
        )
        other = BloomUser.objects.create_user(
            email="other-async@example.test",
            password=None,
            group="bloom",
            force_password_reset=False,
        )
        other.user_permissions.add(
            Permission.objects.get(codename="manage_word_comparisons")
        )
        self.client.force_login(other)
        self.assertEqual(
            self.client.post(
                url, {"run": token, "passive": 3}, HTTP_ACCEPT="application/json"
            ).status_code,
            404,
        )
        self.client.force_login(self.user)
        self.user.user_permissions.remove(
            Permission.objects.get(codename="manage_word_comparisons")
        )
        self.assertEqual(
            self.client.post(
                url, {"run": token, "passive": 3}, HTTP_ACCEPT="application/json"
            ).status_code,
            403,
        )
