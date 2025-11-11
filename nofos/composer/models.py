from __future__ import annotations

import re
from typing import List

from bloom_nofos.markdown_extensions.curly_variables import CURLY_VARIABLE_PATTERN
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.db import models
from martor.models import MartorField
from slugify import slugify

from nofos.models import BaseNofo, BaseSection, BaseSubsection


class ContentGuide(BaseNofo):
    """
    A template document created by System Admins that NOFO Writers will later use.
    Guides remain editable by admins even when ACTIVE.
    """

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("retired", "Retired"),
    ]

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
        help_text="Visibility/lifecycle for writers. NOFO Writers only see ACTIVE.",
    )

    class Meta:
        ordering = ["-created"]

    def __str__(self) -> str:  # pragma: no cover
        return self.title


class ContentGuideSection(BaseSection):
    """
    Ordered section of a Content Guide.
    """

    class Meta:
        ordering = ["order"]
        unique_together = ("document", "order")

    document = models.ForeignKey(
        ContentGuide,
        on_delete=models.CASCADE,
        related_name="sections",
    )

    def get_document(self):
        return self.document

    def get_subsection_model(self):
        return ContentGuideSubsection

    def get_sibling_queryset(self):
        return self.document.sections.all()


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
        ("yes_no", "Select Yes/No only"),
        ("locked", "Content is locked"),
    ]

    edit_mode = models.CharField(
        max_length=16,
        choices=EDIT_MODE_CHOICES,
        default="locked",
        help_text="Decide how NOFO Writers can edit this subsection.",
    )

    # Admin-only Markdown field for guidance.
    instructions = MartorField(
        "Content of subsection",
        blank=True,
        help_text="Guidance for NOFO Writers on filling out this section.",
    )

    # Default include flag for yes/no mode.
    enabled = models.BooleanField(
        default=True,
        help_text="Whether to show this section in the content guide.",
    )

    # ---------- Variable parsing helpers ---------- #

    # Unified pattern - no nested braces allowed
    _VAR_PATTERN = re.compile(CURLY_VARIABLE_PATTERN)

    def extract_variables(self, text: str | None = None) -> List[dict]:
        """
        Parse this subsection's body for variable placeholders.

        Syntax:
          {Prompt text}            -> string variable
          {List: label text}       -> list variable
        Escape literal braces with '\\{' or '\\}'.

        Returns:
            List[{"key": "total_budget_amount", "type": "string", "label": "Enter total budget amount"}]
        """
        text = (text if text is not None else self.body) or ""
        results: List[dict] = []
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
            results.append({"key": key, "type": var_type, "label": label})

        return results

    def render_with_escapes_cleaned(self, text: str) -> str:
        """
        Replace escaped '\\{' and '\\}' with literal braces for display.
        """
        return text.replace(r"\{", "{").replace(r"\}", "}")

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
