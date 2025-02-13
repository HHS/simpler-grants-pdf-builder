from django.test import TestCase
from ..models import Nofo, Section, Subsection
from ..views import compare_nofos


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
        self.old_sub_1 = self.old_section.subsections.first()
        self.old_sub_1.name = "Budget Requirements"
        self.old_sub_1.body = "Budget must not exceed $100K."
        self.old_sub_1.tag = "h3"
        self.old_sub_1.save()

        self.new_sub_1 = self.new_section.subsections.first()
        self.new_sub_1.name = "Budget Requirements"
        self.new_sub_1.body = "Budget must not exceed $100K."
        self.new_sub_1.tag = "h3"
        self.new_sub_1.save()

        # Changed subsection (same name, different content)
        self.old_sub_2 = Subsection.objects.create(
            name="Application Process",
            body="Submit before Jan 1.",
            section=self.old_section,
            order=3,
            tag="h3",
        )
        self.new_sub_2 = Subsection.objects.create(
            name="Application Process",
            body="Submit before Feb 1.",
            section=self.new_section,
            order=3,
            tag="h3",
        )

        # Added subsection (exists only in new NOFO)
        self.new_sub_3 = Subsection.objects.create(
            name="New NOFO Funding Guidelines",
            body="Follow these new rules.",
            section=self.new_section,
            order=4,
            tag="h3",
        )

        # Deleted subsection (exists only in old NOFO)
        self.old_sub_4 = Subsection.objects.create(
            name="Old NOFO Fee Requirements",
            body="Processing fee is $50.",
            section=self.old_section,
            order=4,
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
        self.assertEqual(len(subsections), 4)

        # Match test
        subsection_match = subsections[0]
        self.assertEqual(subsection_match["status"], "MATCH")
        self.assertEqual(subsection_match["name"], "Budget Requirements")
        self.assertEqual(subsection_match["body"], "Budget must not exceed $100K.")

        # Update test
        subsection_update = subsections[1]
        self.assertEqual(subsection_update["status"], "UPDATE")
        self.assertEqual(subsection_update["name"], "Application Process")
        self.assertEqual(subsection_update["body"], "Submit before Feb 1.")
        self.assertIn(
            "Submit before <del>Jan</del><ins>Feb</ins> 1.", subsection_update["diff"]
        )

        # Addition test
        subsection_add = subsections[2]
        self.assertEqual(subsection_add["status"], "ADD")
        self.assertEqual(subsection_add["name"], "New NOFO Funding Guidelines")
        self.assertEqual(subsection_add["body"], "Follow these new rules.")

        # Deletion test
        subsection_delete = subsections[3]
        self.assertEqual(subsection_delete["name"], "Old NOFO Fee Requirements")
        self.assertEqual(subsection_delete["body"], "Processing fee is $50.")
        self.assertIn("<del>Processing fee is $50.</del>", subsection_delete["diff"])
