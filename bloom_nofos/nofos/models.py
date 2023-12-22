from django.db import models
from django.urls import reverse
from martor.models import MartorField


class Nofo(models.Model):
    title = models.TextField(
        "NOFO title",
        blank=True,
        help_text="This will be publicly visible when the NOFO is published.",
    )
    short_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="A name to make it easier to see this NOFO in a list. It won’t be public.",
    )

    number = models.CharField(
        "Opportunity number",
        max_length=200,
        blank=True,
        help_text="The official opportunity number for this NOFO. It will be public.",
    )

    tagline = models.TextField(
        "NOFO tagline",
        blank=True,
        help_text="A short sentence that outlines the high-level goal of this NOFO.",
    )

    THEME_CHOICES = [
        ("landscape-cdc-blue", "CDC (Blue)"),
        ("portrait-hrsa-blue", "HRSA (Blue)"),
    ]

    theme = models.CharField(
        max_length=32,
        choices=THEME_CHOICES,
        blank=False,
        default="portrait-hrsa-blue",
        help_text="The theme sets the orientation and colour pallete for this NOFO.",
    )

    COACH_CHOICES = [
        ("emily", "Emily"),
        ("hannah", "Hannah"),
        ("july", "July"),
        ("laura", "Laura"),
        ("moira", "Moira"),
        ("morgan", "Morgan"),
    ]

    coach = models.CharField(
        max_length=16,
        choices=COACH_CHOICES,
        blank=True,
        help_text="The coach has the primary responsibility for editing this NOFO.",
    )

    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("nofos:nofo_edit", args=(self.id,))


# TODO default lambda
# order = models.IntegerField(default=lambda: Section.objects.latest("order") + 1)
class Section(models.Model):
    nofo = models.ForeignKey(Nofo, on_delete=models.CASCADE, related_name="sections")
    name = models.TextField("Section name")
    html_id = models.CharField(
        max_length=200,
        blank=True,
    )
    order = models.IntegerField(null=True)

    class Meta:
        unique_together = ("nofo", "order")

    def __str__(self):
        return self.name


class Subsection(models.Model):
    section = models.ForeignKey(
        Section, on_delete=models.CASCADE, related_name="subsections"
    )
    name = models.TextField("Subsection name")
    html_id = models.CharField(
        max_length=200,
        blank=True,
    )
    order = models.IntegerField(null=True)

    class Meta:
        unique_together = ("section", "order")

    TAG_CHOICES = [
        ("h2", "Heading 2"),
        ("h3", "Heading 3"),
        ("h4", "Heading 4"),
        ("h5", "Heading 5"),
        ("h6", "Heading 6"),
    ]
    tag = models.CharField(
        max_length=2,
        choices=TAG_CHOICES,
    )

    callout_box = models.BooleanField(
        "Callout box",
        default=False,
        help_text="Make this subsection a callout box.",
    )

    body = MartorField("Content of subsection", blank=True)

    def __str__(self):
        return self.name
