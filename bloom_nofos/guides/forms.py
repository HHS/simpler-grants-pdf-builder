from django import forms
from nofos.forms import create_object_model_form

from .models import ContentGuide, ContentGuideSubsection

create_content_guide_form_class = create_object_model_form(ContentGuide)

ContentGuideTitleForm = create_content_guide_form_class(["title"])


class ContentGuideSubsectionEditForm(forms.ModelForm):
    class Meta:
        model = ContentGuideSubsection
        fields = ["comparison_type"]  # only directly editable field from the model

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        values = self._get_diff_string_values()
        num_fields = len(values) + 1 if len(values) else 2

        for i in range(num_fields):
            self.fields[f"diff_string_{i}"] = forms.CharField(
                required=False,
                label=f"Required string {i + 1}",
                initial=values[i] if i < len(values) else "",
            )

    def _get_diff_string_values(self):
        """Get list of input values from form data (if bound) or instance."""
        if self.is_bound:
            return [
                v
                for i in range(100)
                if (v := self.data.get(f"diff_string_{i}")) is not None
            ]
        return self.instance.diff_strings or []

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Pull only non-empty strings in order
        diff_strings = [
            self.cleaned_data[key].strip()
            for key in self.cleaned_data
            if key.startswith("diff_string_") and self.cleaned_data[key].strip()
        ]

        instance.diff_strings = diff_strings

        if commit:
            instance.save()

        return instance
