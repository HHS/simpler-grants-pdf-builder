from django import forms
from martor.fields import MartorFormField

from .models import (
    DESIGNER_CHOICES,
    STATUS_CHOICES,
    THEME_CHOICES,
    Nofo,
    Section,
    Subsection,
)
from .utils import get_icon_path_choices


def create_object_model_form(model_class):
    """
    Returns a function that builds a ModelForm for `model_class` using given field names and optional required label overrides.
    """

    def _form_factory(field_names, not_required_labels=None):
        class _ModelForm(forms.ModelForm):
            class Meta:
                model = model_class
                fields = field_names

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                for field in self.fields.values():
                    if not_required_labels and field.label in not_required_labels:
                        field.required = False
                    else:
                        field.required = True

        _ModelForm.__name__ = f"{model_class.__name__}FormFor_{'_'.join(field_names)}"
        return _ModelForm

    return _form_factory


create_nofo_form_class = create_object_model_form(Nofo)


NofoImportTitleForm = create_nofo_form_class(
    ["title", "short_name"], not_required_labels=["Short name"]
)
NofoTitleForm = create_nofo_form_class(["title"])
NofoShortNameForm = create_nofo_form_class(["short_name"])
NofoAgencyForm = create_nofo_form_class(["agency"])
NofoApplicationDeadlineForm = create_nofo_form_class(["application_deadline"])
NofoNumberForm = create_nofo_form_class(["number"])
NofoGroupForm = create_nofo_form_class(["group"])
NofoOpDivForm = create_nofo_form_class(["opdiv"])
NofoSubagencyForm = create_nofo_form_class(
    ["subagency"], not_required_labels=["Subagency"]
)
NofoSubagency2Form = create_nofo_form_class(
    ["subagency2"], not_required_labels=["Subagency 2"]
)
NofoTaglineForm = create_nofo_form_class(["tagline"])
NofoBeforeYouBeginForm = create_nofo_form_class(["before_you_begin"])


# Nofo status form: same options but with a divider inserted after "published"
class NofoStatusForm(forms.ModelForm):
    class Meta:
        model = Nofo
        fields = ["status"]

    def __init__(self, *args, **kwargs):
        super(NofoStatusForm, self).__init__(*args, **kwargs)

        # Find the index of "published" so we can insert a divider after it
        published_index = next(
            (i for i, (value, _) in enumerate(STATUS_CHOICES) if value == "published"),
            None,
        )

        if published_index is not None:
            updated_choices = STATUS_CHOICES[
                : published_index + 1
            ]  # Include "published"
            updated_choices.append(("", "──────────"))  # Add the divider
            updated_choices.extend(
                STATUS_CHOICES[published_index + 1 :]
            )  # Add the remaining items

            self.fields["status"].choices = updated_choices  # Assign modified choices


# Nofo designer form
class NofoCoachDesignerForm(forms.ModelForm):
    class Meta:
        model = Nofo
        fields = ["coach", "designer"]

    def __init__(self, *args, user=None, **kwargs):
        super(NofoCoachDesignerForm, self).__init__(*args, **kwargs)

        # Initialize choices with an empty option
        initial_choices = [("", "---------")]

        # Adjust designer choices based on user group
        if user and user.group != "bloom":
            # Filter designers by user's group prefix
            self.fields["designer"].choices = initial_choices + [
                (choice, label)
                for choice, label in DESIGNER_CHOICES
                if choice.startswith(user.group)
            ]
        else:
            # If user is from 'bloom' or no user is provided, show all designers
            self.fields["designer"].choices = initial_choices + [
                (
                    code,
                    (
                        name
                        if "bloom" in code
                        else "{} ({})".format(name, code.split("-")[0].upper())
                    ),
                )
                for code, name in DESIGNER_CHOICES
            ]


class NofoThemeOptionsForm(forms.ModelForm):
    class Meta:
        model = Nofo
        fields = ["theme", "cover", "icon_style"]

    def __init__(self, *args, user=None, **kwargs):
        super(NofoThemeOptionsForm, self).__init__(*args, **kwargs)

        # -------- Filter theme choices into optgroups by OpDiv
        theme_categories_dict = {}
        for value, label in THEME_CHOICES:
            opdiv = label.split(" ")[0]
            theme_categories_dict.setdefault(opdiv, []).append((value, label))

        group_key = user.group.upper() if user and hasattr(user, "group") else None

        if group_key and group_key != "BLOOM" and group_key in theme_categories_dict:
            theme_categories = {group_key: theme_categories_dict[group_key]}
        else:
            theme_categories = theme_categories_dict

        # Convert optgroup dict into Django-style optgroup choices
        optgroup_choices = [
            (opdiv, options) for opdiv, options in theme_categories.items()
        ]
        self.fields["theme"].choices = optgroup_choices

        # -------- Filter icon_style choices based on selected theme
        if self.instance and self.instance.theme:
            self.fields["icon_style"].choices = get_icon_path_choices(
                self.instance.theme
            )


class NofoCoverImageForm(forms.ModelForm):
    class Meta:
        model = Nofo
        fields = ["cover_image", "cover_image_alt_text"]


# this one needs a custom field and a custom widget so don't use the factory function
class NofoMetadataForm(forms.ModelForm):
    class Meta:
        model = Nofo
        fields = ["author", "subject", "keywords"]
        widgets = {
            "author": forms.TextInput(),
            "subject": forms.TextInput(),
        }


# body needs a custom field and a custom widget so don't use the factory function
class SubsectionEditForm(forms.ModelForm):
    body = MartorFormField(required=False)

    class Meta:
        model = Subsection
        fields = ["name", "tag", "callout_box", "html_class", "body"]
        widgets = {
            "name": forms.TextInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        tag = cleaned_data.get("tag")

        if tag and not name:
            self.add_error("name", "Subsection name can’t be empty.")

        return cleaned_data


class SubsectionCreateForm(forms.ModelForm):
    body = MartorFormField(required=False)

    class Meta:
        model = Subsection
        fields = ["name", "tag", "callout_box", "body"]
        widgets = {
            "name": forms.TextInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        body = cleaned_data.get("body")
        tag = cleaned_data.get("tag")

        if name and not tag:
            self.add_error("tag", "Subsections with a name must have a heading level.")

        if tag and not name:
            self.add_error("name", "Subsections with a heading level must have a name.")

        if not name and not body and not tag:
            raise forms.ValidationError(
                "Subsection must have either a name or content."
            )

        return cleaned_data


# Simple form for URL input
class CheckNOFOLinkSingleForm(forms.Form):
    url = forms.URLField(
        label="Check this URL",
        max_length=2048,
        required=True,
        assume_scheme="https",
    )


# Simple form for searching for a NOFO
class NofoSearchForm(forms.Form):
    query = forms.CharField(
        label="Search NOFOs",
        required=False,
        help_text="Enter any part of a NOFO name, number, or OpDiv.",
        widget=forms.TextInput(
            attrs={
                "class": "usa-input usa-input border-2px",
            }
        ),
    )


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
