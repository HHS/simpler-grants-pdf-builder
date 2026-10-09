"""Real-worker characterization of supported drafts and their limitations."""

import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from nofos.pdf_readability_worker import analyze
from nofos.tests_nofos.draft_pdf_fixtures import PROSE, WRITER_INSTRUCTION, draft_pdf


class DraftPdfReadabilityTests(SimpleTestCase):
    def report(self, blocks=PROSE, **options):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic-draft.pdf"
            path.write_bytes(draft_pdf(blocks, **options))
            return analyze(path, 150)

    def assert_reference_metrics(self, report):
        baseline = self.report()
        self.assertEqual(report["scope"], baseline["scope"])
        for metric in (
            "word_count",
            "words_per_sentence",
            "sentences_per_paragraph",
            "flesch_kincaid_grade_level",
            "passive_sentence_percentage",
        ):
            self.assertEqual(report["metrics"][metric], baseline["metrics"][metric])

    def test_wrapped_paragraph_keeps_reference_metrics(self):
        report = self.report(
            (
                ("P", "The agency funds local work.\nTeams can send a clear plan."),
                PROSE[1],
            )
        )
        self.assert_reference_metrics(report)

    def test_sentence_continued_across_pages_keeps_reference_metrics(self):
        report = self.report(
            (
                ("P", "The agency funds local\fwork. Teams can send a clear plan."),
                PROSE[1],
            )
        )
        self.assertEqual(report["pages_total"], 2)
        self.assertEqual(report["pages_analyzed"], 2)
        self.assert_reference_metrics(report)

    def test_list_body_continued_across_pages_keeps_reference_metrics(self):
        report = self.report(
            (
                ("LBody", "The agency funds local\fwork. Teams can send a clear plan."),
                ("LBody", PROSE[1][1]),
            )
        )
        self.assertEqual(report["pages_total"], 2)
        self.assert_reference_metrics(report)

    def test_table_cell_continued_across_pages_keeps_reference_metrics(self):
        report = self.report(
            (
                ("TD", "The agency funds local\fwork. Teams can send a clear plan."),
                ("TD", PROSE[1][1]),
            )
        )
        self.assertEqual(report["pages_total"], 2)
        self.assert_reference_metrics(report)

    def test_tagged_reference_denominators(self):
        report = self.report()
        self.assertEqual(report["profile"], "tagged")
        self.assertEqual(report["scope"]["sentence_word_count"], 17)
        self.assertEqual(report["scope"]["complete_sentence_count"], 3)
        # Six identifier-heading tokens plus the 17 prose words.
        self.assertEqual(report["metrics"]["word_count"]["value"], 23)
        self.assertAlmostEqual(
            report["metrics"]["words_per_sentence"]["value"], 17 / 3, places=2
        )
        self.assertEqual(report["metrics"]["sentences_per_paragraph"]["value"], 1.5)
        self.assertAlmostEqual(
            report["metrics"]["passive_sentence_percentage"]["value"], 100 / 3, places=2
        )
        # Manually checked 21 syllables in 17 words: FK = 1.19588..., rounded.
        expected_grade = 0.39 * (17 / 3) + 11.8 * (21 / 17) - 15.59
        self.assertAlmostEqual(
            report["metrics"]["flesch_kincaid_grade_level"]["value"],
            expected_grade,
            places=2,
        )

    def test_ordinary_font_change_preserves_all_five_measures(self):
        baseline = self.report()
        altered = self.report(font_size=10)
        for metric in (
            "word_count",
            "words_per_sentence",
            "sentences_per_paragraph",
            "flesch_kincaid_grade_level",
            "passive_sentence_percentage",
        ):
            self.assertEqual(baseline["metrics"][metric], altered["metrics"][metric])

    def test_writer_notes_are_not_silently_removed_from_pdf(self):
        baseline = self.report()
        instructions = self.report((*PROSE, ("P", WRITER_INSTRUCTION)))
        self.assertEqual(
            instructions["scope"]["recovered_word_count"]
            - baseline["scope"]["recovered_word_count"],
            10,
        )
        self.assertEqual(instructions["scope"]["sentence_word_count"], 27)
        self.assertEqual(instructions["scope"]["complete_sentence_count"], 4)

    def test_table_cell_instructions_are_also_measured(self):
        report = self.report((*PROSE, ("TD", WRITER_INSTRUCTION)))
        self.assertEqual(report["scope"]["recovered_word_count"], 33)
        self.assertEqual(report["scope"]["sentence_word_count"], 27)
        self.assertEqual(report["scope"]["complete_sentence_count"], 4)

    def test_sparse_draft_does_not_receive_a_grade_or_passive_score(self):
        report = self.report((("P", "[Insert program description]"),))
        self.assertEqual(report["scope"]["complete_sentence_count"], 0)
        self.assertEqual(report["metrics"]["word_count"]["value"], 9)
        for metric in (
            "words_per_sentence",
            "flesch_kincaid_grade_level",
            "passive_sentence_percentage",
        ):
            self.assertIsNone(report["metrics"][metric]["value"])

    def test_placeholder_fragments_do_not_become_complete_sentences(self):
        baseline = self.report()
        placeholder = self.report((*PROSE, ("P", "[Insert program description]")))
        self.assertGreater(
            placeholder["scope"]["recovered_word_count"],
            baseline["scope"]["recovered_word_count"],
        )
        self.assertEqual(placeholder["scope"]["sentence_word_count"], 17)
        self.assertEqual(placeholder["scope"]["complete_sentence_count"], 3)

    def test_untagged_draft_stays_an_explicit_low_reliability_estimate(self):
        report = self.report(tagged=False)
        self.assertEqual(report["profile"], "generic")
        self.assertEqual(report["reliability"], "low")
        self.assertTrue(report["warnings"])
