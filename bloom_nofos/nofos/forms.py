from django import forms
from .models import Nofo, Subsection
from martor.fields import MartorFormField


class NofoNameForm(forms.ModelForm):
    class Meta:
        model = Nofo
        fields = ["title", "short_name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].required = True


class NofoCoachForm(forms.ModelForm):
    class Meta:
        model = Nofo
        fields = ["coach"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["coach"].required = True


class SubsectionForm(forms.ModelForm):
    body = MartorFormField(required=False)

    class Meta:
        model = Subsection
        fields = ["name", "body"]
        widgets = {
            "name": forms.TextInput(),
        }
