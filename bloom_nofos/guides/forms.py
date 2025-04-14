from django import forms

from .models import ContentGuide, ContentGuideSubsection


# TODO: genericize this
def create_content_guide_form_class(field_arr, not_required_field_labels=None):
    """
    Factory function to create Nofo form classes dynamically.
    """

    class _CGForm(forms.ModelForm):
        class Meta:
            model = ContentGuide
            fields = field_arr

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            for field in self.fields.values():
                if (
                    not_required_field_labels
                    and field.label in not_required_field_labels
                ):
                    field.required = False
                else:
                    field.required = True

    return _CGForm


ContentGuideTitleForm = create_content_guide_form_class(["title"])


class ContentGuideSubsectionEditForm(forms.ModelForm):
    diff_string_1 = forms.CharField(required=False, label="Required string 1")
    diff_string_2 = forms.CharField(required=False, label="Required string 2")

    class Meta:
        model = ContentGuideSubsection
        fields = ["comparison_type"]  # only directly editable field from the model

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Pre-populate string fields if instance has them
        diff_strings = self.instance.diff_strings or []
        self.fields["diff_string_1"].initial = (
            diff_strings[0] if len(diff_strings) > 0 else ""
        )
        self.fields["diff_string_2"].initial = (
            diff_strings[1] if len(diff_strings) > 1 else ""
        )

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Overwrite diff_strings with what’s in the form fields
        diff_string_1 = self.cleaned_data.get("diff_string_1")
        diff_string_2 = self.cleaned_data.get("diff_string_2")

        instance.diff_strings = [s for s in [diff_string_1, diff_string_2] if s]

        if commit:
            instance.save()

        return instance
