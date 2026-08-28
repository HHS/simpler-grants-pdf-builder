from django.test import SimpleTestCase

from nofos.forms import SubsectionCreateForm, SubsectionEditForm


class SubsectionFormBodyNormalizationTests(SimpleTestCase):
    form_classes = (SubsectionCreateForm, SubsectionEditForm)

    def build_form(self, form_class, body):
        data = {
            "name": "",
            "tag": "",
            "callout_box": "",
            "body": body,
        }
        if form_class is SubsectionEditForm:
            data["html_class"] = ""

        form = form_class(data=data)
        self.assertTrue(form.is_valid(), form.errors)
        return form

    def test_normalizes_ballot_box_to_white_medium_square(self):
        for form_class in self.form_classes:
            with self.subTest(form_class=form_class.__name__):
                form = self.build_form(form_class, "☐ Work plan")
                self.assertEqual(form.cleaned_data["body"], "◻ Work plan")

    def test_preserves_unrelated_markdown_characters_and_entities(self):
        samples = (
            "Literal &nbsp; entity",
            "Nonbreaking\u00a0space",
            "Standalone ¨ character",
            "Delete \x7f character",
        )

        for form_class in self.form_classes:
            for body in samples:
                with self.subTest(form_class=form_class.__name__, body=repr(body)):
                    form = self.build_form(form_class, body)
                    self.assertEqual(form.cleaned_data["body"], body)
