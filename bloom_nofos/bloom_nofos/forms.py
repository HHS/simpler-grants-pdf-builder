from django import forms


class DocraptorTestModeForm(forms.Form):
    docraptor_test_mode = forms.BooleanField(
        required=False, label="Docraptor test mode"
    )
