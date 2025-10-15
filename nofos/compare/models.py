from django.core.validators import MaxLengthValidator
from django.db import models
from django.urls import reverse

from nofos.models import BaseNofo, BaseSection, BaseSubsection, Nofo


class CompareDocument(BaseNofo):
    class Meta:
        verbose_name = "Compare Document"
        verbose_name_plural = "Compare Documents"

    title = models.TextField(
        "Document name",
        max_length=250,
        validators=[MaxLengthValidator(250)],
        blank=True,
    )

    from_nofo = models.ForeignKey(
        Nofo,
        on_delete=models.CASCADE,  # delete this doc if the source NOFO is deleted
        related_name="derived_compare_documents",  # reverse: nofo.derived_compare_documents.all()
        null=True,
        blank=True,
        help_text="If this Compare Document was cloned from a NOFO, this is the source NOFO.",
    )

    def __str__(self):
        return f"(Compare Document {self.id}) {self.title or self.filename}"

    def get_admin_url(self):
        """
        Returns the admin URL for this Compare Document.
        """
        return reverse("admin:compare_comparedocument_change", args=(self.id,))

    def get_absolute_url(self):
        """
        Returns the main edit view for this Compare Document.
        """
        return reverse("compare:compare_edit", args=(self.id,))


class CompareSection(BaseSection):
    class Meta:
        ordering = ["order"]
        unique_together = ("document", "order")

    document = models.ForeignKey(
        "compare.CompareDocument",
        on_delete=models.CASCADE,
        related_name="sections",
    )

    @property
    def document_id(self):
        return self.document.id

    def get_document(self):
        return self.document

    def get_sibling_queryset(self):
        return self.document.sections.all()

    def get_subsection_model(self):
        return CompareSubsection


class CompareSubsection(BaseSubsection):
    class Meta:
        ordering = ["order"]
        unique_together = ("section", "order")

    section = models.ForeignKey(
        CompareSection, on_delete=models.CASCADE, related_name="subsections"
    )

    COMPARISON_CHOICES = [
        ("none", "Do not compare"),
        ("name", "Compare name"),
        ("body", "Compare name and all text"),
        ("diff_strings", "Compare name and required strings"),
    ]

    comparison_type = models.CharField(
        max_length=20,
        choices=COMPARISON_CHOICES,
        default="body",
    )

    diff_strings = models.JSONField(
        default=list,
        blank=True,
        help_text="List of required strings that must be present in the body.",
    )
