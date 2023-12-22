from django import forms
from .models import Nofo, Subsection
from martor.fields import MartorFormField


class BaseNofoRequiredFieldForm(forms.ModelForm):
    """
    Create a BaseNofoRequiredFieldForm that sets required=True for fields that are not specified in "not_required_field_labels"
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not (
                hasattr(self, "not_required_field_labels")
                and field.label in self.not_required_field_labels
            ):
                field.required = True


class NofoNameForm(BaseNofoRequiredFieldForm):
    not_required_field_labels = ["Short name"]

    class Meta:
        model = Nofo
        fields = ["title", "short_name"]


class NofoCoachForm(BaseNofoRequiredFieldForm):
    class Meta:
        model = Nofo
        fields = ["coach"]


class NofoNumberForm(BaseNofoRequiredFieldForm):
    class Meta:
        model = Nofo
        fields = ["number"]


class NofoThemeForm(BaseNofoRequiredFieldForm):
    class Meta:
        model = Nofo
        fields = ["theme"]


class SubsectionForm(forms.ModelForm):
    body = MartorFormField(required=False)

    class Meta:
        model = Subsection
        fields = ["name", "body"]
        widgets = {
            "name": forms.TextInput(),
        }
