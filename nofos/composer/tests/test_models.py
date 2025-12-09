from composer.models import (
    ContentGuide,
    ContentGuideInstance,
    ContentGuideSection,
    ContentGuideSubsection,
    VariableInfo,
)
from django.test import TestCase


class ExtractVariablesTests(TestCase):
    def setUp(self):
        self.guide = ContentGuide.objects.create(
            title="Guide", opdiv="CDC", group="bloom"
        )
        self.section = ContentGuideSection.objects.create(
            content_guide=self.guide, order=1, name="Section 1", html_id="sec-1"
        )

    def _mk(self, body: str):
        return ContentGuideSubsection.objects.create(
            section=self.section,
            order=1,
            name="Sub 1",
            tag="h3",
            body=body,
            edit_mode="full",
        )

    def test_no_variables(self):
        subsection = self._mk("This sentence has no variables.")
        self.assertEqual(subsection.extract_variables(), {})

    def test_simple_variable(self):
        subsection = self._mk("This sentence has one {variable}.")
        variables = subsection.extract_variables()
        self.assertEqual(
            variables,
            {
                "variable": VariableInfo(
                    key="variable", type="string", label="variable"
                ),
            },
        )

    def test_variable_with_spaces(self):
        subsection = self._mk("This has { variable with spaces }.")
        variables = subsection.extract_variables()
        self.assertEqual(
            variables,
            {
                "variable_with_spaces": VariableInfo(
                    key="variable_with_spaces",
                    type="string",
                    label="variable with spaces",
                ),
            },
        )

    def test_duplicate_variables(self):
        subsection = self._mk("Enter {Project name} and confirm {Project name}")
        variables = list(subsection.extract_variables().items())
        self.assertEqual(
            variables[0],
            (
                "project_name",
                VariableInfo(key="project_name", type="string", label="Project name"),
            ),
        )
        self.assertEqual(
            variables[1],
            (
                "project_name_2",
                VariableInfo(key="project_name_2", type="string", label="Project name"),
            ),
        )

    def test_multiple_variables(self):
        subsection = self._mk("This has {first} and {second} variables.")
        variables = subsection.extract_variables()
        self.assertEqual(
            variables,
            {
                "first": VariableInfo(key="first", type="string", label="first"),
                "second": VariableInfo(key="second", type="string", label="second"),
            },
        )

    def test_escaped_braces(self):
        """Escaped braces should not be treated as variables."""
        subsection = self._mk(r"This is not a \{variable\}.")
        variables = subsection.extract_variables()
        self.assertEqual(variables, {})

    def test_escaped_opening_brace(self):
        subsection = self._mk(r"Literal \{not a variable} and real {Variable}")
        variables = subsection.extract_variables()
        self.assertEqual(
            variables,
            {
                "variable": VariableInfo(
                    key="variable", type="string", label="Variable"
                ),
            },
        )

    def test_nested_braces(self):
        """Nested braces should match first complete set of braces: '{outer {inner}'}"""
        subsection = self._mk("This {outer {inner} text} has nesting.")
        variables = subsection.extract_variables()
        self.assertEqual(
            variables,
            {
                "outer_inner": VariableInfo(
                    key="outer_inner",
                    label="outer {inner",
                    type="string",
                )
            },
        )

    def test_empty_braces(self):
        """Empty braces should not be treated as variables."""
        subsection = self._mk("This has {} empty braces.")
        variables = subsection.extract_variables()
        self.assertEqual(variables, {})

    def test_empty_braces_with_whitespace(self):
        subsection = self._mk("This has {   } empty braces with whitespace.")
        variables = subsection.extract_variables()
        self.assertEqual(variables, {})

    def test_unmatched_braces(self):
        subsection = self._mk("This has { unmatched brace.")
        variables = subsection.extract_variables()
        self.assertEqual(variables, {})

    def test_list_type_variable(self):
        subsection = self._mk(
            "Type: {List: Choose from Grant or Cooperative agreement}."
        )
        variables = subsection.extract_variables()
        self.assertEqual(
            variables,
            {
                "choose_from_grant_or_cooperative_agreement": VariableInfo(
                    key="choose_from_grant_or_cooperative_agreement",
                    type="list",
                    label="Choose from Grant or Cooperative agreement",
                )
            },
        )

    def test_variable_in_markdown_context(self):
        subsection = self._mk("**Bold** and {variable} and _italic_.")
        variables = subsection.extract_variables()
        self.assertEqual(
            variables,
            {"variable": VariableInfo(key="variable", type="string", label="variable")},
        )

    def test_attr_list_block_not_wrapped_colon(self):
        subsection = self._mk("This is a paragraph.\n{: #an_id .a_class }")
        variables = subsection.extract_variables()
        self.assertEqual(variables, {})

    def test_attr_list_block_not_wrapped_class(self):
        subsection = self._mk("This is a paragraph.\n{.lead}")
        variables = subsection.extract_variables()
        self.assertEqual(variables, {})

    def test_attr_list_block_not_wrapped_id(self):
        subsection = self._mk("This is a paragraph.\n{#section-id}")
        variables = subsection.extract_variables()
        self.assertEqual(variables, {})

    def test_text_override_parameter_is_used_instead_of_instance_body(self):
        subsection = self._mk("Old body without vars")
        override = "New body with a {Fresh var}"
        variables = subsection.extract_variables(text=override)
        self.assertEqual(
            variables,
            {
                "fresh_var": VariableInfo(
                    key="fresh_var", type="string", label="Fresh var"
                ),
            },
        )


class ConditionalAnswerTests(TestCase):
    def setUp(self):
        self.guide = ContentGuide.objects.create(
            title="Guide", opdiv="CDC", group="bloom"
        )
        self.section = ContentGuideSection.objects.create(
            content_guide=self.guide, order=1, name="Section 1", html_id="sec-1"
        )

    def _mk(self, instructions: None, edit_mode="locked", order=1):
        """
        Helper to create a subsection with given instructions.
        Body is irrelevant for these tests.
        """
        return ContentGuideSubsection.objects.create(
            section=self.section,
            order=order,
            name="Sub 1",
            tag="h3",
            body="",
            instructions=instructions or "",
            edit_mode=edit_mode,
        )

    def test_no_instructions_returns_none_and_not_conditional(self):
        subsection = self._mk(instructions="")
        self.assertIsNone(subsection.conditional_answer)
        self.assertFalse(subsection.is_conditional)

    def test_yes_token_returns_true(self):
        subsection = self._mk("Include this section if (YES).")
        self.assertTrue(subsection.is_conditional)
        self.assertIs(subsection.conditional_answer, True)

    def test_no_token_returns_false(self):
        subsection = self._mk("Exclude this section if (NO).")
        self.assertTrue(subsection.is_conditional)
        self.assertIs(subsection.conditional_answer, False)

    def test_case_insensitive_matching(self):
        # neither should match because we require uppercase
        yes_sub = self._mk("Include when (yes).")
        no_sub = self._mk("Exclude when (nO).", order=2)

        self.assertIs(yes_sub.is_conditional, False)
        self.assertIs(no_sub.is_conditional, False)

    def test_parentheses_without_yes_no_are_ignored(self):
        subsection = self._mk("This text has (MAYBE) but no explicit YES or NO token.")
        self.assertIsNone(subsection.conditional_answer)
        self.assertFalse(subsection.is_conditional)

    def test_first_token_wins_if_both_yes_and_no_present(self):
        """
        Document the current behaviour: we use the first match in instructions.
        """
        subsection = self._mk("First (YES), then (NO).")
        self.assertIs(subsection.conditional_answer, True)

        subsection2 = self._mk("First (NO), then (YES).", order=2)
        self.assertIs(subsection2.conditional_answer, False)

    def test_non_yes_no_edit_mode_still_parses(self):
        """
        Even if edit_mode is not 'locked', the parsing still works.
        This just documents the current behaviour.
        """
        subsection = self._mk("Include for (YES).", edit_mode="full")
        self.assertIs(subsection.conditional_answer, True)
        self.assertTrue(subsection.is_conditional)


class ContentGuideSubsectionStatusTests(TestCase):
    def setUp(self):
        self.guide = ContentGuideInstance.objects.create(
            title="Guide Instance", opdiv="CDC", group="bloom"
        )
        self.section = ContentGuideSection.objects.create(
            content_guide_instance=self.guide,
            order=1,
            name="Section 1",
            html_id="sec-1",
        )

        self.subsection = ContentGuideSubsection.objects.create(
            section=self.section,
            order=1,
            name="Sub 1",
            tag="h3",
            body="Hello",
            instructions="",
            edit_mode="full",
        )

    def test_default_status_is_default(self):
        """New subsections start with status='default'."""
        self.assertEqual(self.subsection.status, "default")

    def test_mark_as_viewed_on_first_open_moves_default_to_viewed(self):
        """Helper should move default → viewed and persist it."""
        self.subsection.status = "default"
        self.subsection.save()

        self.subsection.mark_as_viewed_on_first_open()
        self.subsection.refresh_from_db()

        self.assertEqual(self.subsection.status, "viewed")

    def test_mark_as_viewed_on_first_open_noop_if_already_viewed(self):
        """Helper should be a no-op if status is already 'viewed'."""
        self.subsection.status = "viewed"
        self.subsection.save()

        self.subsection.mark_as_viewed_on_first_open()
        self.subsection.refresh_from_db()

        self.assertEqual(self.subsection.status, "viewed")

    def test_mark_as_viewed_on_first_open_noop_if_done(self):
        """Helper should be a no-op if status is already 'done'."""
        self.subsection.status = "done"
        self.subsection.save()

        self.subsection.mark_as_viewed_on_first_open()
        self.subsection.refresh_from_db()

        self.assertEqual(self.subsection.status, "done")
