from django.test import TestCase

from ..models import Nofo, Section, Subsection
from ..nofo import compare_nofos, compare_nofos_metadata, html_diff


class TestHtmlDiff(TestCase):

    def test_basic_text_change(self):
        original = "Groundhog Day!"
        new = "Valentines Day!"
        expected = "<del>Groundhog</del><ins>Valentines</ins> Day!"
        self.assertEqual(html_diff(original, new), expected)

    def test_whitespace_only_change(self):
        original = "Groundhog      Day!"
        new = "Groundhog Day!"
        self.assertIsNone(html_diff(original, new))  # Whitespace only = None

    def test_identical_strings(self):
        original = "Groundhog Day!"
        new = "Groundhog Day!"
        self.assertIsNone(html_diff(original, new))  # No changes = None

    def test_text_added(self):
        original = "Groundhog"
        new = "Groundhog Day"
        expected = "Groundhog<ins> Day</ins>"
        self.assertEqual(html_diff(original, new), expected)

    def test_text_removed(self):
        original = "Groundhog Day"
        new = "Day"
        expected = "<del>Groundhog </del>Day"
        self.assertEqual(html_diff(original, new), expected)

    def test_replace_with_partial_whitespace(self):
        original = "Groundhog Day!"
        new = "Groundhog Day! (1993)"
        expected = "Groundhog Day!<ins> (1993)</ins>"
        self.assertEqual(html_diff(original, new), expected)

    def test_empty_input(self):
        self.assertIsNone(html_diff("", ""))  # No changes
        self.assertEqual(html_diff("", "Groundhog"), "<ins>Groundhog</ins>")  # insert
        self.assertEqual(html_diff("Groundhog", ""), "<del>Groundhog</del>")  # delete


class TestCompareNofos(TestCase):
    def setUp(self):
        """
        Sets up two NOFO objects (old and new) with sections and subsections.
        """
        self.old_nofo = Nofo.objects.create(title="Old NOFO", opdiv="Test OpDiv")
        self.new_nofo = Nofo.objects.create(title="New NOFO", opdiv="Test OpDiv")

        self.old_section = Section.objects.create(
            name="Step 1",
            nofo=self.old_nofo,
            order=1,
            html_id="step-1",
        )
        self.new_section = Section.objects.create(
            name="Step 1",
            nofo=self.new_nofo,
            order=1,
            html_id="step-1",
        )

        # Modify the first (default) subsection instead of creating a new one
        # These two subsections will match
        self.old_sub_1 = Subsection.objects.create(
            name="Budget Requirements",
            body="Budget must not exceed $100K.",
            section=self.old_section,
            order=1,
            tag="h3",
        )

        self.new_sub_1 = Subsection.objects.create(
            name="Budget Requirements",
            body="Budget must not exceed $100K.",
            section=self.new_section,
            order=1,
            tag="h3",
        )

        # Changed subsection (no name, different content)
        self.old_sub_2 = Subsection.objects.create(
            name="",
            body="Need help? Visit contacts and support",
            section=self.old_section,
            order=3,
            tag="h3",
        )
        self.new_sub_2 = Subsection.objects.create(
            name="",
            body="Go to 'Contacts and Support",
            section=self.new_section,
            order=3,
            tag="h3",
        )

        # Changed subsection (same name, different content)
        self.old_sub_2 = Subsection.objects.create(
            name="Application Process",
            body="Submit before Jan 1.",
            section=self.old_section,
            order=4,
            tag="h3",
        )
        self.new_sub_2 = Subsection.objects.create(
            name="Application Process",
            body="Submit before Feb 1.",
            section=self.new_section,
            order=4,
            tag="h3",
        )

        # Added subsection (exists only in new NOFO)
        self.new_sub_3 = Subsection.objects.create(
            name="New NOFO Funding Guidelines",
            body="Follow these new rules.",
            section=self.new_section,
            order=5,
            tag="h3",
        )

        # Deleted subsection (exists only in old NOFO)
        self.old_sub_4 = Subsection.objects.create(
            name="Old NOFO Fee Requirements",
            body="Processing fee is $50.",
            section=self.old_section,
            order=5,
            tag="h3",
        )

    def test_compare_nofos(self):
        """
        Tests the compare_nofos function, ensuring it correctly identifies matches, updates, additions, and deletions.
        """
        result = compare_nofos(self.new_nofo, self.old_nofo)

        # Ensure the result is structured correctly
        self.assertEqual(len(result), 1)  # Only one section should be in the diff
        self.assertEqual(result[0]["name"], "Step 1")

        subsections = result[0]["subsections"]
        self.assertEqual(len(subsections), 5)

        # Match test
        subsection_match = subsections[0]
        self.assertEqual(subsection_match["status"], "MATCH")
        self.assertEqual(subsection_match["name"], "Budget Requirements")
        self.assertEqual(subsection_match["value"], "Budget must not exceed $100K.")

        # Update test (unnamed subsection)
        subsection_update = subsections[1]
        self.assertEqual(subsection_update["status"], "UPDATE")
        self.assertEqual(subsection_update["name"], "(#3)")
        self.assertEqual(subsection_update["value"], "Go to 'Contacts and Support")
        self.assertIn(
            "<del>Need</del><ins>Go</ins> <del>help?</del><ins>to</ins> <del>Visit contacts</del><ins>'Contacts</ins> and <del>support</del><ins>Support</ins>",
            subsection_update["diff"],
        )

        # Update test 2 (regular subsection)
        subsection_update = subsections[2]
        self.assertEqual(subsection_update["status"], "UPDATE")
        self.assertEqual(subsection_update["name"], "Application Process")
        self.assertEqual(subsection_update["value"], "Submit before Feb 1.")
        self.assertIn(
            "Submit before <del>Jan</del><ins>Feb</ins> 1.", subsection_update["diff"]
        )

        # Addition test
        subsection_add = subsections[3]
        self.assertEqual(subsection_add["status"], "ADD")
        self.assertEqual(subsection_add["name"], "New NOFO Funding Guidelines")
        self.assertEqual(subsection_add["value"], "Follow these new rules.")

        # Deletion test
        subsection_delete = subsections[4]
        self.assertEqual(subsection_delete["name"], "Old NOFO Fee Requirements")
        self.assertEqual(subsection_delete["value"], "Processing fee is $50.")
        self.assertIn("<del>Processing fee is $50.</del>", subsection_delete["diff"])


class TestCompareNofosMetadata(TestCase):
    def setUp(self):
        """
        Sets up two NOFO objects (old and new) with different metadata fields.
        """
        self.old_nofo = Nofo.objects.create(
            title="Groundhog Training Grant",
            number="GHOG-101",
            opdiv="National Oceanic and Atmospheric Administration",
            agency="Climate and Weather Division",
            subagency="Department of Guessing Groundhogs (DGG)",
            subagency2="Action Group for Diverse Prognosticators (AGDP)",
            application_deadline="",
            tagline="Make Groundhogs Great Again",
        )

        self.new_nofo = Nofo.objects.create(
            title="Groundhog Training Grant",  # MATCH
            number="GHOG-101",  # MATCH
            opdiv="National Oceanic and Atmospheric Administration",  # MATCH
            agency="Climate and Weather Division",  # MATCH
            subagency="Department of Groundhog Excellence (DOGE)",  # UPDATE
            subagency2="",  # DELETE
            application_deadline="February 2, 2026",  # ADD
            tagline="Make Groundhogs Great Again",  # MATCH
        )

    def test_compare_nofos_metadata(self):
        """
        Tests the compare_nofos_metadata function, ensuring it correctly identifies matches, updates, additions, and deletions.
        """
        nofo_comparison_metadata = compare_nofos_metadata(self.new_nofo, self.old_nofo)

        # Ensure 8 attributes changes are detected
        self.assertEqual(len(nofo_comparison_metadata), 8)
        # 3 attributes are not matched (update, add, or delete)
        non_matches_results = [
            item for item in nofo_comparison_metadata if item["status"] != "MATCH"
        ]
        self.assertEqual(len(non_matches_results), 3)

        # Match tests
        matched_names = [
            "NOFO title",
            "Opportunity number",
            "Operating Division",
            "Agency",
            "Tagline",
        ]
        for item in nofo_comparison_metadata:
            if item["name"] in matched_names:
                self.assertEqual(item["status"], "MATCH")
                self.assertNotIn("diff", item)

        # Update test (subagency changed)
        subagency_update = nofo_comparison_metadata[4]
        self.assertEqual(subagency_update["status"], "UPDATE")
        self.assertEqual(
            subagency_update["value"], "Department of Groundhog Excellence (DOGE)"
        )
        self.assertIn(
            "Department of <del>Guessing</del><ins>Groundhog</ins> <del>Groundhogs</del><ins>Excellence</ins> (<del>DGG</del><ins>DOGE</ins>)",
            subagency_update["diff"],
        )

        # Delete test (subagency2 removed)
        subagency2_delete = nofo_comparison_metadata[5]
        self.assertEqual(subagency2_delete["status"], "DELETE")
        self.assertEqual(subagency2_delete["value"], "")
        self.assertIn(
            "<del>Action Group for Diverse Prognosticators (AGDP)</del>",
            subagency2_delete["diff"],
        )

        # Addition test (application deadline added)
        application_deadline_add = nofo_comparison_metadata[6]
        self.assertEqual(application_deadline_add["status"], "ADD")
        self.assertEqual(application_deadline_add["value"], "February 2, 2026")
        self.assertIn("<ins>February 2, 2026</ins>", application_deadline_add["diff"])
