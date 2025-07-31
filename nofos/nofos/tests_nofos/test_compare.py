from copy import deepcopy

from django.test import TestCase

from ..models import Nofo, Section, Subsection
from ..nofo_compare import (
    SubsectionDiff,
    annotate_side_by_side_diffs,
    apply_comparison_types,
    compare_nofos,
    compare_nofos_metadata,
    filter_comparison_by_status,
    merge_renamed_subsections,
)


class MergeRenamedSubsectionsTests(TestCase):
    def test_exact_body_match_renamed_title(self):

        input_data = [
            SubsectionDiff(
                name="Overview",
                status="ADD",
                old_value="",
                new_value="This is some content.",
            ),
            SubsectionDiff(
                name="Summary",
                status="DELETE",
                old_value="This is some content.",
                new_value="",
            ),
        ]
        result = merge_renamed_subsections(input_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].status, "UPDATE")
        self.assertIn("<ins>Overview</ins>", result[0].name)
        self.assertIn("<del>Summary</del>", result[0].name)
        self.assertEqual(result[0].diff, "<p>This is some content.</p>")

    def test_renamed_title_and_changed_body(self):
        input_data = [
            SubsectionDiff(
                name="Summary",
                status="ADD",
                old_value="",
                new_value="New content.",
            ),
            SubsectionDiff(
                name="Overview",
                status="DELETE",
                old_value="Old content.",
                new_value="",
            ),
        ]
        result = merge_renamed_subsections(input_data)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].status, "ADD")
        self.assertEqual(result[1].status, "DELETE")

    def test_completely_different_title_and_body(self):
        input_data = [
            SubsectionDiff(
                name="Eligibility",
                status="ADD",
                old_value="",
                new_value="Totally new stuff.",
            ),
            SubsectionDiff(
                name="Overview",
                status="DELETE",
                old_value="Old content.",
                new_value="",
            ),
        ]
        result = merge_renamed_subsections(input_data)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].status, "ADD")
        self.assertEqual(result[1].status, "DELETE")

    def test_minimal_shared_heading(self):
        input_data = [
            SubsectionDiff(
                name="a b",
                status="ADD",
                old_value="",
                new_value="Groundhog Day",
            ),
            SubsectionDiff(
                name="a",
                status="DELETE",
                old_value="Groundhog",
                new_value="",
            ),
        ]
        result = merge_renamed_subsections(input_data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].status, "UPDATE")
        self.assertIn("<ins> b</ins>", result[0].name)
        self.assertEqual(result[0].diff, "<p>Groundhog<ins> Day</ins></p>")


class FilterComparisonByStatusTests(TestCase):
    def test_returns_unchanged_when_no_statuses_to_ignore(self):
        data = [SubsectionDiff(name="A", status="MATCH")]
        result = filter_comparison_by_status(data, statuses_to_ignore=[])
        self.assertEqual(result, data)

    def test_flat_comparison_filters_match(self):
        data = [
            SubsectionDiff(name="A", status="MATCH"),
            SubsectionDiff(name="B", status="ADD"),
            SubsectionDiff(name="C", status="UPDATE"),
        ]
        result = filter_comparison_by_status(data, statuses_to_ignore=["MATCH"])
        self.assertEqual(
            result,
            [
                SubsectionDiff(name="B", status="ADD"),
                SubsectionDiff(name="C", status="UPDATE"),
            ],
        )

    def test_flat_comparison_filters_multiple(self):
        data = [
            SubsectionDiff(name="A", status="MATCH"),
            SubsectionDiff(name="B", status="ADD"),
            SubsectionDiff(name="C", status="UPDATE"),
        ]
        result = filter_comparison_by_status(data, statuses_to_ignore=["MATCH", "ADD"])
        self.assertEqual(result, [SubsectionDiff(name="C", status="UPDATE")])

    def test_flat_comparison_all_filtered(self):
        data = [
            SubsectionDiff(name="A", status="MATCH"),
            SubsectionDiff(name="B", status="MATCH"),
        ]
        result = filter_comparison_by_status(data, statuses_to_ignore=["MATCH"])
        self.assertEqual(result, [])

    def test_section_based_filters_subsections(self):
        data = [
            {
                "name": "Section 1",
                "subsections": [
                    SubsectionDiff(name="A", status="MATCH"),
                    SubsectionDiff(name="B", status="ADD"),
                ],
            },
            {
                "name": "Section 2",
                "subsections": [
                    SubsectionDiff(name="C", status="MATCH"),
                    SubsectionDiff(name="D", status="UPDATE"),
                ],
            },
        ]
        result = filter_comparison_by_status(data, statuses_to_ignore=["MATCH"])
        self.assertEqual(
            result,
            [
                {
                    "name": "Section 1",
                    "subsections": [SubsectionDiff(name="B", status="ADD")],
                },
                {
                    "name": "Section 2",
                    "subsections": [SubsectionDiff(name="D", status="UPDATE")],
                },
            ],
        )

    def test_section_based_drops_empty_sections(self):
        data = [
            {
                "name": "Section 1",
                "subsections": [SubsectionDiff(name="A", status="MATCH")],
            },
            {
                "name": "Section 2",
                "subsections": [SubsectionDiff(name="B", status="ADD")],
            },
        ]
        result = filter_comparison_by_status(data, statuses_to_ignore=["MATCH"])
        self.assertEqual(
            result,
            [
                {
                    "name": "Section 2",
                    "subsections": [SubsectionDiff(name="B", status="ADD")],
                }
            ],
        )

    def test_section_based_keeps_empty_sections_if_no_array_provided(self):
        data = [
            {
                "name": "Section 1",
                "subsections": [],
            },
            {
                "name": "Section 2",
                "subsections": [],
            },
        ]
        result = filter_comparison_by_status(data)
        self.assertEqual(result, data)

    def test_section_based_drops_intially_empty_sections_if_array_provided(self):
        data = [
            {
                "name": "Section 1",
                "subsections": [],
            },
            {
                "name": "Section 2",
                "subsections": [],
            },
        ]
        result = filter_comparison_by_status(data, statuses_to_ignore=["MATCH"])
        self.assertEqual(result, [])

    def test_empty_array_returns_empty(self):
        result = filter_comparison_by_status([], statuses_to_ignore=["MATCH"])
        self.assertEqual(result, [])

    def test_empty_array_with_no_ignored_statuses_returns_empty(self):
        result = filter_comparison_by_status([], statuses_to_ignore=[])
        self.assertEqual(result, [])


class TestApplyComparisonTypes(TestCase):

    def test_none_comparison_type_skips_all_statuses(self):
        for status in ["UPDATE", "MATCH", "ADD", "DELETE"]:
            with self.subTest(status=status):
                items = [
                    SubsectionDiff(
                        name="", status=status, comparison_type="none", diff="old diff"
                    )
                ]
                result = apply_comparison_types(items)
                self.assertEqual(result, [], f"Failed for status={status}")

    def test_missing_comparison_type_appends_all_statuses(self):
        # Single test for "UPDATE" without comparison_type
        item = SubsectionDiff(status="UPDATE", name="Something", diff="old diff")
        self.assertEqual(apply_comparison_types([item])[0], item)

        for status in ["UPDATE", "MATCH", "ADD", "DELETE"]:
            with self.subTest(status=status):
                item = SubsectionDiff(status=status, name="Something", diff="old diff")
                original_item = deepcopy(item)

                result = apply_comparison_types([item])
                self.assertEqual(
                    result[0], original_item, f"Failed for status={status}"
                )

    # ADD can't have comparison types
    def test_add_status_untouched(self):
        item = SubsectionDiff(
            name="", status="ADD", comparison_type="name", diff="old diff"
        )

        self.assertIn(item, apply_comparison_types([item]))

    def test_delete_status_comparison_type_name(self):
        item = SubsectionDiff(
            name="",
            status="DELETE",
            comparison_type="name",
            diff="old diff",
            diff_strings=["one", "two", "three"],
        )

        original_item = deepcopy(item)

        result = apply_comparison_types([item])
        original_item.diff = "—"
        self.assertEqual(result[0], original_item)

    def test_delete_status_comparison_type_body(self):
        item = SubsectionDiff(
            name="",
            status="DELETE",
            comparison_type="body",
            diff="old diff",
            diff_strings=["one", "two", "three"],
        )
        original_item = deepcopy(item)

        result = apply_comparison_types([item])
        self.assertEqual(result[0], original_item)

    def test_delete_status_comparison_type_diff_strings(self):
        item = SubsectionDiff(
            name="",
            status="DELETE",
            comparison_type="diff_strings",
            diff="old diff",
            diff_strings=["one", "two", "three"],
        )
        original_item = deepcopy(item)

        result = apply_comparison_types([item])
        original_item.diff = "<ul><li><del>one</del></li><li><del>two</del></li><li><del>three</del></li></ul>"
        self.assertEqual(result[0], original_item)

    def test_none_comparison_type_skips_all_statuses(self):
        for status in ["UPDATE", "MATCH", "ADD", "DELETE"]:
            with self.subTest(status=status):
                items = [
                    SubsectionDiff(
                        name="", status=status, comparison_type="none", diff="old diff"
                    )
                ]
                result = apply_comparison_types(items)
                self.assertEqual(result, [], f"Failed for status={status}")

    def test_match_status_untouched_for_all_comparison_types(self):
        for comparison_type in ["name", "body", "diff_strings"]:
            with self.subTest(comparison_type=comparison_type):
                item = SubsectionDiff(
                    name="",
                    status="MATCH",
                    comparison_type=comparison_type,
                    diff="old diff",
                )

                original_item = deepcopy(item)

                result = apply_comparison_types([item])
                self.assertEqual(
                    result[0],
                    original_item,
                    "Failed for comparison_type={}".format(comparison_type),
                )

    def test_update_name_diff_present(self):
        item = SubsectionDiff(
            status="UPDATE",
            comparison_type="name",
            name="<del>Foo</del><ins>Bar</ins>",
            diff="old diff",
        )
        result = apply_comparison_types([item])[0]
        self.assertEqual(result.status, "UPDATE")
        self.assertEqual(result.diff, "—")

    def test_update_name_no_diff_becomes_match(self):
        item = SubsectionDiff(
            status="UPDATE",
            comparison_type="name",
            name="Section Title",
            diff="old diff",
        )
        result = apply_comparison_types([item])[0]
        self.assertEqual(result.status, "MATCH")
        self.assertEqual(result.diff, "—")

    def test_update_diff_strings_match_all(self):
        item = SubsectionDiff(
            name="",
            status="UPDATE",
            comparison_type="diff_strings",
            diff_strings=["data", "program"],
            new_value="This data program is working.",
            diff="old diff",
        )
        result = apply_comparison_types([item])[0]
        self.assertEqual(result.status, "MATCH")
        self.assertEqual(result.diff, "—")

    def test_update_diff_strings_some_missing(self):
        item = SubsectionDiff(
            name="",
            status="UPDATE",
            comparison_type="diff_strings",
            diff_strings=["data", "banana"],
            new_value="This data program is working.",
            diff="old diff",
        )
        result = apply_comparison_types([item])[0]
        self.assertEqual(result.status, "UPDATE")
        self.assertIn("<del>banana</del>", result.diff)

    def test_update_diff_strings_match_all_but_name_modified(self):
        item = SubsectionDiff(
            name="The <ins>New</ins> Program",
            status="UPDATE",
            comparison_type="diff_strings",
            diff_strings=["data", "program"],
            new_value="This data program is working.",
            diff="old diff",
        )
        result = apply_comparison_types([item])[0]
        self.assertEqual(result.status, "UPDATE")
        self.assertEqual(result.diff, "—")


class AnnotateSideBySideDiffsTests(TestCase):
    def test_empty_diff(self):
        diff = SubsectionDiff(name="Empty", status="MATCH", diff="")
        annotated = annotate_side_by_side_diffs([diff])[0]
        self.assertEqual(annotated.old_diff, None)
        self.assertEqual(annotated.new_diff, None)

    def test_only_insertion(self):
        diff_html = "<p>Intro</p><p>Second <ins>added</ins> sentence.</p>"
        diff = SubsectionDiff(name="Add only", status="UPDATE", diff=diff_html)
        annotated = annotate_side_by_side_diffs([diff])[0]
        self.assertEqual("<p>Intro</p><p>Second  sentence.</p>", annotated.old_diff)
        self.assertEqual(
            "<p>Intro</p><p>Second <ins>added</ins> sentence.</p>", annotated.new_diff
        )

    def test_only_deletion(self):
        diff_html = "<p>Intro</p><p>Second <del>removed</del> sentence.</p>"
        diff = SubsectionDiff(name="Del only", status="UPDATE", diff=diff_html)
        annotated = annotate_side_by_side_diffs([diff])[0]
        self.assertEqual("<p>Intro</p><p>Second  sentence.</p>", annotated.new_diff)
        self.assertEqual(
            "<p>Intro</p><p>Second <del>removed</del> sentence.</p>", annotated.old_diff
        )

    def test_update_with_add_and_delete(self):
        diff_html = "<p>Start <del>old</del><ins>new</ins> middle</p>"
        diff = SubsectionDiff(name="Update", status="UPDATE", diff=diff_html)
        annotated = annotate_side_by_side_diffs([diff])[0]
        self.assertIn("old", annotated.old_diff)
        self.assertEqual("<p>Start <del>old</del> middle</p>", annotated.old_diff)
        self.assertEqual("<p>Start <ins>new</ins> middle</p>", annotated.new_diff)

    def test_no_diff_tags_present(self):
        diff_html = "<p>This is unchanged content</p>"
        diff = SubsectionDiff(name="No diff", status="MATCH", diff=diff_html)
        annotated = annotate_side_by_side_diffs([diff])[0]
        self.assertEqual(annotated.old_diff, diff_html)
        self.assertEqual(annotated.new_diff, diff_html)

    def test_section_dict_with_subsections(self):
        subsection = SubsectionDiff(
            name="Subsection",
            status="UPDATE",
            diff="<p>Original <del>deleted</del> <ins>added</ins></p>",
        )
        section = {"name": "Section A", "subsections": [subsection]}
        result = annotate_side_by_side_diffs([section])[0]
        annotated = result["subsections"][0]
        self.assertEqual("<p>Original <del>deleted</del> </p>", annotated.old_diff)
        self.assertEqual("<p>Original  <ins>added</ins></p>", annotated.new_diff)


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
        Tests the compare_nofos function, ensuring it correctly identifies matches, updates, additions, deletions, and merges.
        """
        result = compare_nofos(self.old_nofo, self.new_nofo)

        # Ensure the result is structured correctly
        self.assertEqual(len(result), 1)  # Only one section should be in the diff
        self.assertEqual(result[0]["name"], "Step 1")

        subsections = result[0]["subsections"]
        self.assertEqual(len(subsections), 7)

        # Match test
        subsection_match = subsections[0]
        self.assertEqual(subsection_match.status, "MATCH")
        self.assertEqual(subsection_match.name, "Budget Requirements")
        self.assertEqual(subsection_match.old_value, "Budget must not exceed $100K.")
        self.assertEqual(subsection_match.new_value, "Budget must not exceed $100K.")

        # Update test (unnamed subsection)
        subsection_update = subsections[1]
        self.assertEqual(subsection_update.status, "UPDATE")
        self.assertEqual(subsection_update.name, "(#2)")
        self.assertEqual(
            subsection_update.old_value, "Need help? Visit contacts and support"
        )
        self.assertEqual(subsection_update.new_value, "Go to 'Contacts and Support")
        self.assertIn(
            "<p><del>Need help? Visit c</del><ins>Go to ‘C</ins>ontacts and <del>s</del><ins>S</ins>upport</p>",
            subsection_update.diff,
        )

        # Update test 2 (regular subsection)
        subsection_update_2 = subsections[2]
        self.assertEqual(subsection_update_2.status, "UPDATE")
        self.assertEqual(subsection_update_2.name, "Application Process")
        self.assertEqual(subsection_update_2.old_value, "Submit before Jan 1.")
        self.assertEqual(subsection_update_2.new_value, "Submit before Feb 1.")
        self.assertIn(
            "Submit before <del>Jan</del><ins>Feb</ins> 1.", subsection_update_2.diff
        )

        # Addition test
        subsection_add = subsections[3]
        self.assertEqual(subsection_add.status, "ADD")
        self.assertEqual(subsection_add.name, "New NOFO Funding Guidelines")
        self.assertEqual(subsection_add.old_value, "")
        self.assertEqual(subsection_add.new_value, "Follow these new rules.")

        # Second match test
        subsection_match_2 = subsections[4]
        self.assertEqual(subsection_match_2.status, "MATCH")
        self.assertEqual(subsection_match_2.name, "Permitting rules")
        self.assertEqual(
            subsection_match_2.old_value, "Of course permits must be obtained."
        )
        self.assertEqual(
            subsection_match_2.new_value, "Of course permits must be obtained."
        )

        # Deletion test
        subsection_delete = subsections[5]
        self.assertEqual(subsection_delete.status, "DELETE")
        self.assertEqual(subsection_delete.name, "<del>Old NOFO Fee Requirements</del>")
        self.assertEqual(subsection_delete.old_value, "Processing fee is $50.")
        self.assertEqual(subsection_delete.new_value, "")
        self.assertIn(
            "<del><p>Processing fee is $50.</p></del>", subsection_delete.diff
        )

        # Merged update test (renamed + updated content)
        subsection_merge = subsections[6]
        self.assertEqual(subsection_merge.status, "UPDATE")
        self.assertEqual(subsection_merge.name, "<ins>Visit </ins>SAM.gov")
        self.assertEqual(subsection_merge.old_value, "Visit the website to sign up.")
        self.assertEqual(
            subsection_merge.new_value, "This is the website where you can sign up."
        )
        self.assertIn(
            "<del>Visit</del><ins>This is</ins> the website <del>to</del><ins>where you can</ins> sign up.",
            subsection_merge.diff,
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
            item for item in nofo_comparison_metadata if item.status != "MATCH"
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
            if item.name in matched_names:
                self.assertEqual(item.status, "MATCH")
                self.assertFalse(item.diff)  # None or ""

        # Update test (subagency changed)
        subagency_update = nofo_comparison_metadata[4]
        self.assertEqual(subagency_update.status, "UPDATE")
        self.assertEqual(
            subagency_update.old_value, "Department of Guessing Groundhogs (DGG)"
        )
        self.assertEqual(
            subagency_update.new_value, "Department of Groundhog Excellence (DOGE)"
        )
        self.assertIn(
            "Department of G<del>uessing Groundhogs (DGG</del><ins>roundhog Excellence (DOGE</ins>)",
            subagency_update.diff,
        )

        # Delete test (subagency2 removed)
        subagency2_delete = nofo_comparison_metadata[5]
        self.assertEqual(subagency2_delete.status, "DELETE")
        self.assertEqual(
            subagency2_delete.old_value,
            "Action Group for Diverse Prognosticators (AGDP)",
        )
        self.assertEqual(subagency2_delete.new_value, "")
        self.assertIn(
            "<del>Action Group for Diverse Prognosticators (AGDP)</del>",
            subagency2_delete.diff,
        )

        # Addition test (application deadline added)
        application_deadline_add = nofo_comparison_metadata[6]
        self.assertEqual(application_deadline_add.status, "ADD")
        self.assertEqual(application_deadline_add.old_value, "")
        self.assertEqual(application_deadline_add.new_value, "February 2, 2026")
        self.assertIn("<ins>February 2, 2026</ins>", application_deadline_add.diff)
