from django import forms

from .models import ContentGuide


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
