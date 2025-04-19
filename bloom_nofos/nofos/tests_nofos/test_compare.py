from copy import deepcopy

from django.test import TestCase

from ..models import Nofo, Section, Subsection
from ..nofo_compare import (
    apply_comparison_types,
    compare_nofos,
    compare_nofos_metadata,
    html_diff,
    merge_renamed_subsections,
)


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


class MergeRenamedSubsectionsTests(TestCase):
    def test_exact_body_match_renamed_title(self):
        input_data = [
            {
                "status": "ADD",
                "name": "Overview",
                "old_value": "",
                "new_value": "This is some content.",
            },
            {
                "status": "DELETE",
                "name": "Summary",
                "old_value": "This is some content.",
                "new_value": "",
            },
        ]
        result = merge_renamed_subsections(input_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["status"], "UPDATE")
        self.assertIn("<ins>Overview</ins>", result[0]["name"])
        self.assertIn("<del>Summary</del>", result[0]["name"])
        self.assertEqual(result[0]["diff"], None)

    def test_renamed_title_and_changed_body(self):
        input_data = [
            {
                "status": "DELETE",
                "name": "Overview",
                "old_value": "Old content.",
                "new_value": "",
            },
            {
                "status": "ADD",
                "name": "Summary",
                "old_value": "",
                "new_value": "New content.",
            },
        ]
        result = merge_renamed_subsections(input_data)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["status"], "DELETE")
        self.assertEqual(result[1]["status"], "ADD")

    def test_completely_different_title_and_body(self):
        input_data = [
            {
                "status": "DELETE",
                "name": "Overview",
                "old_value": "Old content.",
                "new_value": "",
            },
            {
                "status": "ADD",
                "name": "Eligibility",
                "old_value": "",
                "new_value": "Completely new content.",
            },
        ]
        result = merge_renamed_subsections(input_data)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["status"], "DELETE")
        self.assertEqual(result[1]["status"], "ADD")

    def test_minimal_shared_heading(self):
        input_data = [
            {
                "status": "ADD",
                "name": "a b",
                "old_value": "",
                "new_value": "hello world",
            },
            {
                "status": "DELETE",
                "name": "a",
                "old_value": "hello",
                "new_value": "",
            },
        ]
        result = merge_renamed_subsections(input_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["status"], "UPDATE")
        self.assertIn("<ins> b</ins>", result[0]["name"])
        self.assertEqual(result[0]["diff"], "hello<ins> world</ins>")


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
            order=2,
            tag="h3",
        )
        self.new_sub_2 = Subsection.objects.create(
            name="",
            body="Go to 'Contacts and Support",
            section=self.new_section,
            order=2,
            tag="h3",
        )

        # Changed subsection (same name, different content)
        self.old_sub_3 = Subsection.objects.create(
            name="Application Process",
            body="Submit before Jan 1.",
            section=self.old_section,
            order=3,
            tag="h3",
        )
        self.new_sub_3 = Subsection.objects.create(
            name="Application Process",
            body="Submit before Feb 1.",
            section=self.new_section,
            order=3,
            tag="h3",
        )

        # Added subsection (exists only in new NOFO)
        self.new_sub_4 = Subsection.objects.create(
            name="New NOFO Funding Guidelines",
            body="Follow these new rules.",
            section=self.new_section,
            order=4,
            tag="h3",
        )

        # Matched subsection (same name, same content, different orders, different tags)
        self.old_sub_5 = Subsection.objects.create(
            name="Permitting rules",
            body="Of course permits must be obtained.",
            section=self.old_section,
            order=4,
            tag="h3",
        )
        self.new_sub_5 = Subsection.objects.create(
            name="Permitting rules",
            body="Of course permits must be obtained.",
            section=self.new_section,
            order=5,
            tag="h4",
        )

        # Deleted subsection (exists only in old NOFO)
        self.old_sub_5 = Subsection.objects.create(
            name="Old NOFO Fee Requirements",
            body="Processing fee is $50.",
            section=self.old_section,
            order=5,
            tag="h3",
        )

        # THESE 2 WILL GET MERGED

        # Added subsection (exists only in new NOFO)
        self.new_sub_6 = Subsection.objects.create(
            name="Visit SAM.gov",
            body="This is the website where you can sign up.",
            section=self.new_section,
            order=6,
            tag="h3",
        )

        # Deleted subsection (exists only in old NOFO)
        self.old_sub_6 = Subsection.objects.create(
            name="SAM.gov",
            body="Visit the website to sign up.",
            section=self.old_section,
            order=6,
            tag="h3",
        )

    def test_compare_nofos(self):
        """
        Tests the compare_nofos function, ensuring it correctly identifies matches, updates, additions, and deletions.
        """
        result = compare_nofos(self.old_nofo, self.new_nofo)

        # Ensure the result is structured correctly
        self.assertEqual(len(result), 1)  # Only one section should be in the diff
        self.assertEqual(result[0]["name"], "Step 1")

        subsections = result[0]["subsections"]
        self.assertEqual(len(subsections), 7)

        # Match test
        subsection_match = subsections[0]
        self.assertEqual(subsection_match["status"], "MATCH")
        self.assertEqual(subsection_match["name"], "Budget Requirements")
        self.assertEqual(subsection_match["old_value"], "Budget must not exceed $100K.")
        self.assertEqual(subsection_match["new_value"], "Budget must not exceed $100K.")

        # Update test (unnamed subsection)
        subsection_update = subsections[1]
        self.assertEqual(subsection_update["status"], "UPDATE")
        self.assertEqual(subsection_update["name"], "(#2)")
        self.assertEqual(
            subsection_update["old_value"], "Need help? Visit contacts and support"
        )
        self.assertEqual(subsection_update["new_value"], "Go to 'Contacts and Support")
        self.assertIn(
            "<del>Need</del><ins>Go</ins> <del>help?</del><ins>to</ins> <del>Visit contacts</del><ins>'Contacts</ins> and <del>support</del><ins>Support</ins>",
            subsection_update["diff"],
        )

        # Update test 2 (regular subsection)
        subsection_update = subsections[2]
        self.assertEqual(subsection_update["status"], "UPDATE")
        self.assertEqual(subsection_update["name"], "Application Process")
        self.assertEqual(subsection_update["old_value"], "Submit before Jan 1.")
        self.assertEqual(subsection_update["new_value"], "Submit before Feb 1.")
        self.assertIn(
            "Submit before <del>Jan</del><ins>Feb</ins> 1.", subsection_update["diff"]
        )

        # Addition test
        subsection_add = subsections[3]
        self.assertEqual(subsection_add["status"], "ADD")
        self.assertEqual(subsection_add["name"], "New NOFO Funding Guidelines")
        self.assertEqual(subsection_add["old_value"], "")
        self.assertEqual(subsection_add["new_value"], "Follow these new rules.")

        # Second match test
        subsection_match_2 = subsections[4]
        self.assertEqual(subsection_match_2["status"], "MATCH")
        self.assertEqual(subsection_match_2["name"], "Permitting rules")
        self.assertEqual(
            subsection_match_2["old_value"], "Of course permits must be obtained."
        )
        self.assertEqual(
            subsection_match_2["new_value"], "Of course permits must be obtained."
        )

        # Deletion test
        subsection_delete = subsections[5]
        self.assertEqual(
            subsection_delete["name"], "<del>Old NOFO Fee Requirements</del>"
        )
        self.assertEqual(subsection_delete["old_value"], "Processing fee is $50.")
        self.assertEqual(subsection_delete["new_value"], "")
        self.assertIn("<del>Processing fee is $50.</del>", subsection_delete["diff"])

        # Deletion test
        subsection_merge = subsections[6]
        self.assertEqual(subsection_merge["name"], "<ins>Visit </ins>SAM.gov")
        self.assertEqual(subsection_merge["old_value"], "Visit the website to sign up.")
        self.assertEqual(
            subsection_merge["new_value"], "This is the website where you can sign up."
        )
        self.assertIn(
            "<del>Visit</del><ins>This is</ins> the website <del>to</del><ins>where you can</ins> sign up.",
            subsection_merge["diff"],
        )


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
        nofo_comparison_metadata = compare_nofos_metadata(self.old_nofo, self.new_nofo)

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


class TestApplyComparisonTypes(TestCase):

    def test_none_comparison_type_skips_all_statuses(self):
        for status in ["UPDATE", "MATCH", "ADD", "DELETE"]:
            with self.subTest(status=status):
                items = [
                    {"status": status, "comparison_type": "none", "diff": "old diff"}
                ]
                result = apply_comparison_types(items)
                self.assertEqual(result, [], "Failed for status={}".format(status))

    def test_missing_comparison_type_appends_all_statuses(self):
        item = {"status": "UPDATE", "name": "Something", "diff": "old diff"}
        self.assertEqual(apply_comparison_types([item])[0], item)

        for status in ["UPDATE", "MATCH", "ADD", "DELETE"]:
            with self.subTest(status=status):
                item = {"status": status, "name": "Something", "diff": "old diff"}
                original_item = deepcopy(item)

                result = apply_comparison_types([item])
                self.assertEqual(
                    result[0], original_item, "Failed for status={}".format(status)
                )

    # ADD can't have comparison types
    def test_add_status_untouched(self):
        item = {"status": "ADD", "diff": "old diff", "comparison_type": "name"}
        self.assertIn(item, apply_comparison_types([item]))

    def test_delete_status_comparison_type_name(self):
        item = {
            "status": "DELETE",
            "diff": "old diff",
            "comparison_type": "name",
            "diff_strings": ["one", "two", "three"],
        }
        original_item = deepcopy(item)

        result = apply_comparison_types([item])
        original_item["diff"] = "—"
        self.assertEqual(result[0], original_item)

    def test_delete_status_comparison_type_body(self):
        item = {
            "status": "DELETE",
            "diff": "old diff",
            "comparison_type": "body",
            "diff_strings": ["one", "two", "three"],
        }
        original_item = deepcopy(item)

        result = apply_comparison_types([item])
        self.assertEqual(result[0], original_item)

    def test_delete_status_comparison_type_diff_strings(self):
        item = {
            "status": "DELETE",
            "diff": "old diff",
            "comparison_type": "diff_strings",
            "diff_strings": ["one", "two", "three"],
        }
        original_item = deepcopy(item)

        result = apply_comparison_types([item])
        original_item["diff"] = (
            "<ul><li><del>one</del></li><li><del>two</del></li><li><del>three</del></li></ul>"
        )
        self.assertEqual(result[0], original_item)

    def test_match_status_untouched_for_all_comparison_types(self):
        for comparison_type in ["name", "body", "diff_strings"]:
            with self.subTest(comparison_type=comparison_type):
                item = {
                    "status": "MATCH",
                    "comparison_type": comparison_type,
                    "diff": "old diff",
                }
                original_item = deepcopy(item)

                result = apply_comparison_types([item])
                self.assertEqual(
                    result[0],
                    original_item,
                    "Failed for comparison_type={}".format(comparison_type),
                )

    def test_update_name_diff_present(self):
        item = {
            "status": "UPDATE",
            "comparison_type": "name",
            "name": "<del>Foo</del><ins>Bar</ins>",
            "diff": "old diff",
        }
        result = apply_comparison_types([item])[0]
        self.assertEqual(result["status"], "UPDATE")
        self.assertEqual(result["diff"], "—")

    def test_update_name_no_diff_becomes_match(self):
        item = {
            "status": "UPDATE",
            "comparison_type": "name",
            "name": "Section Title",
            "diff": "old diff",
        }
        result = apply_comparison_types([item])[0]
        self.assertEqual(result["status"], "MATCH")
        self.assertEqual(result["diff"], "—")

    def test_update_diff_strings_match_all(self):
        item = {
            "status": "UPDATE",
            "comparison_type": "diff_strings",
            "diff_strings": ["data", "program"],
            "new_value": "This data program is working.",
            "diff": "old diff",
        }
        result = apply_comparison_types([item])[0]
        self.assertEqual(result["status"], "MATCH")
        self.assertEqual(result["diff"], "—")

    def test_update_diff_strings_some_missing(self):
        item = {
            "status": "UPDATE",
            "comparison_type": "diff_strings",
            "diff_strings": ["data", "banana"],
            "new_value": "This data program is working.",
            "diff": "old diff",
        }
        result = apply_comparison_types([item])[0]
        self.assertEqual(result["status"], "UPDATE")
        self.assertIn("<del>banana</del>", result["diff"])

    def test_update_diff_strings_match_all_but_name_modified(self):
        item = {
            "name": "The <ins>New</ins> Program",
            "status": "UPDATE",
            "comparison_type": "diff_strings",
            "diff_strings": ["data", "program"],
            "new_value": "This data program is working.",
            "diff": "old diff",
        }
        result = apply_comparison_types([item])[0]
        self.assertEqual(result["status"], "UPDATE")
        self.assertEqual(result["diff"], "—")
