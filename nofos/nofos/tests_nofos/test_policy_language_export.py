from unittest.mock import patch

from bs4 import BeautifulSoup
from django.http import HttpResponse
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from users.models import BloomUser

from nofos.models import Nofo, PolicyLanguageSlot, PolicyLanguageVariant, Section, Subsection
from nofos.nofo import _build_document
from nofos.readability import ReadabilityMetricsUnavailable
from nofos.views import duplicate_nofo


class PolicyLanguageImportTaggingTests(TestCase):
    """Import-time detection must be gated by HHS_NOFO_POLICY_EXPORT_ENABLED
    itself, not just by the model having the field - a disabled flag should
    mean zero extra work on a normal import, not just a hidden export
    button."""

    @classmethod
    def setUpTestData(cls):
        cls.slot = PolicyLanguageSlot.objects.create(
            slot_key="TEST-IMPORT-TAG", name="Import Tag Test Slot", slot_type="fixed",
            required=False, flag_prominently=False, template_version="v1",
        )
        PolicyLanguageVariant.objects.create(
            slot=cls.slot, canonical_text="This exact canonical sentence must be present."
        )

    @staticmethod
    def _section_input(subsection_name, body):
        return [{
            "name": "Section One", "order": 1, "has_section_page": False,
            "subsections": [{
                "name": subsection_name, "order": 1, "body": body, "tag": "h4",
            }],
        }]

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=False)
    def test_flag_off_does_not_tag_even_on_exact_match(self):
        nofo = Nofo.objects.create(
            title="Flag off import", short_name="flag-off-import", number="TEST-TAG-001",
            opdiv="TEST", group="bloom", status="draft",
        )
        _build_document(
            nofo,
            self._section_input(
                "Import Tag Test Slot", "This exact canonical sentence must be present."
            ),
            SectionModel=Section, SubsectionModel=Subsection,
        )
        subsection = Subsection.objects.get(section__nofo=nofo)
        self.assertEqual(subsection.policy_language_status, "none")
        self.assertIsNone(subsection.policy_language_slot)

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=True)
    def test_flag_on_tags_exact_match_as_intact(self):
        nofo = Nofo.objects.create(
            title="Flag on import", short_name="flag-on-import", number="TEST-TAG-002",
            opdiv="TEST", group="bloom", status="draft",
        )
        _build_document(
            nofo,
            self._section_input(
                "Import Tag Test Slot", "This exact canonical sentence must be present."
            ),
            SectionModel=Section, SubsectionModel=Subsection,
        )
        subsection = Subsection.objects.get(section__nofo=nofo)
        self.assertEqual(subsection.policy_language_status, "intact")
        self.assertEqual(subsection.policy_language_slot_id, self.slot.id)

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=True)
    def test_flag_on_ordinary_content_stays_none(self):
        nofo = Nofo.objects.create(
            title="Ordinary import", short_name="ordinary-import", number="TEST-TAG-003",
            opdiv="TEST", group="bloom", status="draft",
        )
        _build_document(
            nofo,
            self._section_input(
                "Program Summary", "This program funds community health workers."
            ),
            SectionModel=Section, SubsectionModel=Subsection,
        )
        subsection = Subsection.objects.get(section__nofo=nofo)
        self.assertEqual(subsection.policy_language_status, "none")


class NofoExportPolicyLanguageRenderingTests(TestCase):
    """Full export-view rendering: flag on/off, stripped vs. flagged vs.
    ordinary content, the watermark, and the generated clearance summary."""

    @classmethod
    def setUpTestData(cls):
        cls.user = BloomUser.objects.create_user(
            email="policy-export-test@example.com", password="testpass123",
            group="bloom", force_password_reset=False,
        )

        cls.sam_slot = PolicyLanguageSlot.objects.create(
            slot_key="TEST-SAM-SLOT", name="SAM.gov registration requirement",
            slot_type="fixed", template_version="v1",
        )
        PolicyLanguageVariant.objects.create(
            slot=cls.sam_slot,
            canonical_text=(
                "Your organization must have an active account with SAM.gov "
                "to apply unless you are exempt under 2 CFR 25. SAM.gov "
                "registration can take several weeks."
            ),
        )

        cls.altered_slot = PolicyLanguageSlot.objects.create(
            slot_key="TEST-ALTERED-SLOT", name="Initial review",
            slot_type="fixed", template_version="v1",
        )
        PolicyLanguageVariant.objects.create(
            slot=cls.altered_slot, canonical_text="Standard initial-review text."
        )

        cls.prominent_slot = PolicyLanguageSlot.objects.create(
            slot_key="TEST-PROMINENT-SLOT",
            name="Funding preferences/priorities for alignment with agency priorities",
            slot_type="fixed", flag_prominently=True, template_version="v1",
        )
        PolicyLanguageVariant.objects.create(
            slot=cls.prominent_slot, canonical_text="Standard funding-preferences text."
        )

        # Required, but deliberately never matched by any subsection below -
        # exercises the clearance summary's missing-required-slot listing.
        cls.missing_required_slot = PolicyLanguageSlot.objects.create(
            slot_key="TEST-MISSING-REQUIRED-SLOT", name="Missing Required Slot",
            slot_type="fixed", required=True, template_version="v1",
        )
        PolicyLanguageVariant.objects.create(
            slot=cls.missing_required_slot, canonical_text="Text nobody imported."
        )

        cls.nofo = Nofo.objects.create(
            title="Policy export view test NOFO", short_name="policy-export-view-test",
            number="TEST-VIEW-001", opdiv="TEST", group="bloom", status="draft",
        )
        section = Section.objects.create(
            nofo=cls.nofo, name="Before You Get Started",
            html_id="before-you-get-started", order=1,
        )
        Subsection.objects.create(
            section=section, name=cls.sam_slot.name, tag="h4",
            body=cls.sam_slot.variants.first().canonical_text, order=1,
            policy_language_status="intact", policy_language_slot=cls.sam_slot,
        )
        Subsection.objects.create(
            section=section, name=cls.altered_slot.name, tag="h4",
            body="This text has clearly been rewritten by the program office.", order=2,
            policy_language_status="may_be_altered", policy_language_slot=cls.altered_slot,
        )
        Subsection.objects.create(
            section=section, name=cls.prominent_slot.name, tag="h4",
            body="A modified version of the funding preferences language.", order=3,
            policy_language_status="may_be_altered", policy_language_slot=cls.prominent_slot,
        )
        Subsection.objects.create(
            section=section, name="Program Summary", tag="h4",
            body="This program funds community health workers in rural areas.", order=4,
            policy_language_status="none",
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)
        self.export_url = reverse("nofos:nofo_export", kwargs={"pk": self.nofo.pk})

    # --- Flag off: completely unaffected, regardless of query param -------

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=False)
    def test_flag_off_export_is_unaffected(self):
        resp = self.client.get(self.export_url)
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        self.assertNotIn("PRE-DECISIONAL", body)
        self.assertNotIn("Download for Clearance", body)
        self.assertIn(self.sam_slot.variants.first().canonical_text, body)

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=False)
    def test_flag_off_query_param_is_ignored(self):
        resp = self.client.get(self.export_url + "?policy_stripped=1")
        body = resp.content.decode()
        self.assertNotIn("PRE-DECISIONAL", body)
        self.assertIn(self.sam_slot.variants.first().canonical_text, body)

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=False)
    def test_flag_off_download_stripped_action_rejected(self):
        resp = self.client.post(self.export_url, {"export_action": "download_stripped"})
        self.assertEqual(resp.status_code, 400)

    # --- Flag on, plain export: still unaffected ---------------------------

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=True)
    def test_flag_on_plain_export_unaffected(self):
        resp = self.client.get(self.export_url)
        body = resp.content.decode()
        self.assertIn("Download for Clearance", body)
        self.assertNotIn("PRE-DECISIONAL", body)
        self.assertIn(self.sam_slot.variants.first().canonical_text, body)

    # --- Flag on, stripped export: the actual feature -----------------------

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=True)
    def test_flag_on_stripped_export_strips_intact_sections(self):
        resp = self.client.get(self.export_url + "?policy_stripped=1")
        body = resp.content.decode()
        self.assertNotIn(self.sam_slot.variants.first().canonical_text, body)
        self.assertIn("policy-language-stripped-note", body)

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=True)
    def test_flag_on_stripped_export_flags_altered_sections(self):
        resp = self.client.get(self.export_url + "?policy_stripped=1")
        body = resp.content.decode()
        self.assertIn("This text has clearly been rewritten", body)
        self.assertIn("REVIEW: This section corresponds to", body)

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=True)
    def test_flag_on_stripped_export_elevates_prominent_slot(self):
        resp = self.client.get(self.export_url + "?policy_stripped=1")
        body = resp.content.decode()
        self.assertIn("PRIORITY REVIEW: This section corresponds to HHS-locked", body)

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=True)
    def test_flag_on_stripped_export_leaves_ordinary_content_untouched(self):
        resp = self.client.get(self.export_url + "?policy_stripped=1")
        body = resp.content.decode()
        self.assertIn("This program funds community health workers", body)

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=True)
    def test_flag_on_stripped_export_includes_watermark(self):
        resp = self.client.get(self.export_url + "?policy_stripped=1")
        body = resp.content.decode()
        self.assertIn("PRE-DECISIONAL", body)
        self.assertIn("NOT THE OFFICIAL SUBMISSION COPY", body)

    # --- The generated page-1 clearance summary -----------------------------

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=True)
    def test_clearance_summary_says_nofo_builder_not_builder(self):
        resp = self.client.get(self.export_url + "?policy_stripped=1")
        body = resp.content.decode()
        self.assertIn("Clearance Review Summary", body)
        self.assertIn("NOFO Builder", body)

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=True)
    def test_clearance_summary_reports_correct_stripped_and_flagged_counts(self):
        resp = self.client.get(self.export_url + "?policy_stripped=1")
        soup = BeautifulSoup(resp.content, "html.parser")
        summary_text = " ".join(
            soup.select_one(".clearance-summary").get_text(" ", strip=True).split()
        )
        self.assertIn(
            "1 section matched current HHS Department Governance language", summary_text
        )
        self.assertIn("2 sections flagged below for review", summary_text)

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=True)
    def test_clearance_summary_lists_missing_required_slots(self):
        resp = self.client.get(self.export_url + "?policy_stripped=1")
        body = resp.content.decode()
        self.assertIn("Missing expected Department Governance language", body)

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=True)
    def test_clearance_summary_anchor_links_resolve_to_real_elements(self):
        resp = self.client.get(self.export_url + "?policy_stripped=1")
        soup = BeautifulSoup(resp.content, "html.parser")
        links = soup.select(".clearance-summary a")
        self.assertTrue(links)
        for link in links:
            target_id = link["href"].lstrip("#")
            self.assertIsNotNone(
                soup.find(id=target_id), f"anchor target #{target_id} not found"
            )

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=True)
    def test_clearance_summary_includes_readability_metrics_when_available(self):
        resp = self.client.get(self.export_url + "?policy_stripped=1")
        body = resp.content.decode()
        self.assertIn("Readability metrics", body)
        self.assertIn("Total Words", body)

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=True)
    def test_clearance_summary_omits_metrics_gracefully_when_unavailable(self):
        with patch(
            "nofos.views.analyze_nofo_readability",
            side_effect=ReadabilityMetricsUnavailable("not installed"),
        ):
            resp = self.client.get(self.export_url + "?policy_stripped=1")
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        self.assertNotIn("Readability metrics", body)
        self.assertIn("Clearance Review Summary", body)

    # --- Buttons: label, style, aria-label, modal notice --------------------

    def _get_export_nav_buttons(self, response):
        soup = BeautifulSoup(response.content, "html.parser")
        buttons = soup.select("nav.usa-nav button[type=submit]")
        return {b.get_text(" ", strip=True): b for b in buttons}

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=True)
    def test_download_word_is_primary_and_clearance_is_secondary_button(self):
        resp = self.client.get(self.export_url)
        labels = self._get_export_nav_buttons(resp)
        self.assertIn("Download Word", labels)
        self.assertIn("Download for Clearance", labels)
        self.assertNotIn("usa-button--outline", labels["Download Word"]["class"])
        self.assertIn("usa-button--outline", labels["Download for Clearance"]["class"])

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=True)
    def test_clearance_button_has_descriptive_aria_label(self):
        resp = self.client.get(self.export_url)
        labels = self._get_export_nav_buttons(resp)
        aria_label = labels["Download for Clearance"].get("aria-label", "")
        self.assertIn("clearance review", aria_label.lower())

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=True)
    def test_clearance_modal_shows_pre_decisional_notice(self):
        resp = self.client.get(self.export_url)
        body = resp.content.decode()
        self.assertIn("Pre-decisional", body)

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=False)
    def test_clearance_button_absent_when_flag_disabled(self):
        resp = self.client.get(self.export_url)
        labels = self._get_export_nav_buttons(resp)
        self.assertIn("Download Word", labels)
        self.assertNotIn("Download for Clearance", labels)


class NofoExportPolicyLanguagePostTests(TestCase):
    """POST /export builds a different GrabzIt export_url/filename per
    action - verified here without touching the real GrabzIt integration."""

    @classmethod
    def setUpTestData(cls):
        cls.user = BloomUser.objects.create_user(
            email="policy-export-post-test@example.com", password="testpass123",
            group="bloom", force_password_reset=False,
        )
        cls.nofo = Nofo.objects.create(
            title="Policy export POST test", short_name="policy-export-post-test",
            number="TEST-POST-001", opdiv="TEST", group="bloom", status="draft",
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)
        self.export_url = reverse("nofos:nofo_export", kwargs={"pk": self.nofo.pk})

    @staticmethod
    def _fake_generate(captured):
        def fake(*, request, export_url, target_element, filename_base, tmp_name):
            captured["export_url"] = export_url
            captured["filename_base"] = filename_base
            return HttpResponse(b"fake-docx-bytes")

        return fake

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=True)
    def test_download_action_builds_plain_export_url(self):
        captured = {}
        with patch(
            "nofos.views.generate_docx_download_response",
            side_effect=self._fake_generate(captured),
        ):
            resp = self.client.post(self.export_url, {"export_action": "download"})

        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("policy_stripped", captured["export_url"])
        self.assertEqual(captured["filename_base"], self.nofo.short_name)

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=True)
    def test_download_stripped_action_builds_stripped_export_url(self):
        captured = {}
        with patch(
            "nofos.views.generate_docx_download_response",
            side_effect=self._fake_generate(captured),
        ):
            resp = self.client.post(self.export_url, {"export_action": "download_stripped"})

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(captured["export_url"].endswith("?policy_stripped=1"))
        self.assertEqual(
            captured["filename_base"], f"{self.nofo.short_name} (Policy Language Stripped)"
        )

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=False)
    def test_download_stripped_action_rejected_when_flag_off(self):
        resp = self.client.post(self.export_url, {"export_action": "download_stripped"})
        self.assertEqual(resp.status_code, 400)

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=True)
    def test_unknown_action_rejected(self):
        resp = self.client.post(self.export_url, {"export_action": "bogus"})
        self.assertEqual(resp.status_code, 400)


class NofoExportPolicyLanguageFreshnessTests(TestCase):
    """
    The clearance export must never trust the stored policy_language_status
    for its own sake - nothing else in Builder keeps that column up to date
    after import. These reproduce the three ways it goes stale and confirm
    export still gets it right by recomputing fresh instead.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = BloomUser.objects.create_user(
            email="policy-freshness-test@example.com", password="testpass123",
            group="bloom", force_password_reset=False,
        )
        cls.sam_slot = PolicyLanguageSlot.objects.create(
            slot_key="TEST-FRESHNESS-SLOT", name="SAM.gov registration requirement",
            slot_type="fixed", template_version="v1",
        )
        PolicyLanguageVariant.objects.create(
            slot=cls.sam_slot,
            canonical_text=(
                "Your organization must have an active account with SAM.gov "
                "to apply unless you are exempt under 2 CFR 25. SAM.gov "
                "registration can take several weeks."
            ),
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)

    @staticmethod
    def _make_nofo(short_name, number):
        nofo = Nofo.objects.create(
            title=f"Freshness test {short_name}", short_name=short_name,
            number=number, opdiv="TEST", group="bloom", status="draft",
        )
        section = Section.objects.create(
            nofo=nofo, name="Before You Get Started",
            html_id="before-you-get-started", order=1,
        )
        return nofo, section

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=True)
    def test_subsection_edited_after_import_is_reflected_at_export(self):
        # Imported intact (matches canonical text exactly)...
        nofo, section = self._make_nofo("edit-staleness", "TEST-FRESH-001")
        subsection = Subsection.objects.create(
            section=section, name=self.sam_slot.name, tag="h4",
            body=self.sam_slot.variants.first().canonical_text, order=1,
            policy_language_status="intact", policy_language_slot=self.sam_slot,
        )

        # ...then edited afterward, the way a program office would in the
        # normal editor - nothing re-runs detection on save, so the stored
        # column still says "intact" even though the content no longer
        # matches. Confirm that's really the state before testing export.
        subsection.body = "This paragraph has been substantively rewritten."
        subsection.save(update_fields=["body"])
        subsection.refresh_from_db()
        self.assertEqual(subsection.policy_language_status, "intact")

        export_url = reverse("nofos:nofo_export", kwargs={"pk": nofo.pk})
        resp = self.client.get(export_url + "?policy_stripped=1")
        body = resp.content.decode()

        # If export trusted the stale stored status, this altered text
        # would be silently stripped. It must instead render visible with
        # a review flag.
        self.assertIn("This paragraph has been substantively rewritten.", body)
        self.assertIn("REVIEW: This section corresponds to", body)
        self.assertNotIn("policy-language-stripped-note", body)

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=True)
    def test_duplicated_nofo_reflects_edits_made_after_duplication(self):
        original, section = self._make_nofo("dup-original", "TEST-FRESH-002")
        Subsection.objects.create(
            section=section, name=self.sam_slot.name, tag="h4",
            body=self.sam_slot.variants.first().canonical_text, order=1,
            policy_language_status="intact", policy_language_slot=self.sam_slot,
        )

        duplicate = duplicate_nofo(original)

        duplicated_subsection = Subsection.objects.get(section__nofo=duplicate)
        # duplicate_nofo() copies the stored field verbatim via
        # model_to_dict - confirm that's really what happened here, so
        # this test is exercising the real gap, not a mocked-up one.
        self.assertEqual(duplicated_subsection.policy_language_status, "intact")

        duplicated_subsection.body = "The duplicated content was then rewritten."
        duplicated_subsection.save(update_fields=["body"])

        export_url = reverse("nofos:nofo_export", kwargs={"pk": duplicate.pk})
        resp = self.client.get(export_url + "?policy_stripped=1")
        body = resp.content.decode()

        self.assertIn("The duplicated content was then rewritten.", body)
        self.assertIn("REVIEW: This section corresponds to", body)
        self.assertNotIn("policy-language-stripped-note", body)

    @override_settings(HHS_NOFO_POLICY_EXPORT_ENABLED=True)
    def test_canonical_slot_revision_is_reflected_without_reimporting(self):
        nofo, section = self._make_nofo("canonical-revision", "TEST-FRESH-003")
        old_canonical_text = self.sam_slot.variants.first().canonical_text
        Subsection.objects.create(
            section=section, name=self.sam_slot.name, tag="h4",
            body=old_canonical_text, order=1,
            policy_language_status="intact", policy_language_slot=self.sam_slot,
        )

        # HHS revises this slot's wording - supersede it, the same way
        # ingest_canonical_policy_language would for a real template
        # update, without ever re-importing this NOFO.
        self.sam_slot.is_current = False
        self.sam_slot.save(update_fields=["is_current"])
        new_slot = PolicyLanguageSlot.objects.create(
            slot_key=self.sam_slot.slot_key, name=self.sam_slot.name, slot_type="fixed",
            required=True, template_version="TEST-REVISED",
        )
        PolicyLanguageVariant.objects.create(
            slot=new_slot,
            canonical_text="A deliberately revised version of the text.",
        )
        self.sam_slot.superseded_by = new_slot
        self.sam_slot.save(update_fields=["superseded_by"])

        export_url = reverse("nofos:nofo_export", kwargs={"pk": nofo.pk})
        resp = self.client.get(export_url + "?policy_stripped=1")
        body = resp.content.decode()

        # The subsection's text still matches the OLD wording, which is now
        # superseded rather than current - it should be flagged as matching
        # a prior version (content stays visible, same as any other
        # non-intact status), not silently stripped as "intact".
        self.assertNotIn("policy-language-stripped-note", body)
        self.assertIn("REVIEW: This section matches a prior version of", body)
        self.assertIn(old_canonical_text, body)  # visible, not stripped
