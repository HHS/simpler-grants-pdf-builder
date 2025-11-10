from composer.models import (
    ContentGuide,
    ContentGuideSection,
    ContentGuideSubsection,
)
from django.test import TestCase


class ExtractVariablesTests(TestCase):
    def setUp(self):
        self.guide = ContentGuide.objects.create(
            title="Guide", opdiv="CDC", group="bloom"
        )
        self.section = ContentGuideSection.objects.create(
            document=self.guide, order=1, name="Section 1", html_id="sec-1"
        )

    def _mk(self, body: str):
        return ContentGuideSubsection.objects.create(
            section=self.section,
            order=1,
            name="Sub 1",
            tag="h3",
            body=body,
            edit_mode="full",
            enabled=True,
        )

    def test_no_variables_returns_empty_list(self):
        ss = self._mk("No placeholders here.")
        self.assertEqual(ss.extract_variables(), [])

    def test_simple_string_variable(self):
        ss = self._mk("Please provide {Project name} for the application.")
        vars_ = ss.extract_variables()
        self.assertEqual(
            vars_,
            [
                {"key": "project_name", "type": "string", "label": "Project name"},
            ],
        )

    def test_list_variable_type(self):
        ss = self._mk("Add tags: {List: Tags}")
        vars_ = ss.extract_variables()
        self.assertEqual(
            vars_,
            [
                {"key": "tags", "type": "list", "label": "Tags"},
            ],
        )

    def test_duplicate_labels_are_deduped(self):
        ss = self._mk("Enter {Project name} and confirm {Project name}")
        vars_ = ss.extract_variables()
        self.assertEqual(
            vars_[0], {"key": "project_name", "type": "string", "label": "Project name"}
        )
        self.assertEqual(
            vars_[1],
            {"key": "project_name_2", "type": "string", "label": "Project name"},
        )

    def test_escaped_opening_brace_does_not_create_variable(self):
        ss = self._mk(r"Literal \{not a variable} and real {Variable}")
        vars_ = ss.extract_variables()
        self.assertEqual(
            vars_,
            [
                {"key": "variable", "type": "string", "label": "Variable"},
            ],
        )

    def test_empty_or_whitespace_label_falls_back_to_key_var(self):
        ss = self._mk("Weird case: {   }")
        vars_ = ss.extract_variables()
        self.assertEqual(
            vars_,
            [
                {
                    "key": "var",
                    "type": "string",
                    "label": "",
                },  # label trimmed to empty → key fallback
            ],
        )

    def test_text_override_parameter_is_used_instead_of_instance_body(self):
        ss = self._mk("Old body without vars")
        override = "New body with a {Fresh var}"
        vars_ = ss.extract_variables(text=override)
        self.assertEqual(
            vars_,
            [
                {"key": "fresh_var", "type": "string", "label": "Fresh var"},
            ],
        )


class GetGroupedSubsections(TestCase):
    def setUp(self):
        # Minimal parent objects so we can create valid subsections
        self.guide = ContentGuide.objects.create(
            title="Guide", opdiv="CDC", group="bloom"
        )
        self.section = ContentGuideSection.objects.create(
            document=self.guide, order=1, name="Section 1", html_id="sec-1"
        )

    def _make_subsection(
        self, name, tag=None, order=1, body="Generic body content", instructions=""
    ):
        """Helper to make a subsection instance (not saved content matters for grouping)."""
        return ContentGuideSubsection.objects.create(
            section=self.section,
            order=order,
            name=name,
            tag=tag or "",
            body=body,
            instructions=instructions,
            enabled=True,
        )

    def test_empty_list_returns_empty_groups(self):
        groups = self.section.get_grouped_subsections()
        self.assertEqual(groups, [])

    def test_first_item_not_a_header_starts_its_own_group(self):
        # s1 is not in preset headers and has no h2/h3 tag → becomes first group's heading
        s1 = self._make_subsection("Intro", tag="h5", order=1)
        # s2 matches a preset header name → starts new group
        s2 = self._make_subsection("Funding details", tag="h5", order=2)
        # s3 is a normal item → belongs to s2's group
        s3 = self._make_subsection("Line items", tag="h5", order=3)

        groups = self.section.get_grouped_subsections()

        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]["heading"], "Intro")
        self.assertEqual([x.pk for x in groups[0]["items"]], [s1.pk])

        self.assertEqual(groups[1]["heading"], "Funding details")
        self.assertEqual([x.pk for x in groups[1]["items"]], [s2.pk, s3.pk])

    def test_header_created_by_tag_h2_or_h3(self):
        # s1 is header because tag=h3 (even though name not in preset headers)
        s1 = self._make_subsection("Overview", tag="h3", order=1)
        # s2 is header because tag=h2
        s2 = self._make_subsection("Deep dive", tag="h2", order=2)
        # s3 follows s2 and is not a header → stays in s2's group
        s3 = self._make_subsection("Details list", tag="h5", order=3)

        groups = self.section.get_grouped_subsections()

        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]["heading"], "Overview")
        self.assertEqual([x.pk for x in groups[0]["items"]], [s1.pk])

        self.assertEqual(groups[1]["heading"], "Deep dive")
        self.assertEqual([x.pk for x in groups[1]["items"]], [s2.pk, s3.pk])

    def test_consecutive_headers_each_start_their_own_group(self):
        # Two headers in a row → two groups, each includes the header item itself
        s1 = self._make_subsection("Funding details", tag="h4", order=1)
        s2 = self._make_subsection("Eligibility", tag="h4", order=2)

        groups = self.section.get_grouped_subsections()

        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]["heading"], "Funding details")
        self.assertEqual([x.pk for x in groups[0]["items"]], [s1.pk])

        self.assertEqual(groups[1]["heading"], "Eligibility")
        self.assertEqual([x.pk for x in groups[1]["items"]], [s2.pk])

    def test_none_or_empty_name_is_tolerated(self):
        # First item has no name and is not a header → catch-all creates a group with that (None) heading
        s1 = self._make_subsection(name="", tag="", order=1)
        s2 = self._make_subsection(
            "Basic information", tag="h4", order=2
        )  # preset header starts new group

        groups = self.section.get_grouped_subsections()

        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]["heading"], "")
        self.assertEqual([x.pk for x in groups[0]["items"]], [s1.pk])

        self.assertEqual(groups[1]["heading"], "Basic information")
        self.assertEqual([x.pk for x in groups[1]["items"]], [s2.pk])

    def test_header_item_with_empty_body_is_skipped(self):
        # s1 is a header (preset name); its body is empty → should NOT appear in items
        s1 = self._make_subsection("Funding details", tag="h4", order=1, body="")
        # A normal subsection after the header
        s2 = self._make_subsection(
            "Budget breakdown", tag="h5", order=2, body="Some text"
        )

        groups = self.section.get_grouped_subsections()

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["heading"], "Funding details")
        # Only s2 shows up because s1 (the header item) had no body
        self.assertEqual([x.pk for x in groups[0]["items"]], [s2.pk])

    def test_header_item_with_nonempty_body_is_included(self):
        # s1 is a header (preset name) with real body → should appear in items
        s1 = self._make_subsection(
            "Funding details", tag="h4", order=1, body="<p>Hello</p>"
        )
        s2 = self._make_subsection(
            "Budget breakdown", tag="h5", order=2, body="Some text"
        )

        groups = self.section.get_grouped_subsections()

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["heading"], "Funding details")
        # s1 included first, then s2
        self.assertEqual([x.pk for x in groups[0]["items"]], [s1.pk, s2.pk])

    def test_header_item_with_nonempty_instructions_is_included(self):
        # s1 is a header (preset name) with non-empty instructions → should appear in items
        s1 = self._make_subsection(
            "Funding details",
            tag="h4",
            order=1,
            body="",
            instructions="Please enter funding details in Canadian dollars",
        )

        s2 = self._make_subsection(
            "Budget breakdown", tag="h5", order=2, body="Some text"
        )

        groups = self.section.get_grouped_subsections()

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["heading"], "Funding details")
        # s1 included first, then s2
        self.assertEqual([x.pk for x in groups[0]["items"]], [s1.pk, s2.pk])
