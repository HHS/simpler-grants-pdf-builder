import json
from copy import deepcopy
from types import SimpleNamespace

from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from nofos import content_processing as core
from nofos import design_pilot_host as host
from nofos import metadata_provenance as provenance
from nofos.design_candidate import DesignRequestError
from nofos.models import DesignPilotCandidate
from nofos.tests_nofos import test_design_pilot_host as fixtures
from nofos.tests_nofos.test_metadata_block_import import metadata_docx

HTML = '<body><h1>Step 1: Review the Opportunity</h1><h2>Basic information</h2><p>Keep body.</p><h2 id="first">Metadata</h2><p>OpDiv: NIH</p><p>Agency: Earlier</p><h2>Appendix</h2><p>Keep appendix.</p><h2 id="last">Metadata</h2><p>OpDiv: HHS</p><p></p><p>Agency: </p><p>Agency: Ignored duplicate</p><h3>After metadata</h3><p><a href="#first">Keep link wording</a></p><table><tr><td>125,000</td></tr></table></body>'


class CoreMetadataTraceTests(SimpleTestCase):
    def test_trace_is_detached_and_output_equivalent(self):
        soup = BeautifulSoup(HTML, "html.parser")
        original = str(soup)
        trace = []
        observed = core.builder_import_content(soup, metadata_trace=trace)
        ordinary = core.builder_import_content(soup)
        self.assertEqual(str(observed), str(ordinary))
        self.assertEqual(str(soup), original)
        self.assertEqual(trace[0]["selected_block"], 1)
        self.assertEqual(len(trace[0]["blocks"]), 2)
        self.assertEqual(len(trace[0]["flattened_links"]), 1)
        events = trace[0]["blocks"][1]["fields"]
        agency = [e for e in events if e.get("key") == "agency"]
        self.assertEqual([e["first"] for e in agency], [True, False])
        self.assertEqual(agency[0]["value_sha256"], provenance.digest(""))
        self.assertTrue(any(e["kind"] == "blank" for e in events))
        self.assertNotIn("Ignored duplicate", json.dumps(trace))
        self.assertIn("Keep link wording", str(observed))
        self.assertIn("125,000", str(observed))
        self.assertEqual(trace, json.loads(json.dumps(trace)))

    def test_full_processing_trace_does_not_change_sections_or_source(self):
        trace = []
        options = dict(
            builder_import=True, extract_scoped_tagline=True, editable_intro="detect"
        )
        ordinary = core.process_document_content(HTML, **options)
        observed = core.process_document_content(HTML, metadata_trace=trace, **options)
        self.assertEqual(ordinary.sections, observed.sections)
        self.assertEqual(str(ordinary.soup), str(observed.soup))
        self.assertEqual(ordinary.imported_tagline, observed.imported_tagline)
        self.assertEqual(len(trace), 1)  # Not a duplicate from heading-resolution copy.
        self.assertEqual(trace[0]["selected_block"], 1)

    def test_no_block_and_media_or_prose_boundary_are_not_consumed(self):
        soup = BeautifulSoup(
            "<body><h1>Metadata discussion</h1><p>Not a label</p></body>", "html.parser"
        )
        trace = []
        self.assertEqual(
            str(core.builder_import_content(soup, metadata_trace=trace)), str(soup)
        )
        self.assertIsNone(trace[0]["selected_block"])
        self.assertEqual(trace[0]["blocks"], [])
        for boundary in (
            '<p><img src="x">Agency: retained</p>',
            "<p>Ordinary prose remains.</p>",
            "<table><tr><td>Retained</td></tr></table>",
        ):
            soup = BeautifulSoup(
                "<body><h1>Metadata</h1><p>OpDiv: HHS</p>" + boundary + "</body>",
                "html.parser",
            )
            result = core.builder_import_content(soup, metadata_trace=[])
            self.assertIn(str(BeautifulSoup(boundary, "html.parser")), str(result))

    def test_invalid_trace_request_and_repeat_collection_are_rejected(self):
        for trace in ({}, ["caller-data"]):
            with self.assertRaises(ValueError):
                core.builder_import_content(
                    BeautifulSoup(HTML, "html.parser"), metadata_trace=trace
                )
        with self.assertRaises(ValueError):
            core.process_document_content(HTML, metadata_trace=[])

    def test_no_recognized_block_has_no_field_claims(self):
        html = "<body><h1>Opportunity</h1><p>Retained prose.</p></body>"
        soup = BeautifulSoup(html, "html.parser")
        trace = []
        core.builder_import_content(soup, metadata_trace=trace)
        run = SimpleNamespace(
            source_sha256=provenance.digest("invented source"),
            conversion_html=html,
            nofo=SimpleNamespace(),
        )
        run.metadata_trace_json = provenance.package_trace(
            run.source_sha256, html, soup, trace, run.nofo
        )
        self.assertEqual(provenance.check_trace(run)["destinations"], [])
        malformed = json.loads(run.metadata_trace_json)
        malformed["trace"] = [{"blocks": [None]}]
        run.metadata_trace_json = json.dumps(malformed)
        with self.assertRaises(ValueError):
            provenance.check_trace(run)


class HostedMetadataTraceTests(TestCase):
    setUp = fixtures.ConnectedDesignPilotTests.setUp
    upload = fixtures.ConnectedDesignPilotTests.upload
    candidate = fixtures.ConnectedDesignPilotTests.candidate
    command = fixtures.ConnectedDesignPilotTests.command

    def metadata_candidate(self, **options):
        return host.import_candidate(
            self.user,
            SimpleUploadedFile(
                "invented-metadata.docx",
                metadata_docx(**options),
                content_type=host.WORD_TYPE,
            ),
        )

    def replace_trace(self, run, data):
        DesignPilotCandidate.objects.filter(pk=run.pk).update(
            metadata_trace_json=json.dumps(data)
        )
        run.refresh_from_db()

    def test_actual_word_trace_fields_match_and_placeholder_uses_existing_rule(self):
        run = self.metadata_candidate(author="{Same as OpDiv.}")
        data = provenance.check_trace(run)
        rows = {r["destination"]: r for r in data["destinations"]}
        self.assertEqual(rows["agency"]["status"], "pass")
        self.assertEqual(rows["author"]["status"], "pass")
        self.assertEqual(run.nofo.author, "")
        self.assertEqual(data["source_sha256"], run.source_sha256)
        self.assertEqual(
            data["conversion_sha256"], provenance.digest(run.conversion_html)
        )
        self.assertNotIn("Synthetic Agency", run.metadata_trace_json)
        self.assertEqual(self.metadata_candidate(author="{Same as OpDiv.}").pk, run.pk)
        response = self.client.get(reverse("design_pilot:review", args=[run.pk]))
        self.assertContains(response, "Metadata provenance")
        self.assertContains(response, "Metadata destination: agency")
        self.assertContains(response, "Source and import: Not assessed (Blocking)")

    def test_legacy_candidate_has_no_inferred_block_or_backfill(self):
        run = self.candidate()
        self.assertIsNotNone(provenance.check_trace(run))
        DesignPilotCandidate.objects.filter(pk=run.pk).update(metadata_trace_json="")
        run.refresh_from_db()
        self.assertIsNone(provenance.check_trace(run))
        response = self.client.get(reverse("design_pilot:review", args=[run.pk]))
        self.assertContains(response, "predates Metadata provenance capture")

    def test_defaults_are_explicitly_unassessed_and_bad_opdiv_still_rejected(self):
        run = self.metadata_candidate(number="")
        row = next(
            r
            for r in provenance.check_trace(run)["destinations"]
            if r["destination"] == "number"
        )
        self.assertEqual(row["status"], "not_assessed")
        self.assertEqual(run.nofo.number, "NOFO #999")
        before = DesignPilotCandidate.objects.count()
        with self.assertRaises(ValidationError):
            self.metadata_candidate(opdiv="")
        self.assertEqual(DesignPilotCandidate.objects.count(), before)

    def test_source_conversion_destinations_and_status_are_checked(self):
        run = self.metadata_candidate()
        original = json.loads(run.metadata_trace_json)
        for mutate in (
            lambda d: d.update(source_sha256="wrong"),
            lambda d: d.update(conversion_sha256="wrong"),
            lambda d: d["destinations"][0].update(saved_sha256="wrong"),
            lambda d: d["destinations"][0].update(status="forged"),
            lambda d: d.update(trace=[]),
            lambda d: d["trace"][0].update(blocks=[None]),
            lambda d: d["trace"][0].update(selected_block=999),
            lambda d: d["trace"][0].update(rule="invented"),
            lambda d: d["trace"][0]["blocks"][0].update(fields=[]),
            lambda d: d["trace"][0]["blocks"][0]["fields"][0].update(first=False),
            lambda d: d["trace"][0].update(flattened_links=[None]),
            lambda d: d.update(destinations=[]),
            lambda d: d["destinations"][0].update(source_element=999),
            lambda d: d["destinations"][0].update(expected_sha256="invalid"),
        ):
            data = deepcopy(original)
            mutate(data)
            self.replace_trace(run, data)
            with self.assertRaises(DesignRequestError):
                host.review_artifact(run)
        self.replace_trace(run, original)
        host.review_artifact(run)

    def test_changed_trace_identity_stales_old_design_form(self):
        run = self.metadata_candidate()
        command = self.command(run)
        data = json.loads(run.metadata_trace_json)
        data["trace"][0]["after_sha256"] = "0" * 64
        self.replace_trace(run, data)
        with self.assertRaises(DesignRequestError):
            host.update_candidate(self.user, run.pk, command)
