from django.db import models
from nofos.models import BaseNofo, BaseSubsection, Section
from django.core.validators import MaxLengthValidator


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

    # def get_absolute_url(self):
    #     """
    #     Returns the main edit view for this NOFO.
    #     """
    #     return reverse("nofos:nofo_edit", args=(self.id,))


class ContentGuideSubsection(BaseSubsection):
    class Meta:
        ordering = ["order"]
        unique_together = ("section", "order")

    section = models.ForeignKey(
        Section, on_delete=models.CASCADE, related_name="diff_subsections"
    )

    COMPARISON_CHOICES = [
        ("none", "Do not compare"),
        ("name", "Compare name"),
        ("body", "Compare name and all text"),
        ("diff_strings", "Compare name and text segments"),
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
