from unittest import TestCase

from composer.conditional.conditional_questions import (
    ConditionalQuestion,
    ConditionalQuestionRegistry,
)


class DummySubsection:
    """
    Minimal stand-in for your real Subsection model.
    Only needs a `.name` attribute for these tests.
    """

    def __init__(self, name: str | None):
        self.name = name


class ConditionalQuestionTests(TestCase):
    def test_matches_subsection_name_is_case_insensitive_and_trimmed(self):
        q = ConditionalQuestion(
            key="letters_of_support",
            label="Are letters of support required?",
            subsections=["Letters of support"],
            page=1,
        )

        # Matching subsection names
        self.assertTrue(q.matches_subsection_name("Letters of support"))
        self.assertTrue(q.matches_subsection_name("letters of support"))
        self.assertTrue(q.matches_subsection_name("  Letters of support  "))

        # Non-matching
        self.assertFalse(q.matches_subsection_name("Letter of support"))
        self.assertFalse(q.matches_subsection_name(""))
        self.assertFalse(q.matches_subsection_name(None))


class ConditionalQuestionRegistryTests(TestCase):
    def setUp(self):
        # Use the real JSON file via the registry helper
        self.registry = ConditionalQuestionRegistry.load_default()

    def test_registry_is_populated_from_default_json(self):
        # Sanity: must contain at least these keys (adjust as needed)
        expected_keys = {
            "cost_sharing",
            "maintenance_of_effort",
            "letters_of_support",
            "intergovernmental_review",
            "cooperative_agreement",
        }
        self.assertTrue(expected_keys.issubset(self.registry.keys()))

    def test_related_subsections_filters_by_subsections(self):
        subsections = [
            DummySubsection("Cost sharing"),  # Match
            DummySubsection("Method 1: Start with the federal share"),  # Match
            DummySubsection("Some other section"),  # Non-match
            DummySubsection("COST-SHARING WAIVER"),  # case-insensitive match
            DummySubsection(None),  # should be ignored safely
        ]

        related = self.registry.related_subsections("cost_sharing", subsections)
        related_names = {s.name for s in related}

        # Only subsections whose name is in the JSON config should appear
        self.assertEqual(
            related_names,
            {
                "Cost sharing",
                "Method 1: Start with the federal share",
                "COST-SHARING WAIVER",
            },
        )

    def test_related_subsections_for_question_with_single_subsection_name(self):
        subsections = [
            DummySubsection("Maintenance of effort"),
            DummySubsection("maintenance of effort"),  # lower case
            DummySubsection("Other thing"),
        ]

        related = self.registry.related_subsections(
            "maintenance_of_effort", subsections
        )
        related_names = {s.name for s in related}

        # Note that the same name twice will match twice, we don't de-dupe
        self.assertEqual(
            related_names,
            {"Maintenance of effort", "maintenance of effort"},
        )
