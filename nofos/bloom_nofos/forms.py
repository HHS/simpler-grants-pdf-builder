from django import forms


class DocraptorTestModeForm(forms.Form):
    docraptor_live_mode = forms.BooleanField(
        required=False, label="Docraptor Live Mode"
    )
