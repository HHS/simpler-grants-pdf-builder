from django.core.validators import MaxLengthValidator
from django.db import models
from django.urls import reverse
from nofos.models import BaseNofo, BaseSection, BaseSubsection


class ContentGuide(BaseNofo):
    class Meta:
        verbose_name = "Content Guide"
        verbose_name_plural = "Content Guides"

    title = models.TextField(
        "Content Guide title",
        max_length=250,
        validators=[MaxLengthValidator(250)],
        blank=True,
        help_text="The title of this Content Guide template.",
    )

    def __str__(self):
        return f"(Guide {self.id}) {self.title or self.filename}"

    def get_admin_url(self):
        """
        Returns the admin URL for this Content Guide.
        """
        return reverse("admin:guides_contentguide_change", args=(self.id,))

    def get_absolute_url(self):
        """
        Returns the main edit view for this Content Guide.
        """
        return reverse("guides:guide_edit", args=(self.id,))


class ContentGuideSection(BaseSection):
    content_guide = models.ForeignKey(
        "guides.ContentGuide",
        on_delete=models.CASCADE,
        related_name="sections",
    )

    @property
    def document_id(self):
        return self.content_guide.id

    @property
    def subsections(self):
        return self.subsections.all()

    def get_document(self):
        return self.content_guide

    def get_sibling_queryset(self):
        return self.content_guide.sections.all()

    def get_subsection_model(self):
        return ContentGuideSubsection


class ContentGuideSubsection(BaseSubsection):
    class Meta:
        ordering = ["order"]
        unique_together = ("section", "order")

    section = models.ForeignKey(
        ContentGuideSection, on_delete=models.CASCADE, related_name="subsections"
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
        default="name",
    )

    diff_strings = models.JSONField(
        default=list,
        blank=True,
        help_text="List of required strings that must be present in the body.",
    )
