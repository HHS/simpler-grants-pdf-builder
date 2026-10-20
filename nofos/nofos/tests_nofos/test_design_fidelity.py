"""Bounded offline evidence is not whole-document fidelity or approval."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from nofos import design_fidelity as fidelity
from nofos import design_pilot_review as review
from nofos.design_candidate import DesignRequestError
from nofos.models import DesignPilotReviewDecision
from nofos.tests_nofos import test_design_pilot_review as review_fixtures

TABLE = '<table><tr><th>Amount</th><th>Period</th></tr><tr><td>$125,000</td><td rowspan="2">12 months</td></tr></table>'
LIST = '<ol start="3"><li>Prepare budget</li><li value="8">Submit</li></ol>'
LINK = '<a href="https://example.test/apply">Apply</a>'
IMAGE = '<img src="data:image/png;base64,aW52ZW50ZWQ=">'
SOURCE = TABLE + LIST + LINK + IMAGE


def rows(source, output):
    return {row["id"]: row for row in fidelity.inspect(source, output)}


class FidelityInventoryTests(SimpleTestCase):
    def test_exact_supported_elements_survive_generated_extras(self):
        generated = "<table><tr><td>Generated metadata</td></tr></table>"
        result = rows(SOURCE, generated + SOURCE)
        for key in ("tables", "ordered_lists", "links", "images"):
            self.assertEqual(result[key]["status"], "pass")

    def test_changed_numbers_cells_spans_and_whitespace_do_not_pass(self):
        for altered in (
            TABLE.replace("125,000", "12,500"),
            TABLE.replace('rowspan="2"', 'rowspan="1"'),
            TABLE.replace("12 months", "12months"),
            TABLE.replace("<td>$125,000</td>", ""),
        ):
            self.assertEqual(rows(TABLE, altered)["tables"]["status"], "fail")

    def test_list_start_value_and_item_order_are_preserved(self):
        for altered in (
            LIST.replace('start="3"', 'start="1"'),
            LIST.replace('value="8"', 'value="9"'),
            '<ol start="3"><li value="8">Submit</li><li>Prepare budget</li></ol>',
        ):
            self.assertEqual(rows(LIST, altered)["ordered_lists"]["status"], "fail")
        self.assertEqual(
            rows(LIST.replace("<ol ", "<ol reversed "), LIST)["ordered_lists"][
                "status"
            ],
            "fail",
        )

    def test_header_semantics_and_equal_count_input_changes_are_bound(self):
        self.assertEqual(
            rows(TABLE, TABLE.replace("<th>", "<td>").replace("</th>", "</td>"))[
                "tables"
            ]["status"],
            "fail",
        )
        first = rows("<p>First source</p>", "<p>First source</p>")["tables"]
        second = rows("<p>Other source</p>", "<p>Other source</p>")["tables"]
        self.assertEqual(first["evidence"], second["evidence"])
        self.assertNotEqual(first["input_digest"], second["input_digest"])

    def test_reordering_and_duplicate_loss_are_not_hidden_by_membership(self):
        first = TABLE
        second = TABLE.replace("125,000", "55,000")
        self.assertEqual(
            rows(first + second, second + first)["tables"]["status"], "fail"
        )
        self.assertEqual(rows(LINK + LINK, LINK)["links"]["status"], "fail")

    def test_removed_remapped_or_empty_destinations_are_not_inferred_equivalent(self):
        for source, output in (
            (LINK, "<a>Apply</a>"),
            ('<a href="#old">See</a>', '<a href="#new">See</a>'),
            ("<a>Empty</a>", "<a>Empty</a>"),
        ):
            self.assertEqual(rows(source, output)["links"]["status"], "fail")
        self.assertEqual(rows(IMAGE, "")["images"]["status"], "fail")

    def test_absent_conversion_elements_are_not_claimed_absent_in_word(self):
        result = rows("<p>Plain prose only</p>", "<p>Plain prose only</p>")
        for key in ("tables", "ordered_lists", "links", "images", "static-assets"):
            self.assertEqual(result[key]["status"], "not_assessed")

    def test_nested_tables_and_resource_budgets_are_explicit(self):
        nested = "<table><tr><td>" + TABLE + "</td></tr></table>"
        self.assertEqual(rows(nested, nested)["inventory"]["status"], "not_assessed")
        with patch.object(fidelity, "MAX_HTML_BYTES", 2):
            self.assertIn("inventory", rows(TABLE, TABLE))
        with patch.object(fidelity, "MAX_ITEMS", 1):
            self.assertIn("inventory", rows(LINK * 2, LINK * 2))

    def test_unsupported_and_oversized_inputs_still_bind_exact_evidence(self):
        first = "<table><tr><td>" + TABLE + "</td></tr></table>"
        other = first.replace("125,000", "55,000")
        self.assertNotEqual(
            rows(first, first)["inventory"]["input_digest"],
            rows(other, first)["inventory"]["input_digest"],
        )
        with patch.object(fidelity, "MAX_HTML_BYTES", 2):
            self.assertNotEqual(
                rows("abc", "abc")["inventory"]["input_digest"],
                rows("xyz", "abc")["inventory"]["input_digest"],
            )
        header = TABLE.replace("<th>", '<th id="budget">', 1)
        self.assertEqual(
            rows(header, header.replace('id="budget"', 'id="other"'))["tables"][
                "status"
            ],
            "fail",
        )

    def test_css_driven_list_markers_are_unsupported_not_false_pass(self):
        styled = LIST.replace("<ol ", '<ol style="list-style-type:lower-alpha" ')
        result = rows(styled, styled.replace("lower-alpha", "decimal"))
        self.assertEqual(result["inventory"]["status"], "not_assessed")
        self.assertIn("CSS-driven", result["inventory"]["evidence"])

    def test_only_direct_local_asset_bytes_are_hashed_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve() / "theme.css"
            path.write_bytes(b"/* invented test asset */")
            html = '<link rel="stylesheet" href="/static/theme.css">'
            with patch.object(fidelity.finders, "find", return_value=str(path)), patch(
                "socket.create_connection", side_effect=AssertionError("No network")
            ):
                first = rows("", html)["static-assets"]
                path.write_bytes(b"/* changed test asset */")
                second = rows("", html)["static-assets"]
            self.assertEqual(first["status"], "pass")
            self.assertNotEqual(first["evidence"], second["evidence"])
        with patch.object(fidelity.finders, "find", return_value=None):
            self.assertEqual(rows("", html)["static-assets"]["status"], "fail")

    def test_path_traversal_and_linked_or_large_assets_fail_closed(self):
        for url in (
            "/static/../private",
            "/static/%2e%2e/private",
            "/static/%252e%252e/private",
            "/static/foo\\bar",
        ):
            with patch.object(fidelity.finders, "find") as find:
                self.assertEqual(
                    rows("", f'<img src="{url}">')["static-assets"]["status"], "fail"
                )
                find.assert_not_called()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve() / "asset"
            path.write_bytes(b"123")
            link = path.with_name("linked")
            link.symlink_to(path)
            with patch.object(fidelity.finders, "find", return_value=str(link)):
                self.assertEqual(
                    rows("", '<img src="/static/test">')["static-assets"]["status"],
                    "fail",
                )
            with patch.object(
                fidelity.finders, "find", return_value=str(path)
            ), patch.object(fidelity, "MAX_ASSET_BYTES", 2):
                self.assertEqual(
                    rows("", '<img src="/static/test">')["static-assets"]["status"],
                    "fail",
                )

    def test_total_local_asset_budget_is_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve() / "asset"
            path.write_bytes(b"123")
            with patch.object(
                fidelity.finders, "find", return_value=str(path)
            ), patch.object(fidelity, "MAX_TOTAL_ASSET_BYTES", 4):
                self.assertEqual(
                    rows("", '<img src="/static/first"><img src="/static/second">')[
                        "static-assets"
                    ]["status"],
                    "fail",
                )


class ConnectedFidelityTests(TestCase):
    setUp = review_fixtures.CandidateReviewTests.setUp
    upload = review_fixtures.CandidateReviewTests.upload
    candidate = review_fixtures.CandidateReviewTests.candidate
    warning = review_fixtures.CandidateReviewTests.warning
    acknowledgment = review_fixtures.CandidateReviewTests.acknowledgment

    def test_report_adds_evidence_without_clearing_overall_fidelity(self):
        run = self.candidate()
        report = review.report(run)
        findings = {f["id"]: f for f in report["findings"]}
        self.assertEqual(findings["source-import"]["severity"], "blocking")
        self.assertEqual(findings["assets-links"]["severity"], "blocking")
        self.assertFalse(report["acceptance_available"])
        self.assertIn("fidelity-tables", findings)
        response = self.client.get(reverse("design_pilot:review", args=[run.pk]))
        self.assertContains(response, "Converted table cells and spans")
        self.assertContains(response, "Direct local HTML resources")

    def test_changed_resource_evidence_stales_human_acknowledgment(self):
        run = self.warning()
        evidence = dict(
            id="static-assets",
            status="pass",
            target="Direct local HTML resources",
            evidence="manifest-v1",
            action="Bounded check only",
        )
        with patch.object(review, "inspect_fidelity", return_value=[evidence]):
            command = self.acknowledgment(run)
        with patch.object(
            review,
            "inspect_fidelity",
            return_value=[{**evidence, "evidence": "manifest-v2"}],
        ):
            with self.assertRaises(DesignRequestError):
                review.acknowledge(self.user, run.pk, command)
        self.assertFalse(DesignPilotReviewDecision.objects.exists())

    def test_failures_are_blocking_but_missing_conversion_element_is_informational(
        self,
    ):
        run = self.candidate()
        with patch.object(
            review,
            "inspect_fidelity",
            return_value=[
                dict(
                    id="images",
                    status="not_assessed",
                    target="Images",
                    evidence="No converted image",
                    action="Unknown source coverage",
                ),
                dict(
                    id="links",
                    status="fail",
                    target="Links",
                    evidence="One unmatched",
                    action="Reconcile",
                ),
            ],
        ):
            findings = {f["id"]: f for f in review.report(run)["findings"]}
        self.assertEqual(findings["fidelity-images"]["severity"], "info")
        self.assertEqual(findings["fidelity-links"]["severity"], "blocking")
