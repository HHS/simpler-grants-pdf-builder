from unittest.mock import patch

from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase

from nofos.models import Nofo, PolicyLanguageSlot, PolicyLanguageVariant, Section, Subsection
from nofos.policy_language import (
    detect_policy_language_status,
    get_missing_required_slots,
    get_policy_language_export_note,
    get_policy_language_export_summary,
    normalize_for_comparison,
)


class NormalizeForComparisonTests(TestCase):
    def test_collapses_whitespace(self):
        self.assertEqual(normalize_for_comparison("a   b\n\nc"), "a b c")

    def test_normalizes_smart_quotes_and_dashes(self):
        self.assertEqual(
            normalize_for_comparison("“Hello” — it’s a test"),
            "\"Hello\" - it's a test",
        )

    def test_none_input_is_empty_string(self):
        self.assertEqual(normalize_for_comparison(None), "")


class DetectPolicyLanguageStatusTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.fixed_slot = PolicyLanguageSlot.objects.create(
            slot_key="TEST-FIXED",
            name="Fixed Test Slot",
            slot_type="fixed",
            match_scope="whole_subsection",
            required=True,
            flag_prominently=False,
            template_version="test",
        )
        PolicyLanguageVariant.objects.create(
            slot=cls.fixed_slot,
            canonical_text="This is fixed canonical text with no blanks.",
        )

        cls.placeholder_slot = PolicyLanguageSlot.objects.create(
            slot_key="TEST-PLACEHOLDER",
            name="Placeholder Test Slot",
            slot_type="fixed_with_placeholders",
            match_scope="whole_subsection",
            required=False,
            flag_prominently=True,
            template_version="test",
        )
        PolicyLanguageVariant.objects.create(
            slot=cls.placeholder_slot,
            canonical_text="Insert your {amount} here for the {program} program.",
        )

        cls.span_slot = PolicyLanguageSlot.objects.create(
            slot_key="TEST-SPAN",
            name="Span Test Slot",
            slot_type="fixed",
            match_scope="span_within_subsection",
            required=False,
            flag_prominently=False,
            template_version="test",
        )
        PolicyLanguageVariant.objects.create(
            slot=cls.span_slot,
            canonical_text="This exact fragment must appear somewhere in the body.",
        )

    def test_exact_match_is_intact(self):
        status, slot = detect_policy_language_status(
            "Fixed Test Slot", "This is fixed canonical text with no blanks."
        )
        self.assertEqual(status, "intact")
        self.assertEqual(slot, self.fixed_slot)

    def test_cosmetic_whitespace_difference_is_still_intact(self):
        status, slot = detect_policy_language_status(
            "Fixed Test Slot", "This is fixed canonical   text\nwith no blanks."
        )
        self.assertEqual(status, "intact")

    def test_substantive_edit_is_may_be_altered(self):
        status, slot = detect_policy_language_status(
            "Fixed Test Slot", "This is completely different rewritten content."
        )
        self.assertEqual(status, "may_be_altered")
        self.assertEqual(slot, self.fixed_slot)

    def test_unrelated_name_and_content_is_none(self):
        status, slot = detect_policy_language_status(
            "Some Unrelated Subsection", "Totally unrelated program-specific content."
        )
        self.assertEqual(status, "none")
        self.assertIsNone(slot)

    def test_no_name_is_none(self):
        status, slot = detect_policy_language_status("", "Some content.")
        self.assertEqual(status, "none")
        self.assertIsNone(slot)

    def test_placeholder_spans_are_ignored(self):
        status, slot = detect_policy_language_status(
            "Placeholder Test Slot",
            "Insert your $500,000 here for the Community Health program.",
        )
        self.assertEqual(status, "intact")
        self.assertEqual(slot, self.placeholder_slot)

    def test_extra_content_beyond_canonical_is_altered_for_whole_subsection(self):
        status, slot = detect_policy_language_status(
            "Fixed Test Slot",
            "This is fixed canonical text with no blanks. Plus some extra sentence.",
        )
        self.assertEqual(status, "may_be_altered")

    def test_span_scoped_slot_matches_as_fragment_regardless_of_name(self):
        status, slot = detect_policy_language_status(
            "Totally Different Heading",
            "Intro text. This exact fragment must appear somewhere in the body. Trailing text.",
        )
        self.assertEqual(status, "intact")
        self.assertEqual(slot, self.span_slot)

    def test_span_scoped_slot_no_match_is_none_not_altered(self):
        # A subsection that simply doesn't contain the fragment shouldn't be
        # penalized - only whole_subsection slots get 'may_be_altered' for a
        # name match with no content match.
        status, slot = detect_policy_language_status(
            "Some Other Heading", "Nothing related here at all."
        )
        self.assertEqual(status, "none")


class SupersessionVersioningTests(TestCase):
    def test_two_current_rows_for_same_slot_key_violates_constraint(self):
        PolicyLanguageSlot.objects.create(
            slot_key="TEST-DUP", name="A", slot_type="fixed", template_version="v1"
        )
        with self.assertRaises(IntegrityError):
            PolicyLanguageSlot.objects.create(
                slot_key="TEST-DUP", name="B", slot_type="fixed", template_version="v2"
            )

    def test_matches_prior_version_returns_current_slot_not_stale_one(self):
        old = PolicyLanguageSlot.objects.create(
            slot_key="TEST-VERSIONED",
            name="Versioned Slot",
            slot_type="fixed",
            template_version="v1",
        )
        PolicyLanguageVariant.objects.create(slot=old, canonical_text="Old canonical text.")

        old.is_current = False
        old.save(update_fields=["is_current"])
        new = PolicyLanguageSlot.objects.create(
            slot_key="TEST-VERSIONED",
            name="Versioned Slot",
            slot_type="fixed",
            template_version="v2",
        )
        PolicyLanguageVariant.objects.create(slot=new, canonical_text="New canonical text.")
        old.superseded_by = new
        old.save(update_fields=["superseded_by"])

        status, slot = detect_policy_language_status("Versioned Slot", "Old canonical text.")
        self.assertEqual(status, "matches_prior_version")
        # The current revision is returned, not the stale row that matched.
        self.assertEqual(slot, new)

    def test_span_scoped_prior_version_also_returns_current_slot(self):
        # Regression test: span-scoped slots must check all versions of a
        # slot_key together (current first), not one version in isolation -
        # otherwise a superseded row (always created before its replacement)
        # could out-race the current row and get returned instead.
        old = PolicyLanguageSlot.objects.create(
            slot_key="TEST-SPAN-VERSIONED",
            name="Span Versioned Slot",
            slot_type="fixed",
            match_scope="span_within_subsection",
            template_version="v1",
        )
        PolicyLanguageVariant.objects.create(slot=old, canonical_text="Old span fragment text.")
        old.is_current = False
        old.save(update_fields=["is_current"])
        new = PolicyLanguageSlot.objects.create(
            slot_key="TEST-SPAN-VERSIONED",
            name="Span Versioned Slot",
            slot_type="fixed",
            match_scope="span_within_subsection",
            template_version="v2",
        )
        PolicyLanguageVariant.objects.create(slot=new, canonical_text="New span fragment text.")
        old.superseded_by = new
        old.save(update_fields=["superseded_by"])

        status, slot = detect_policy_language_status(
            "Any Heading", "Intro. Old span fragment text. Outro."
        )
        self.assertEqual(status, "matches_prior_version")
        self.assertEqual(slot, new)

    def test_span_scoped_current_version_match_is_intact_not_stale_match(self):
        old = PolicyLanguageSlot.objects.create(
            slot_key="TEST-SPAN-CURRENT",
            name="Span Current Slot",
            slot_type="fixed",
            match_scope="span_within_subsection",
            template_version="v1",
        )
        PolicyLanguageVariant.objects.create(slot=old, canonical_text="Old span fragment text.")
        old.is_current = False
        old.save(update_fields=["is_current"])
        new = PolicyLanguageSlot.objects.create(
            slot_key="TEST-SPAN-CURRENT",
            name="Span Current Slot",
            slot_type="fixed",
            match_scope="span_within_subsection",
            template_version="v2",
        )
        PolicyLanguageVariant.objects.create(slot=new, canonical_text="New span fragment text.")
        old.superseded_by = new
        old.save(update_fields=["superseded_by"])

        status, slot = detect_policy_language_status(
            "Any Heading", "Intro. New span fragment text. Outro."
        )
        self.assertEqual(status, "intact")
        self.assertEqual(slot, new)

    def test_whole_subsection_aligns_by_any_versions_name_after_rename(self):
        # Regression test: a slot can be renamed across a supersession even
        # when its canonical text doesn't change. Alignment must check every
        # version's name, not just whichever version happens to be first in
        # the (unordered) candidate list - otherwise a subsection correctly
        # retitled to the new name fails to align at all and falls through
        # to "none", silently treating real canonical text as ordinary
        # content.
        old = PolicyLanguageSlot.objects.create(
            slot_key="TEST-RENAMED",
            name="Old Heading",
            slot_type="fixed",
            template_version="v1",
        )
        PolicyLanguageVariant.objects.create(slot=old, canonical_text="Canonical text.")
        old.is_current = False
        old.save(update_fields=["is_current"])
        new = PolicyLanguageSlot.objects.create(
            slot_key="TEST-RENAMED",
            name="New Heading",
            slot_type="fixed",
            template_version="v2",
        )
        PolicyLanguageVariant.objects.create(slot=new, canonical_text="Canonical text.")
        old.superseded_by = new
        old.save(update_fields=["superseded_by"])

        status, slot = detect_policy_language_status("New Heading", "Canonical text.")
        self.assertEqual(status, "intact")
        self.assertEqual(slot, new)


class MultipleSlotKeysShareNameTests(TestCase):
    """Two distinct slot_keys can legitimately share one real-world heading
    - e.g. two mutually-exclusive versions of a "Cost sharing" section.
    Alignment must try every slot_key matching that name, not just whichever
    happens to be first in dict iteration order."""

    @classmethod
    def setUpTestData(cls):
        cls.slot_a = PolicyLanguageSlot.objects.create(
            slot_key="TEST-SHARED-A", name="Cost sharing", slot_type="fixed",
            template_version="v1",
        )
        PolicyLanguageVariant.objects.create(
            slot=cls.slot_a, canonical_text="This program has no cost sharing requirement."
        )

        cls.slot_b = PolicyLanguageSlot.objects.create(
            slot_key="TEST-SHARED-B", name="Cost sharing", slot_type="fixed",
            template_version="v1",
        )
        PolicyLanguageVariant.objects.create(
            slot=cls.slot_b, canonical_text="This program requires you to contribute 15%."
        )

    def test_content_matching_second_slot_is_intact_not_altered(self):
        # A naive "stop at the first name match" loop would find TEST-SHARED-A
        # first (it doesn't match this content) and incorrectly report
        # may_be_altered instead of trying TEST-SHARED-B, which does match.
        status, slot = detect_policy_language_status(
            "Cost sharing", "This program requires you to contribute 15%."
        )
        self.assertEqual(status, "intact")
        self.assertEqual(slot, self.slot_b)

    def test_content_matching_first_slot_is_still_intact(self):
        status, slot = detect_policy_language_status(
            "Cost sharing", "This program has no cost sharing requirement."
        )
        self.assertEqual(status, "intact")
        self.assertEqual(slot, self.slot_a)

    def test_content_matching_neither_slot_is_may_be_altered(self):
        status, slot = detect_policy_language_status(
            "Cost sharing", "Some entirely different, unrecognized wording."
        )
        self.assertEqual(status, "may_be_altered")
        self.assertIn(slot, (self.slot_a, self.slot_b))


class MissingRequiredSlotsTests(TestCase):
    def test_required_slot_with_no_matching_subsection_is_missing(self):
        required_slot = PolicyLanguageSlot.objects.create(
            slot_key="TEST-REQUIRED", name="Required Slot", slot_type="fixed",
            required=True, template_version="v1",
        )
        PolicyLanguageVariant.objects.create(slot=required_slot, canonical_text="Required text.")

        nofo = Nofo.objects.create(
            title="Missing slot test", short_name="missing-slot-test",
            number="TEST-MISSING-001", opdiv="TEST", group="bloom", status="draft",
        )
        section = Section.objects.create(nofo=nofo, name="Section", html_id="section", order=1)
        Subsection.objects.create(
            section=section, name="Something Else", tag="h4", body="Unrelated.", order=1
        )

        missing = get_missing_required_slots(nofo)
        self.assertIn(required_slot, missing)

    def test_matched_required_slot_is_not_missing(self):
        required_slot = PolicyLanguageSlot.objects.create(
            slot_key="TEST-REQUIRED-2", name="Required Slot 2", slot_type="fixed",
            required=True, template_version="v1",
        )
        PolicyLanguageVariant.objects.create(slot=required_slot, canonical_text="Required text.")

        nofo = Nofo.objects.create(
            title="Matched slot test", short_name="matched-slot-test",
            number="TEST-MATCHED-001", opdiv="TEST", group="bloom", status="draft",
        )
        section = Section.objects.create(nofo=nofo, name="Section", html_id="section", order=1)
        Subsection.objects.create(
            section=section, name="Required Slot 2", tag="h4", body="Required text.", order=1,
            policy_language_status="intact", policy_language_slot=required_slot,
        )

        missing = get_missing_required_slots(nofo)
        self.assertNotIn(required_slot, missing)


class PolicyLanguageExportNoteTests(TestCase):
    def test_intact_and_none_have_no_note(self):
        nofo = Nofo.objects.create(
            title="Note test", short_name="note-test", number="TEST-NOTE-001",
            opdiv="TEST", group="bloom", status="draft",
        )
        section = Section.objects.create(nofo=nofo, name="Section", html_id="section", order=1)
        intact_sub = Subsection.objects.create(
            section=section, name="A", tag="h4", body="x", order=1,
            policy_language_status="intact",
        )
        none_sub = Subsection.objects.create(
            section=section, name="B", tag="h4", body="y", order=2,
            policy_language_status="none",
        )
        self.assertIsNone(get_policy_language_export_note(intact_sub))
        self.assertIsNone(get_policy_language_export_note(none_sub))

    def test_routine_flag_note_for_non_prominent_slot(self):
        slot = PolicyLanguageSlot.objects.create(
            slot_key="TEST-ROUTINE", name="Routine Slot", slot_type="fixed",
            flag_prominently=False, template_version="v1",
        )
        nofo = Nofo.objects.create(
            title="Routine note test", short_name="routine-note-test",
            number="TEST-ROUTINE-001", opdiv="TEST", group="bloom", status="draft",
        )
        section = Section.objects.create(nofo=nofo, name="Section", html_id="section", order=1)
        sub = Subsection.objects.create(
            section=section, name="Routine Slot", tag="h4", body="altered", order=1,
            policy_language_status="may_be_altered", policy_language_slot=slot,
        )
        note = get_policy_language_export_note(sub)
        self.assertIn("REVIEW:", note)
        self.assertNotIn("PRIORITY REVIEW", note)
        self.assertIn("Routine Slot", note)

    def test_elevated_note_for_prominent_slot(self):
        slot = PolicyLanguageSlot.objects.create(
            slot_key="TEST-PROMINENT",
            name="Prominent Slot",
            slot_type="fixed_with_placeholders", flag_prominently=True, template_version="v1",
        )
        nofo = Nofo.objects.create(
            title="Elevated note test", short_name="elevated-note-test",
            number="TEST-ELEVATED-001", opdiv="TEST", group="bloom", status="draft",
        )
        section = Section.objects.create(nofo=nofo, name="Section", html_id="section", order=1)
        sub = Subsection.objects.create(
            section=section, name="Prominent Slot", tag="h4", body="altered", order=1,
            policy_language_status="may_be_altered", policy_language_slot=slot,
        )
        note = get_policy_language_export_note(sub)
        self.assertIn("PRIORITY REVIEW", note)


class PolicyLanguageExportSummaryTests(TestCase):
    def test_summary_counts_flags_and_missing_slots(self):
        required_slot = PolicyLanguageSlot.objects.create(
            slot_key="TEST-SUMMARY-REQ", name="Required Summary Slot",
            slot_type="fixed", required=True, template_version="v1",
        )
        PolicyLanguageVariant.objects.create(slot=required_slot, canonical_text="text")

        matched_slot = PolicyLanguageSlot.objects.create(
            slot_key="TEST-SUMMARY-MATCHED", name="Matched Slot", slot_type="fixed",
            template_version="v1",
        )

        nofo = Nofo.objects.create(
            title="Summary test", short_name="summary-test", number="TEST-SUMMARY-001",
            opdiv="TEST", group="bloom", status="draft",
        )
        section = Section.objects.create(nofo=nofo, name="Section", html_id="section", order=1)
        Subsection.objects.create(
            section=section, name="Intact", tag="h4", body="x", order=1,
            policy_language_status="intact", policy_language_slot=matched_slot,
        )
        flagged_sub = Subsection.objects.create(
            section=section, name="Flagged", tag="h4", body="y", order=2,
            policy_language_status="may_be_altered", policy_language_slot=matched_slot,
        )
        Subsection.objects.create(
            section=section, name="Ordinary", tag="h4", body="z", order=3,
            policy_language_status="none",
        )

        summary = get_policy_language_export_summary(nofo)
        self.assertEqual(summary["stripped_count"], 1)
        self.assertEqual(summary["flagged"], [flagged_sub])
        self.assertIn(required_slot, summary["missing_slots"])


SAMPLE_SLOTS = [
    {
        "slot_key": "TEST-SAMPLE-001",
        "name": "Sample Slot One",
        "slot_type": "fixed",
        "required": True,
        "flag_prominently": False,
        "variants": [{"canonical_text": "Sample canonical text for slot one."}],
    },
    {
        "slot_key": "TEST-SAMPLE-002",
        "name": "Sample Slot Two",
        "slot_type": "fixed",
        "required": False,
        "flag_prominently": False,
        "variants": [{"canonical_text": "Sample canonical text for slot two."}],
    },
]


@patch(
    "nofos.management.commands.ingest_canonical_policy_language.SLOTS", SAMPLE_SLOTS
)
@patch(
    "nofos.management.commands.ingest_canonical_policy_language.TEMPLATE_VERSION",
    "TEST-SAMPLE-V1",
)
class IngestCanonicalPolicyLanguageCommandTests(TestCase):
    """Exercises the ingest command's own behavior (creation, idempotency,
    dry-run, supersession, in-place version updates) against a small
    synthetic sample data set - never the real production canonical text -
    so this test suite carries no dependency on what the (separately
    published, possibly still-empty) canonical data module contains."""

    def test_first_run_creates_all_slots(self):
        call_command("ingest_canonical_policy_language")
        self.assertEqual(
            PolicyLanguageSlot.objects.filter(is_current=True).count(),
            len(SAMPLE_SLOTS),
        )

    def test_rerun_is_idempotent(self):
        call_command("ingest_canonical_policy_language")
        count_after_first = PolicyLanguageSlot.objects.count()

        call_command("ingest_canonical_policy_language")
        self.assertEqual(PolicyLanguageSlot.objects.count(), count_after_first)

    def test_dry_run_writes_nothing(self):
        call_command("ingest_canonical_policy_language", "--dry-run")
        self.assertEqual(PolicyLanguageSlot.objects.count(), 0)

    def test_revised_data_supersedes_rather_than_edits_in_place(self):
        call_command("ingest_canonical_policy_language")
        original = PolicyLanguageSlot.objects.get(
            slot_key="TEST-SAMPLE-001", is_current=True
        )
        original_id = original.id

        revised_slots = [
            {
                "slot_key": "TEST-SAMPLE-001",
                "name": original.name,
                "slot_type": "fixed",
                "required": True,
                "flag_prominently": False,
                "variants": [
                    {"canonical_text": "A deliberately revised version of the text."}
                ],
            }
        ]

        with patch(
            "nofos.management.commands.ingest_canonical_policy_language.SLOTS",
            revised_slots,
        ), patch(
            "nofos.management.commands.ingest_canonical_policy_language.TEMPLATE_VERSION",
            "TEST-REVISED",
        ):
            call_command("ingest_canonical_policy_language")

        original.refresh_from_db()
        self.assertFalse(original.is_current)
        self.assertIsNotNone(original.superseded_by_id)

        new_current = PolicyLanguageSlot.objects.get(
            slot_key="TEST-SAMPLE-001", is_current=True
        )
        self.assertNotEqual(new_current.id, original_id)
        self.assertEqual(new_current.id, original.superseded_by_id)
        self.assertEqual(
            new_current.variants.first().canonical_text,
            "A deliberately revised version of the text.",
        )

    def test_version_only_change_updates_in_place_without_superseding(self):
        call_command("ingest_canonical_policy_language")
        original = PolicyLanguageSlot.objects.get(
            slot_key="TEST-SAMPLE-001", is_current=True
        )
        original_id = original.id
        original_variant_id = original.variants.first().id

        same_slots = [
            {
                "slot_key": "TEST-SAMPLE-001",
                "name": original.name,
                "slot_type": original.slot_type,
                "required": original.required,
                "flag_prominently": original.flag_prominently,
                "variants": [
                    {"canonical_text": original.variants.first().canonical_text}
                ],
            }
        ]

        with patch(
            "nofos.management.commands.ingest_canonical_policy_language.SLOTS",
            same_slots,
        ), patch(
            "nofos.management.commands.ingest_canonical_policy_language.TEMPLATE_VERSION",
            "TEST-NEW-VERSION-LABEL",
        ):
            call_command("ingest_canonical_policy_language")

        original.refresh_from_db()
        self.assertTrue(original.is_current)
        self.assertIsNone(original.superseded_by_id)
        self.assertEqual(original.id, original_id)
        self.assertEqual(original.template_version, "TEST-NEW-VERSION-LABEL")
        self.assertEqual(original.variants.first().id, original_variant_id)
        self.assertEqual(
            PolicyLanguageSlot.objects.filter(slot_key="TEST-SAMPLE-001").count(), 1
        )
