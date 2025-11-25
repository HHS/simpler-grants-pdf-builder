from django import forms
from martor.fields import MartorFormField

from nofos.forms import create_object_model_form

from .models import ContentGuide, ContentGuideInstance, ContentGuideSubsection

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

    TODO: should only show 'published' Content Guides, but this is not ready yet
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
            # status="published", # TODO: only show published
        )
        # if not a bloom user, only show content guides from that user's group
        if user and getattr(user, "group", None) != "bloom":
            qs = qs.filter(group=user.group)

        self.fields["parent"].queryset = qs.order_by("title")
        self.fields["parent"].label_from_instance = lambda obj: obj.title or obj


class WriterInstanceDetailsForm(forms.ModelForm):
    """
    Step 2: capture basic NOFO metadata for the new ContentGuideInstance.
    Agency is set from the user's group in the view, but displayed read-only.
    """

    class Meta:
        model = ContentGuideInstance
        fields = ["short_name", "title", "number"]
        labels = {
            "short_name": "Short name",
            "title": "NOFO title",
            "number": "NOFO number",
        }
        help_texts = {
            "short_name": "A name that makes it easier to find this NOFO later. It won’t be public.",
            "title": "The official name for this NOFO.",
            "number": "The opportunity number for this NOFO.",
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # You can customize widgets / placeholders here if you like:
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "usa-input")
