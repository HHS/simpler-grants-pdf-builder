from django.db import models
from nofos.models import BaseNofo
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
