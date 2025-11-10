from django.test import TestCase

from composer.forms import ComposerSubsectionEditForm
from composer.models import (
    ContentGuide,
    ContentGuideSection,
    ContentGuideSubsection,
)


class SubsectionEditFormVariablesTests(TestCase):
    def setUp(self):
        self.guide = ContentGuide.objects.create(title="G", opdiv="CDC", group="bloom")
        self.section = ContentGuideSection.objects.create(
            document=self.guide, order=1, name="S"
        )
        self.ss = ContentGuideSubsection.objects.create(
            section=self.section,
            order=1,
            name="Intro",
            tag="h4",
            body="Initial body",
            edit_mode="full",
        )

    def test_variables_validation_uses_posted_body(self):
        form = ComposerSubsectionEditForm(
            data={"edit_mode": "variables", "body": "Has {Variable} now"},
            instance=self.ss,
        )
        self.assertTrue(form.is_valid(), form.errors.as_json())

    def test_variables_validation_errors_when_no_vars(self):
        form = ComposerSubsectionEditForm(
            data={"edit_mode": "variables", "body": "No placeholders here"},
            instance=self.ss,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("edit_mode", form.errors)


class SubsectionCreateFormVariablesTests(TestCase):
    def setUp(self):
        self.guide = ContentGuide.objects.create(title="G", opdiv="CDC", group="bloom")
        self.section = ContentGuideSection.objects.create(
            document=self.guide, order=1, name="S"
        )

    def test_variables_validation_uses_posted_body(self):
        form = ComposerSubsectionEditForm(
            data={
                "section": self.section.id,
                "order": 1,
                "name": "New Sub",
                "tag": "h4",
                "edit_mode": "variables",
                "body": "Has {Variable} now",
            }
        )
        self.assertTrue(form.is_valid(), form.errors.as_json())

    def test_variables_validation_errors_when_no_vars(self):
        form = ComposerSubsectionEditForm(
            data={
                "section": self.section.id,
                "order": 1,
                "name": "New Sub",
                "tag": "h4",
                "edit_mode": "variables",
                "body": "No placeholders here",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("edit_mode", form.errors)
