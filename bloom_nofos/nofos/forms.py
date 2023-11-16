from django import forms
from .models import Subsection
from martor.fields import MartorFormField


class SubsectionForm(forms.ModelForm):
    body = MartorFormField(required=False)

    class Meta:
        model = Subsection
        fields = ["name", "body"]
        widgets = {
            "name": forms.TextInput(),
        }
