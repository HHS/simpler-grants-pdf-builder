from django import forms
from martor.fields import MartorFormField

from .models import Nofo, Section, Subsection


def create_nofo_form_class(field_arr, not_required_field_labels=None):
    """
    Factory function to create Nofo form classes dynamically.
    """

    class _NofoForm(forms.ModelForm):
        class Meta:
            model = Nofo
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

    return _NofoForm


# Creating form classes
NofoNameForm = create_nofo_form_class(
    ["title", "short_name"], not_required_field_labels=["Short name"]
)

NofoCoachForm = create_nofo_form_class(["coach"])
NofoNumberForm = create_nofo_form_class(["number"])
NofoOpDivForm = create_nofo_form_class(["opdiv"])
NofoAgencyForm = create_nofo_form_class(["agency"])
NofoSubagencyForm = create_nofo_form_class(["subagency"])
NofoSubagency2Form = create_nofo_form_class(["subagency2"])
NofoApplicationDeadlineForm = create_nofo_form_class(["application_deadline"])
NofoTaglineForm = create_nofo_form_class(["tagline"])
NofoThemeForm = create_nofo_form_class(["theme"])
NofoCoverForm = create_nofo_form_class(["cover"])
NofoStatusForm = create_nofo_form_class(["status"])
NofoIconPathForm = create_nofo_form_class(
    ["icon_path"], not_required_field_labels=["Icon path"]
)


# this one needs a custom field and a custom widget so don't use the factory function
class NofoMetadataForm(forms.ModelForm):
    class Meta:
        model = Nofo
        fields = ["author", "subject", "keywords"]
        widgets = {
            "author": forms.TextInput(),
            "subject": forms.TextInput(),
        }


# this one needs a custom field and a custom widget so don't use the factory function
class SubsectionForm(forms.ModelForm):
    body = MartorFormField(required=False)

    class Meta:
        model = Subsection
        fields = ["name", "tag", "callout_box", "html_class", "body"]
        widgets = {
            "name": forms.TextInput(),
        }


class InsertOrderSpaceForm(forms.Form):
    section = forms.ModelChoiceField(
        queryset=Section.objects.all(), required=True, label="Section", disabled=False
    )
    order = forms.ChoiceField(choices=[], required=True, label="Insert space at order")

    def __init__(self, *args, **kwargs):
        super(InsertOrderSpaceForm, self).__init__(*args, **kwargs)

        if "initial" in kwargs:
            self.fields["section"].disabled = True

        section_id = kwargs.get("initial")["section"].id
        subsection_orders = (
            Subsection.objects.filter(section_id=section_id)
            .values_list("order", flat=True)
            .order_by("order")
        )

        choices = []

        for order in subsection_orders:
            choices.append((order, str(order)))

        self.fields["order"].choices = choices
