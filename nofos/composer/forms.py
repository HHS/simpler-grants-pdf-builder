from django import forms
from martor.fields import MartorFormField

from nofos.forms import create_object_model_form

from .models import ContentGuide, ContentGuideSubsection

create_composer_form_class = create_object_model_form(ContentGuide)

CompareTitleForm = create_composer_form_class(["title"])


class ComposerSubsectionCreateForm(forms.ModelForm):
    body = MartorFormField(required=False)
    instructions = MartorFormField(required=False)

    class Meta:
        model = ContentGuideSubsection
        fields = ["name", "tag", "callout_box", "edit_mode", "body", "instructions"]
        widgets = {
            "name": forms.TextInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        body = cleaned_data.get("body")
        tag = cleaned_data.get("tag")
        edit_mode = cleaned_data.get("edit_mode")

        # Validate tag present if name is provided
        if name and not tag:
            self.add_error("tag", "Subsections with a name must have a Heading level.")

        # Validate name is present if tag is selected
        if tag and not name:
            self.add_error("name", "Subsections with a heading level must have a name.")

        # Validate at least one of name, body, or tag is provided
        if not name and not body and not tag:
            raise forms.ValidationError(
                "Subsection must have either a name or content."
            )

        # Validate if edit_mode is "variables", that variables are present in body
        if edit_mode == "variables":
            posted_body = body or ""
            if not ContentGuideSubsection.extract_variables(text=posted_body):
                self.add_error(
                    "edit_mode",
                    "No {…} variables found in this subsection’s body. "
                    "Switch to 'Edit all text' or add variables.",
                )

        return cleaned_data


class ComposerSubsectionEditForm(forms.ModelForm):
    body = MartorFormField(required=False)

    class Meta:
        model = ContentGuideSubsection
        fields = ["edit_mode", "body"]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("edit_mode") == "variables":
            subsection: ContentGuideSubsection = self.instance
            posted_body = cleaned.get("body") or ""
            if not subsection.extract_variables(text=posted_body):
                self.add_error(
                    "edit_mode",
                    "No {…} variables found in this subsection’s body. "
                    "Switch to 'Edit all text' or add variables.",
                )
        return cleaned


class ComposerSubsectionInstructionsEditForm(forms.ModelForm):
    instructions = MartorFormField(required=False)

    class Meta:
        model = ContentGuideSubsection
        fields = ["instructions"]
