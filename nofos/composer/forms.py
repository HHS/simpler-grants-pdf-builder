import json

from bloom_nofos.utils import cast_to_boolean
from django import forms
from martor.fields import MartorFormField

from nofos.forms import create_object_model_form

from .conditional.conditional_questions import CONDITIONAL_QUESTIONS
from .models import ContentGuide, ContentGuideInstance, ContentGuideSubsection
from .utils import get_opdiv_label

create_composer_form_class = create_object_model_form(ContentGuide)

CompareTitleForm = create_composer_form_class(["title"])


###########################################################
###################### SYSTEM ADMINS ######################
###########################################################


class ComposerSubsectionCreateForm(forms.ModelForm):
    body = MartorFormField(required=False)
    instructions = MartorFormField(required=False)

    class Meta:
        model = ContentGuideSubsection
        fields = [
            "name",
            "tag",
            "callout_box",
            "optional",
            "edit_mode",
            "body",
            "instructions",
        ]
        widgets = {
            "name": forms.TextInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        body = cleaned_data.get("body")
        tag = cleaned_data.get("tag")
        edit_mode = cleaned_data.get("edit_mode")

        # Validate tag present if name is provided
        if name and not tag:
            self.add_error("tag", "Sections with a name must have a heading level.")

        # Validate name is present if tag is selected
        if tag and not name:
            self.add_error("name", "Sections with a heading level must have a name.")

        # Validate at least one of name, body, or tag is provided
        if not name and not body and not tag:
            raise forms.ValidationError("Section must have either a name or content.")

        # Validate if edit_mode is "variables", that variables are present in body
        if edit_mode == "variables":
            posted_body = body or ""
            subsection: ContentGuideSubsection = self.instance
            if not subsection.extract_variables(text=posted_body):
                self.add_error(
                    "edit_mode",
                    "No {variables} found in section content. "
                    "Select another option or add variables.",
                )

        return cleaned_data


class ComposerSubsectionEditForm(forms.ModelForm):
    body = MartorFormField(required=False)

    class Meta:
        model = ContentGuideSubsection
        fields = ["optional", "edit_mode", "body"]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("edit_mode") == "variables":
            subsection: ContentGuideSubsection = self.instance
            posted_body = cleaned.get("body") or ""
            if not subsection.extract_variables(text=posted_body):
                self.add_error(
                    "edit_mode",
                    "No {variables} found in section content. "
                    "Select another option or add variables.",
                )
        return cleaned


class ComposerSubsectionInstructionsEditForm(forms.ModelForm):
    instructions = MartorFormField(required=False)

    class Meta:
        model = ContentGuideSubsection
        fields = ["instructions"]


###########################################################
###################### NOFO WRITERS #######################
###########################################################


class WriterInstanceStartForm(forms.Form):
    """
    Step 1: choose which ContentGuide to base the draft NOFO on.
    """

    parent = forms.ModelChoiceField(
        queryset=ContentGuide.objects.none(),
        widget=forms.RadioSelect,
        empty_label=None,
        label="Choose an approved content guide as a basis for your draft NOFO.",
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        qs = ContentGuide.objects.filter(
            archived__isnull=True,
            successor__isnull=True,
            status="published",
        )
        # if not a bloom user, only show content guides from that user's group
        if user and getattr(user, "group", None) != "bloom":
            qs = qs.filter(group=user.group)

        self.fields["parent"].queryset = qs.order_by("title")
        self.fields["parent"].label_from_instance = lambda obj: obj.title or obj


class WriterInstanceDetailsForm(forms.ModelForm):
    """
    Step 2: capture basic NOFO metadata for the new ContentGuideInstance.
    opdiv and title are required; others are optional.
    """

    class Meta:
        model = ContentGuideInstance
        fields = [
            "opdiv",
            "agency",
            "title",
            "short_name",
            "number",
            "activity_code",
            "federal_assistance_listing",
            "tagline",
            "author",
            "subject",
            "keywords",
        ]
        labels = {
            "opdiv": "Operating Division",
            "agency": "Agency",
            "title": "NOFO title",
            "short_name": "Short name",
            "number": "NOFO number",
            "activity_code": "Activity Code",
            "federal_assistance_listing": "Federal Assistance Listing",
            "tagline": "Tagline",
            "author": "Metadata Author",
            "subject": "Metadata Subject",
            "keywords": "Metadata Keywords",
        }
        help_texts = {
            "opdiv": "The HHS operating division responsible for this NOFO (eg, CDC).",
            "agency": "The agency or office within the operating division (eg, Global Health Center).",
            "short_name": "A name that makes it easier to find this NOFO later. It won’t be public.",
            "title": "The official name for this NOFO.",
            "number": "The opportunity number for this NOFO.",
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Make opdiv + title required
        self.fields["opdiv"].required = True
        self.fields["title"].required = True

        # Make "author" and "subject" into text fields, not text areas
        self.fields["author"].widget = forms.TextInput()
        self.fields["subject"].widget = forms.TextInput()

        # Prefill opdiv with the user's group for the initial GET only.
        # Don't overwrite user input on POST (self.is_bound == True).
        if not self.is_bound and user:
            self.fields["opdiv"].initial = get_opdiv_label(getattr(user, "group", ""))

        # Basic USWDS styling on widgets
        for name, field in self.fields.items():
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = (existing + " " + "usa-input").strip()


class WriterInstanceConditionalQuestionsForm(forms.Form):
    """
    A dynamic form that renders all conditional questions for a given page.
    """

    def __init__(
        self,
        *args,
        instance: ContentGuideInstance,
        page: int,
        **kwargs,
    ):
        self.instance = instance
        self.page = page
        super().__init__(*args, **kwargs)

        questions = CONDITIONAL_QUESTIONS.for_page(page)

        for question in questions:
            field_name = question.key
            self.fields[field_name] = forms.TypedChoiceField(
                label=question.label,
                choices=(
                    ("true", "Yes"),
                    ("false", "No"),
                ),
                coerce=cast_to_boolean,
                required=True,
                widget=forms.RadioSelect(
                    attrs={
                        "class": "usa-radio__input",
                    }
                ),
            )

            # Initial value from instance.conditional_questions
            existing = self.instance.get_conditional_question_answer(question.key)
            if existing is True:
                self.initial[field_name] = "true"
            elif existing is False:
                self.initial[field_name] = "false"

    def save(self):
        """
        Merge cleaned values into instance.conditional_questions, only touching
        keys for this page, and preserving others.
        """
        if not self.is_valid():
            raise ValueError("Cannot save an invalid form")

        # Start with existing ContentGuideInstance.conditional_questions JSON blob (or empty object)
        current = dict(self.instance.conditional_questions or {})

        # Restrict updates to questions on this page
        questions = CONDITIONAL_QUESTIONS.for_page(self.page)
        keys_for_page = {question.key for question in questions}

        for key in keys_for_page:
            value = self.cleaned_data.get(key, None)
            if value is None:
                current.pop(key, None)  # No answer -> drop the key
            else:
                current[key] = value  # Set as True / False

        self.instance.conditional_questions = current
        self.instance.save(update_fields=["conditional_questions", "updated"])
        return self.instance


class WriterInstanceSubsectionEditForm(forms.Form):
    """
    A dynamic form that renders the body field for a given ContentGuideSubsection, as well as individual
    fields for each variables in that subsection body if edit_mode = 'variables'.
    """

    def __init__(
        self,
        *args,
        subsection: ContentGuideSubsection,
        **kwargs,
    ):
        self.subsection = subsection
        super().__init__(*args, **kwargs)

        # the "Yes, keep it" radio does not actually get sent
        self.fields["hidden"] = forms.BooleanField(
            required=False,
            widget=forms.HiddenInput,
        )

        self.initial["hidden"] = self.subsection.hidden

        if self.subsection.edit_mode == "full":
            self.fields["body"] = MartorFormField(required=False)
            self.initial["body"] = self.subsection.body

        elif self.subsection.edit_mode == "variables":
            for variable_key, variable_info in self.subsection.get_variables().items():
                field_name = variable_key
                self.fields[field_name] = forms.CharField(
                    label=variable_info.get("label", variable_key),
                    required=False,
                    widget=forms.TextInput(
                        attrs={
                            "class": "usa-input",
                        }
                    ),
                )
                existing = self.subsection.get_variable_value(variable_key)
                if existing is not None:
                    self.initial[field_name] = existing

    def save(self):
        """
        Merge cleaned values into subsection.variables.
        """
        if not self.is_valid():
            raise ValueError("Cannot save an invalid form")

        # Update hidden field
        self.subsection.hidden = bool(self.cleaned_data.get("hidden", False))
        update_fields = ["hidden"]

        # Update body or variables based on edit_mode
        if self.subsection.edit_mode == "full":
            self.subsection.body = self.cleaned_data.get("body", "")
            update_fields.append("body")

        elif self.subsection.edit_mode == "variables":
            current = dict(self.subsection.get_variables() or {})

            for key in self.fields:
                # don't save "hidden" to JSON fields
                if key == "hidden":
                    continue
                updated = self.cleaned_data.get(key, None)
                existing = current.get(key, {})
                # Update with new value
                current[key] = {**existing, "value": updated}

            self.subsection.variables = json.dumps(current)
            update_fields.append("variables")

        self.subsection.save(update_fields=update_fields)
        return self.subsection
