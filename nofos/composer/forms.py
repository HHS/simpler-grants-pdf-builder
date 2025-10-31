from django import forms
from martor.fields import MartorFormField

from nofos.forms import create_object_model_form

from .models import ContentGuide, ContentGuideSubsection

create_composer_form_class = create_object_model_form(ContentGuide)

CompareTitleForm = create_composer_form_class(["title"])


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
