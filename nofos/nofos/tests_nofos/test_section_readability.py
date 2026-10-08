import json
from importlib.metadata import version
from unittest.mock import patch

from constance.test import override_config
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from users.models import BloomUser

from nofos.models import (
    Nofo,
    NofoReadabilityScore,
    PolicyLanguageSlot,
    PolicyLanguageVariant,
    Section,
    Subsection,
)
from nofos.section_readability import measure_section
from nofos.section_readability_views import section_inputs

PROSE = (
    "We fund local groups that help people get the care they need. "
    "Your plan should explain how you will find people and help them get care. "
    "Tell us what your team will do and how you will check your work. "
    "We review each plan and send a letter to the groups we select."
)


class SectionMeasurementTests(SimpleTestCase):
    def test_real_engine_returns_numeric_grade_and_identity(self):
        result = measure_section(f"<p>{PROSE}</p>")
        self.assertEqual(result["status"], "current")
        self.assertIsInstance(result["grade"], (float, int))
        self.assertEqual(
            result["measurement"]["engine"]["version"], version("hhs-nofo-metrics")
        )
        self.assertEqual(result["measurement"]["input_contract"], "section-html-v1")
        self.assertEqual(result["sentence_count"], 4)

    def test_short_prose_is_not_given_a_grade(self):
        result = measure_section(
            "<p>We fund local work. You may apply. We review plans.</p>"
        )
        self.assertEqual(result["status"], "insufficient")
        self.assertIsNone(result["grade"])

    def test_long_single_sentence_is_insufficient(self):
        result = measure_section("<p>" + "we help people " * 30 + ".</p>")
        self.assertEqual(result["status"], "insufficient")

    def test_engine_owns_heading_list_and_table_scopes(self):
        baseline = measure_section(f"<p>{PROSE}</p>")
        self.assertEqual(
            measure_section(
                f"<h2>A heading with many complex words</h2><p>{PROSE}</p>"
            )["grade"],
            baseline["grade"],
        )
        for tag in ("li", "td"):
            with self.subTest(tag=tag):
                html = (
                    f"<ul><li>{PROSE}</li></ul>"
                    if tag == "li"
                    else f"<table><tr><td>{PROSE}</td></tr></table>"
                )
                self.assertEqual(measure_section(html)["grade"], baseline["grade"])

    def test_fragments_and_contacts_do_not_create_grade(self):
        for html in (
            "<p>Contact: test@example.org</p>",
            "<ul><li>Budget</li><li>Timeline</li></ul>",
            "<p></p>",
        ):
            with self.subTest(html=html):
                self.assertIsNone(measure_section(html)["grade"])


@override_config(
    HHS_NOFO_SECTION_READABILITY_ENABLED=True, HHS_NOFO_POLICY_EXPORT_ENABLED=False
)
class SectionReadabilityViewTests(TestCase):
    def setUp(self):
        self.user = BloomUser.objects.create_user(
            email="section@example.com",
            password="testpass",
            group="bloom",
            force_password_reset=False,
        )
        self.nofo = Nofo.objects.create(
            title="Synthetic section test",
            number="TEST-SECTION",
            opdiv="TEST",
            group="bloom",
            status="draft",
        )
        section = Section.objects.create(nofo=self.nofo, name="Step 1", order=1)
        self.body = Subsection.objects.create(
            section=section, name="Summary", order=1, body=PROSE, tag="h3"
        )
        self.slot = PolicyLanguageSlot.objects.create(
            slot_key="TEST-POLICY", name="Policy", slot_type="fixed", is_current=True
        )
        self.variant = PolicyLanguageVariant.objects.create(
            slot=self.slot, canonical_text="This is synthetic policy language."
        )
        self.url = reverse("nofos:section_readability", args=[self.nofo.pk])
        self.client.force_login(self.user)

    def post(self, **data):
        return self.client.post(
            self.url,
            json.dumps({"revision": section_inputs(self.nofo)[3], **data}),
            content_type="application/json",
        )

    def test_check_all_is_transient_and_recheck_is_scoped(self):
        short = Subsection.objects.create(
            section=self.body.section,
            name="Short",
            tag="h3",
            order=2,
            body="We fund work. You may apply. We review plans.",
        )
        payload = self.post().json()
        self.assertEqual(
            [r["status"] for r in payload["results"]], ["current", "insufficient"]
        )
        self.assertEqual(
            len(self.post(subsection_id=str(short.pk)).json()["results"]), 1
        )
        self.assertFalse(NofoReadabilityScore.objects.exists())
        self.assertIn("no-store", self.post()["Cache-Control"])
        self.body.refresh_from_db()
        self.assertEqual(self.body.body, PROSE)

    def test_missing_and_incomplete_policy_data_fail_closed(self):
        self.variant.delete()
        with patch("nofos.section_readability_views.measure_section") as scoring:
            self.assertEqual(
                self.post().json()["results"][0]["status"], "policy_unavailable"
            )
            scoring.assert_not_called()
        self.slot.delete()
        self.assertEqual(
            self.post().json()["results"][0]["status"], "policy_unavailable"
        )

    def test_fresh_policy_checks_current_prior_altered_and_mixed(self):
        old = PolicyLanguageSlot.objects.create(
            slot_key=self.slot.slot_key,
            name="Policy",
            slot_type="fixed",
            is_current=False,
        )
        PolicyLanguageVariant.objects.create(
            slot=old, canonical_text="This is earlier synthetic policy language."
        )
        cases = [
            ("Policy", self.variant.canonical_text),
            ("Policy", "This is earlier synthetic policy language."),
            ("Policy", "Altered text."),
            ("Summary", PROSE + " " + self.variant.canonical_text),
        ]
        self.slot.match_scope = "span_within_subsection"
        # Whole-subsection alignment also excludes altered text by heading.
        for name, body in cases[:3]:
            with self.subTest(name=name, body=body):
                self.body.name, self.body.body = name, body
                self.body.save()
                self.assertEqual(
                    self.post().json()["results"][0]["status"], "excluded_policy"
                )
        self.slot.save()
        self.body.name, self.body.body = cases[3]
        self.body.save()
        with patch("nofos.section_readability_views.measure_section") as scoring:
            self.assertEqual(
                self.post().json()["results"][0]["status"], "excluded_policy"
            )
            scoring.assert_not_called()
        self.body.refresh_from_db()
        self.assertEqual(self.body.policy_language_status, "none")

    def test_basic_information_excluded(self):
        self.body.name = "Basic information"
        self.body.save()
        self.assertEqual(self.post().json()["results"][0]["status"], "excluded_basic")

    def test_stale_page_and_mid_calculation_edits_rejected(self):
        revision = section_inputs(self.nofo)[3]
        self.body.body += " We have changed this text."
        self.body.save()
        self.assertEqual(self.post(revision=revision).status_code, 409)

        def changed(_html):
            Subsection.objects.filter(pk=self.body.pk).update(body="Changed again.")
            return {"status": "current", "grade": 4}

        with patch(
            "nofos.section_readability_views.measure_section", side_effect=changed
        ):
            self.assertEqual(self.post().status_code, 409)

    def test_canonical_change_invalidates_page(self):
        revision = section_inputs(self.nofo)[3]
        self.variant.canonical_text += " A changed policy."
        self.variant.save()
        self.assertEqual(self.post(revision=revision).status_code, 409)

    def test_partial_failure_preserves_other_sections(self):
        Subsection.objects.create(
            section=self.body.section, name="Second", tag="h3", order=2, body=PROSE
        )
        with patch(
            "nofos.section_readability_views.measure_section",
            side_effect=[
                RuntimeError("private text"),
                {"status": "current", "grade": 4},
            ],
        ):
            response = self.post()
        self.assertEqual(
            [r["status"] for r in response.json()["results"]],
            ["unavailable", "current"],
        )
        self.assertNotContains(response, "private text")

    @override_settings(HHS_NOFO_METRIC_GOALS={})
    def test_absent_targets_do_not_invent_assessments(self):
        self.assertEqual(self.post().json()["goals"], [])

    @override_settings(
        HHS_NOFO_METRIC_GOALS={
            "flesch_kincaid_grade_level": {
                "label": "Configured goal",
                "operator": "at_most",
                "value": 12,
            }
        }
    )
    def test_reuses_existing_configured_targets(self):
        self.assertEqual(self.post().json()["goals"][0]["value"], 12)

    def test_permissions_csrf_and_method(self):
        self.user.group = "cdc"
        self.user.save()
        self.assertEqual(self.post().status_code, 403)
        self.user.group = "bloom"
        self.user.save()
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.user)
        self.assertEqual(
            protected.post(self.url, "{}", content_type="application/json").status_code,
            403,
        )
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertEqual(self.post(subsection_id="not-this-nofo").status_code, 400)
        self.assertEqual(
            self.client.post(
                self.url, "[]", content_type="application/json"
            ).status_code,
            400,
        )

    @override_config(HHS_NOFO_SECTION_READABILITY_ENABLED=False)
    def test_disabled_endpoint_and_ui(self):
        self.assertEqual(self.post().status_code, 503)
        self.assertNotContains(
            self.client.get(reverse("nofos:nofo_edit", args=[self.nofo.pk])),
            'id="section-readability"',
        )

    def test_ui_only_on_editor_no_automatic_scoring(self):
        with patch("nofos.section_readability_views.measure_section") as scoring:
            response = self.client.get(reverse("nofos:nofo_edit", args=[self.nofo.pk]))
            self.assertContains(response, 'id="section-readability"')
            scoring.assert_not_called()
        self.assertNotContains(
            self.client.get(reverse("nofos:nofo_export", args=[self.nofo.pk])),
            "Check section readability",
        )
