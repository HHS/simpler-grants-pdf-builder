from __future__ import annotations

import json
import re
from typing import Dict

from bloom_nofos.markdown_extensions.curly_variables import CURLY_VARIABLE_PATTERN
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.db import models
from django.urls import reverse
from martor.models import MartorField
from slugify import slugify

from nofos.models import BaseNofo, BaseSection, BaseSubsection


class ContentGuide(BaseNofo):
    """
    A template document created by System Admins that NOFO Writers will later use.
    Guides remain editable by admins even when ACTIVE.
    """

    STATUS_CHOICES = [("draft", "Draft"), ("published", "Published")]

    title = models.TextField(
        "Content Guide title",
        max_length=250,
        validators=[MaxLengthValidator(250)],
        blank=True,
        help_text="The official name for this NOFO. It will be public when the NOFO is published.",
    )

    status = models.CharField(
        max_length=32,
        validators=[MaxLengthValidator(32)],
        choices=STATUS_CHOICES,
        blank=False,
        default="draft",
        help_text="Visibility/lifecycle for writers. NOFO Writers only see Published.",
    )

    class Meta:
        ordering = ["-created"]

    def __str__(self) -> str:
        return "(ContentGuide) {}".format(self.title)

    def get_admin_url(self):
        """
        Returns the admin URL for this ContentGuide.
        """
        return reverse("admin:composer_contentguide_change", args=(self.id,))

    def get_absolute_url(self):
        """
        Returns the main edit view for this ContentGuide.
        """
        return reverse("composer:composer_document_redirect", args=(self.id,))


class ContentGuideInstance(BaseNofo):
    """
    An instance of a ContentGuide, to be filled out by NOFO Writers.
    Guides remain editable by admins even when ACTIVE.
    """

    title = models.TextField(
        "Content Guide title",
        max_length=250,
        validators=[MaxLengthValidator(250)],
        blank=True,
        help_text="The official name for this NOFO. It will be public when the NOFO is published.",
    )

    # status is a required field, so let's just make it a "Draft"
    status = models.CharField(
        max_length=32,
        validators=[MaxLengthValidator(32)],
        choices=[
            ("draft", "Draft"),
        ],
        blank=False,
        default="draft",
    )

    short_name = models.CharField(
        max_length=511,
        validators=[MaxLengthValidator(511)],
        blank=True,
        help_text="A name that makes it easier to find this NOFO in a list. It won’t be public.",
    )

    number = models.CharField(
        "Opportunity number",
        max_length=200,
        validators=[MaxLengthValidator(200)],
        blank=True,
        help_text="The official opportunity number for this NOFO.",
    )

    agency = models.CharField(
        "Agency",
        max_length=511,
        validators=[MaxLengthValidator(511)],
        blank=True,
        help_text="The agency within the operating division (eg, Bureau of Health Workforce)",
    )

    activity_code = models.CharField(
        "Activity code",
        max_length=511,
        validators=[MaxLengthValidator(511)],
        blank=True,
        help_text="Used to identify related NOFO types or templates, if applicable.",
    )

    federal_assistance_listing = models.CharField(
        "Federal assistance listing",
        max_length=511,
        validators=[MaxLengthValidator(511)],
        blank=True,
        help_text="Associated assistance listing for this program.",
    )

    statutory_authority = models.CharField(
        "Statutory authority",
        max_length=511,
        validators=[MaxLengthValidator(511)],
        blank=True,
        help_text="Primary authority or legislation governing this program’s funding.",
    )

    tagline = models.TextField(
        "NOFO tagline",
        blank=True,
        help_text="A short phrase that describes your program. Leave blank if not known.",
    )

    author = models.TextField(
        "NOFO author",
        blank=True,
        help_text="Request your subagency name (e.g., OPHDST) instead of CDC as the author. (Optional)",
    )

    subject = models.TextField(
        "NOFO subject",
        blank=True,
        help_text='Add a one-line statement, 25 words or less. eg: "A notice of funding opportunity from the [Agency or OpDiv] about/on/to [the purpose of the NOFO]." (Optional).',
    )

    keywords = models.TextField(
        "NOFO keywords",
        blank=True,
        help_text="Suggest keywords to help someone get the overall sense of this opportunity. Provide 5 to 10 keywords, separate them by commas. (Optional)",
    )

    conditional_questions = models.JSONField(
        default=dict,
        blank=True,
        help_text="Yes/No answers keyed by question key (e.g. intergov_review: true).",
    )

    # convenience helper for getting 1 conditional_question value at a time
    def get_conditional_question_answer(self, key: str, default=None):
        return self.conditional_questions.get(key, default)

    parent = models.ForeignKey(
        ContentGuide,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="instances",
        help_text="The original Content Guide this instance was created from.",
    )

    class Meta:
        ordering = ["-created"]

    def __str__(self) -> str:
        return "(ContentGuideInstance) {}".format(self.title or self.short_name)

    def get_admin_url(self):
        """
        Returns the admin URL for this ContentGuideInstance.
        """
        return reverse("admin:composer_contentguideinstance_change", args=(self.id,))

    def get_absolute_url(self):
        """
        Returns the main edit view for this ContentGuideInstance.
        """
        return reverse("composer:writer_instance_redirect", args=(self.id,))


class ContentGuideSection(BaseSection):
    """
    Ordered section of a Content Guide or a Content Guide Instance.
    """

    class Meta:
        ordering = ["order"]
        unique_together = ("content_guide", "content_guide_instance", "order")
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(
                        content_guide__isnull=False, content_guide_instance__isnull=True
                    )
                    | models.Q(
                        content_guide__isnull=True, content_guide_instance__isnull=False
                    )
                ),
                name="section_has_exactly_one_parent",
            )
        ]

    content_guide = models.ForeignKey(
        ContentGuide,
        on_delete=models.CASCADE,
        related_name="sections",
        null=True,
        blank=True,
    )

    content_guide_instance = models.ForeignKey(
        ContentGuideInstance,
        on_delete=models.CASCADE,
        related_name="sections",
        null=True,
        blank=True,
    )

    def get_document(self):
        return self.content_guide or self.content_guide_instance

    @property
    def document_id(self):
        document = self.get_document()
        return document.id

    def get_subsection_model(self):
        return ContentGuideSubsection

    def get_sibling_queryset(self):
        document = self.get_document()
        return document.sections.all()

    def get_document_field_name(self):
        """Return the parent document field name: 'content_guide' or 'content_guide_instance'."""
        if self.content_guide_id is not None:
            return "content_guide"
        if self.content_guide_instance_id is not None:
            return "content_guide_instance"
        # This should never happen
        raise ValueError("Section has no parent document.")

    @classmethod
    def get_document_field_name_for(cls, document):
        """Return the document field name for a 'passed in' document. This is useful during _build_document."""
        # Match by type
        if isinstance(document, ContentGuide):
            return "content_guide"
        if isinstance(document, ContentGuideInstance):
            return "content_guide_instance"

        raise ValueError(
            f"Cannot determine parent field for document type: {type(document).__name__}"
        )


class ContentGuideSubsection(BaseSubsection):
    """
    Content block within a Content Guide.
    Supports different edit behaviors for NOFO Writers, includes optional instructions.
    """

    class Meta:
        ordering = ["order"]
        unique_together = ("section", "order")

    section = models.ForeignKey(
        ContentGuideSection, on_delete=models.CASCADE, related_name="subsections"
    )

    EDIT_MODE_CHOICES = [
        ("full", "Edit all text"),
        ("variables", "Edit variables"),
        ("locked", "Content is locked"),
    ]

    edit_mode = models.CharField(
        max_length=16,
        choices=EDIT_MODE_CHOICES,
        default="locked",
        help_text="Decide how NOFO Writers can edit this subsection.",
    )

    WRITER_STATUS_CHOICES = [
        ("default", "Not started"),
        ("viewed", "Viewed at least once"),
        ("done", "Done editing"),
    ]

    status = models.CharField(
        max_length=16,
        choices=WRITER_STATUS_CHOICES,
        default="default",
        help_text=(
            "Subsection progress status field used by NOFO Writers."
            "Only relevant for subsections that belong to a ContentGuideInstance."
        ),
    )

    optional = models.BooleanField(
        default=False,
        help_text="Decide if this subsection is required, or can be hidden by NOFO Writers",
    )

    hidden = models.BooleanField(
        default=False,
        help_text="If optional, whether the subsection is currently hidden by the NOFO Writer.",
    )

    # Admin-only Markdown field for guidance.
    instructions = MartorField(
        "Content of subsection",
        blank=True,
        help_text="Guidance for NOFO Writers on filling out this section.",
    )

    # Stored as TextField instead of JSONField to ensure no DB sorting or re-ordering happens.
    # Values will JSON-encoded/decoded upon retrieval/storage.
    variables = models.TextField(
        default="",
        blank=True,
        help_text="Variables from the subsection body, keyed by variable key. If ContentGuideInstance, also includes writer-provided values.",
    )

    def get_variables(self) -> dict:
        if not self.variables:
            return {}
        try:
            return json.loads(self.variables)
        except json.JSONDecodeError as e:
            return {}

    # ---------- Conditional answer helpers ---------- #

    _YES_NO_PATTERN = re.compile(r"\((YES|NO)\)")

    def _find_yes_no_string(self) -> str | None:
        """
        Find the exact strings "(YES)" or "(NO)" inside the instructions.

        Returns "YES", "NO", or None if nothing found.
        """
        if not self.instructions:
            return None

        token = self._YES_NO_PATTERN.search(self.instructions)
        if not token:
            return None

        return token.group(1).upper()

    @property
    def conditional_answer(self) -> bool | None:
        """
        Boolean representation of the (YES)/(NO) token in instructions.

        Returns:
            (YES) -> True
            (NO) -> False
            No token -> None
        """
        token = self._find_yes_no_string()
        if token == "YES":
            return True
        if token == "NO":
            return False
        return None

    @property
    def is_conditional(self) -> bool:
        return self.conditional_answer is not None

    # ---------- Variable helpers ---------- #

    # Unified pattern - no nested braces allowed
    _VAR_PATTERN = re.compile(CURLY_VARIABLE_PATTERN)

    def extract_variables(self, text: str | None = None) -> Dict[str, dict]:
        """
        Parse this subsection's body for variable placeholders.

        Syntax:
          {Prompt text}            -> string variable
          {List: label text}       -> list variable
        Escape literal braces with '\\{' or '\\}'.

        Returns:
            Dict{"total_budget_amount": {"key": "total_budget_amount", "type": "string", "label": "Enter total budget amount"}}
        """
        text = (text if text is not None else self.body) or ""
        results: Dict[str, dict] = {}
        used_keys = set()

        for m in self._VAR_PATTERN.finditer(text):
            variable = m.group(1).strip()

            var_type = "string"
            label = variable

            if ":" in variable:
                head, tail = variable.split(":", 1)
                if head.strip().lower() == "list":
                    var_type = "list"
                    label = tail.strip()

            # slugify the label into a key
            base_key = slugify(label, separator="_")
            if not base_key:
                base_key = "var"

            key = base_key
            i = 2
            # Deduplicate keys if repeated labels
            while key in used_keys:
                key = f"{base_key}_{i}"
                i += 1

            used_keys.add(key)
            results[key] = {"key": key, "type": var_type, "label": label}

        return results

    def render_with_escapes_cleaned(self, text: str) -> str:
        """
        Replace escaped '\\{' and '\\}' with literal braces for display.
        """
        return text.replace(r"\{", "{").replace(r"\}", "}")

    def get_variable_value(self, key: str) -> str | None:
        """
        Get the value for a variable by key.

        Returns:
            The variable value (str or List[str]) if set, else None.
        """
        var_info = self.get_variables().get(key)
        if not var_info:
            return None
        return var_info.get("value")

    # ---------- Subsection status helpers ---------- #

    def mark_as_viewed_on_first_open(self):
        """
        Change subsection.status to "viewed". No-op if already viewed or done.
        """
        if self.status == "default":
            self.status = "viewed"
            self.save(update_fields=["status"])

    # ---------- Validation ---------- #

    def clean(self):
        """
        Ensure that VARIABLE mode subsections actually contain variables.
        """
        super().clean()
        if self.edit_mode == "variables":
            if not self._VAR_PATTERN.search(self.body or ""):
                raise ValidationError(
                    {
                        "body": "'Edit certain text only' selected but no {variables} found in section content."
                    }
                )
