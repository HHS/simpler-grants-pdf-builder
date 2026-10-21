"""Human-only review controls, not acceptance or a complete fidelity check."""

from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from nofos import design_pilot_review as review
from nofos.design_candidate import DesignRequestError
from nofos.models import DesignPilotCandidate, DesignPilotReviewDecision
from nofos.tests_nofos import test_design_pilot_host as fixtures


class CandidateReviewTests(TestCase):
    setUp = fixtures.ConnectedDesignPilotTests.setUp
    upload = fixtures.ConnectedDesignPilotTests.upload
    candidate = fixtures.ConnectedDesignPilotTests.candidate
    command = fixtures.ConnectedDesignPilotTests.command

    def warning(self):
        run = self.candidate()
        run.warnings = ["Review synthetic conversion detail."]
        DesignPilotCandidate.objects.filter(pk=run.pk).update(warnings=run.warnings)
        return run

    def acknowledgment(self, run, finding_id="import-warning-0"):
        report = review.report(run)
        item = next(f for f in report["findings"] if f["id"] == finding_id)
        return dict(
            expected_revision=report["revision"],
            evidence_revision=report["evidence_revision"],
            finding_id=item["id"],
            finding_digest=item["digest"],
            reason="Compared this synthetic detail with the source.",
        )

    def test_no_diagnostic_findings_does_not_claim_acceptance_ready(self):
        run = self.candidate()
        with patch.object(review, "find_broken_links", return_value=[]), patch.object(
            review, "find_endnote_issues", return_value=[]
        ), patch.object(
            review, "find_incorrectly_nested_heading_levels", return_value=[]
        ), patch.object(
            review, "find_same_or_higher_heading_levels_consecutive", return_value=[]
        ):
            report = review.report(run)
        by_id = {f["id"]: f for f in report["findings"]}
        self.assertEqual(by_id["baseline"]["status"], "pass")
        self.assertEqual(by_id["links"]["status"], "pass")
        self.assertEqual(by_id["source-import"]["status"], "not_assessed")
        self.assertEqual(by_id["assets-links"]["severity"], "blocking")
        self.assertEqual(by_id["pdf"]["severity"], "info")
        self.assertEqual(by_id["pdf"]["status"], "unsupported")
        self.assertFalse(report["acceptance_available"])
        self.assertGreaterEqual(report["blockers"], 2)
        response = self.client.get(reverse("design_pilot:review", args=[run.pk]))
        self.assertContains(response, "Ready for review")
        self.assertContains(response, "not a production NOFO")
        self.assertContains(response, "Design acceptance is not available")
        self.assertContains(response, "PDF unavailable")
        self.assertContains(response, "No presentation changes have been saved")

    def test_acknowledgment_records_human_time_reason_and_retry_is_immutable(self):
        run = self.warning()
        payload = self.acknowledgment(run)
        url = reverse("design_pilot:acknowledge", args=[run.pk])
        self.assertEqual(self.client.post(url, payload).status_code, 302)
        decision = DesignPilotReviewDecision.objects.get()
        self.assertEqual(decision.actor, self.user)
        self.assertEqual(decision.reason, payload["reason"])
        self.assertIsNotNone(decision.created)
        payload["reason"] = "A retry must not rewrite history."
        self.assertEqual(self.client.post(url, payload).status_code, 302)
        decision.refresh_from_db()
        self.assertNotEqual(decision.reason, payload["reason"])
        response = self.client.get(reverse("design_pilot:review", args=[run.pk]))
        self.assertContains(response, "Acknowledged by owner@example.com")
        self.assertContains(response, decision.reason)
        self.assertEqual(review.report(run)["open_warnings"], 0)
        self.assertGreaterEqual(review.report(run)["blockers"], 2)

    def test_acknowledgment_never_clears_blocker_or_capability_limit(self):
        run = self.warning()
        for key in ("source-import", "assets-links", "baseline", "pdf"):
            with self.assertRaises(DesignRequestError):
                review.acknowledge(self.user, run.pk, self.acknowledgment(run, key))
        self.assertFalse(DesignPilotReviewDecision.objects.exists())

    def test_stale_design_or_render_inputs_invalidate_warning_form(self):
        run = self.warning()
        payload = self.acknowledgment(run)
        review.acknowledge(self.user, run.pk, payload)
        updated = fixtures.host.update_candidate(self.user, run.pk, self.command(run))
        self.assertEqual(review.report(updated)["open_warnings"], 1)
        with self.assertRaises(DesignRequestError):
            review.acknowledge(self.user, run.pk, payload)
        fresh = self.acknowledgment(updated)
        with patch.object(
            fixtures.host, "_render_inputs", return_value="changed-assets"
        ):
            with self.assertRaises(DesignRequestError):
                review.acknowledge(self.user, run.pk, fresh)
        self.assertEqual(DesignPilotReviewDecision.objects.count(), 1)

    def test_changed_warning_evidence_stales_even_with_same_html(self):
        run = self.warning()
        payload = self.acknowledgment(run)
        DesignPilotCandidate.objects.filter(pk=run.pk).update(
            warnings=["Different warning"]
        )
        with self.assertRaises(DesignRequestError):
            review.acknowledge(self.user, run.pk, payload)
        self.assertFalse(DesignPilotReviewDecision.objects.exists())

    def test_existing_diagnostic_target_and_failure_are_not_silenced(self):
        run = self.candidate()
        subsection = run.nofo.sections.first().subsections.first()
        issue = {"subsection": subsection, "error": "Synthetic skipped heading"}
        with patch.object(
            review, "find_incorrectly_nested_heading_levels", return_value=[issue]
        ):
            report = review.report(run)
        finding = next(f for f in report["findings"] if f["evidence"] == issue["error"])
        self.assertEqual(finding["section_id"], str(subsection.section_id))
        self.assertEqual(finding["severity"], "blocking")
        with patch.object(
            review, "find_broken_links", side_effect=KeyError("unsupported")
        ):
            report = review.report(run)
        self.assertEqual(
            next(f for f in report["findings"] if f["id"] == "links")["status"],
            "not_assessed",
        )

    def test_html_failure_and_outside_content_changes_fail_closed(self):
        run = self.warning()
        url = reverse("design_pilot:review", args=[run.pk])
        with patch.object(
            fixtures.host,
            "_safe_document",
            side_effect=DesignRequestError("Synthetic render failure"),
        ):
            response = self.client.get(url)
        self.assertContains(response, "Synthetic render failure", status_code=409)
        payload = self.acknowledgment(run)
        run.nofo.title = "Outside content change"
        run.nofo.save(update_fields=["title"])
        self.assertEqual(self.client.get(url).status_code, 409)
        with self.assertRaises(DesignRequestError):
            review.acknowledge(self.user, run.pk, payload)

    def test_owner_group_csrf_post_and_profile_gates(self):
        run = self.warning()
        payload = self.acknowledgment(run)
        url = reverse("design_pilot:acknowledge", args=[run.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.user)
        self.assertEqual(csrf.post(url, payload).status_code, 403)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(url, payload).status_code, 404)
        self.client.force_login(self.user)
        self.user.group = "hrsa"
        self.user.save(update_fields=["group"])
        self.assertEqual(self.client.post(url, payload).status_code, 404)
        with override_settings(DESIGN_PILOT_ENABLED=False):
            self.assertEqual(self.client.post(url, payload).status_code, 404)
        self.assertFalse(DesignPilotReviewDecision.objects.exists())

    def test_invalid_or_forged_fields_and_escaped_untrusted_text(self):
        run = self.warning()
        payload = self.acknowledgment(run)
        for change in (
            {"actor": str(self.other.pk)},
            {"reason": ""},
            {"reason": "x" * 501},
            {"finding_digest": "forged"},
            {"finding_id": "unknown"},
            {"reason": 12},
        ):
            with self.assertRaises(DesignRequestError):
                review.acknowledge(self.user, run.pk, {**payload, **change})
        payload["reason"] = "<script>synthetic-not-code</script>"
        review.acknowledge(self.user, run.pk, payload)
        response = self.client.get(reverse("design_pilot:review", args=[run.pk]))
        self.assertNotContains(response, payload["reason"])
        self.assertContains(response, "&lt;script&gt;synthetic-not-code&lt;/script&gt;")

    def test_repeated_fields_bounded_body_and_no_pdf_or_network(self):
        run = self.warning()
        url = reverse("design_pilot:acknowledge", args=[run.pk])
        self.assertEqual(
            self.client.post(url, {"reason": ["one", "two"]}).status_code, 400
        )
        self.assertEqual(self.client.post(url, {"reason": "x" * 4097}).status_code, 400)
        with patch(
            "socket.create_connection", side_effect=AssertionError("No network")
        ), patch(
            "nofos.pdf_service.docraptor.DocApi.create_doc",
            side_effect=AssertionError("No PDF"),
        ):
            response = self.client.get(reverse("design_pilot:review", args=[run.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(DesignPilotReviewDecision.objects.exists())

    def test_candidate_token_alone_cannot_make_a_human_decision(self):
        run = self.warning()
        from nofos import design_pilot_tools

        token, _ = design_pilot_tools.issue_access(self.user, run.pk)
        client = Client()
        response = client.post(
            reverse("design_pilot:acknowledge", args=[run.pk]),
            self.acknowledgment(run),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(
            response.status_code, 302
        )  # No session: sign-in, not token authority.
        self.assertFalse(DesignPilotReviewDecision.objects.exists())
