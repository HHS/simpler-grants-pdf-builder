from django.db import models
from django.forms import ValidationError
from django.urls import reverse
from martor.models import MartorField


class Nofo(models.Model):
    title = models.TextField(
        "NOFO title",
        blank=True,
        help_text="This will be publicly visible when the NOFO is published.",
    )
    short_name = models.CharField(
        max_length=511,
        blank=True,
        help_text="A name to make it easier to see this NOFO in a list. It won’t be public.",
    )

    number = models.CharField(
        "Opportunity number",
        max_length=200,
        blank=True,
        help_text="The official opportunity number for this NOFO. It will be public.",
    )

    opdiv = models.CharField(
        "Operating Division",
        max_length=511,
        blank=True,
        help_text="The HHS operating division (eg, HRSA, CDC)",
    )

    agency = models.CharField(
        "Agency",
        max_length=511,
        blank=True,
        help_text="The agency within the operating division (eg, Bureau of Health Workforce)",
    )

    subagency = models.CharField(
        "Subagency",
        max_length=511,
        blank=True,
        help_text="The subagency within the agency (eg, Division of Medicine and Dentistry)",
    )

    subagency2 = models.CharField(
        "Subagency 2",
        max_length=511,
        blank=True,
        help_text="Another subagency within the agency (eg, Division of Medicine and Dentistry) collaborating on this NOFO",
    )

    application_deadline = models.CharField(
        "Application deadline",
        max_length=200,
        blank=True,
        help_text="The date that applications for this NOFO must be submitted.",
    )

    tagline = models.TextField(
        "NOFO tagline",
        blank=True,
        help_text="A short sentence that outlines the high-level goal of this NOFO.",
    )

    author = models.TextField(
        "NOFO author",
        blank=True,
        help_text="The author of this NOFO.",
    )

    subject = models.TextField(
        "NOFO subject",
        blank=True,
        help_text="The subject of this NOFO.",
    )

    keywords = models.TextField(
        "NOFO keywords",
        blank=True,
        help_text="Keywords for this NOFO.",
    )

    THEME_CHOICES = [
        ("landscape-cdc-blue", "CDC Landscape (Default)"),
        ("landscape-cdc-white", "CDC Landscape (Light)"),
        ("landscape-cdc-dop", "CDC Landscape (DOP)"),
        ("portrait-cdc-blue", "CDC Portrait (Default)"),
        ("portrait-cdc-white", "CDC Portrait (Light)"),
        ("portrait-hrsa-blue", "HRSA (Default)"),
        ("portrait-hrsa-white", "HRSA (Light)"),
        ("portrait-acf-blue", "ACF (Blue)"),
        ("portrait-cms-white", "CMS (Light)"),
    ]

    theme = models.CharField(
        max_length=32,
        choices=THEME_CHOICES,
        blank=False,
        default="portrait-hrsa-blue",
        help_text="The theme sets the orientation and colour pallete for this NOFO.",
    )

    COVER_CHOICES = [
        ("nofo--cover-page--hero", "Hero (large) image"),
        ("nofo--cover-page--medium", "Medium image"),
        ("nofo--cover-page--text", "No image, large text"),
    ]

    cover = models.CharField(
        max_length=32,
        choices=COVER_CHOICES,
        blank=False,
        default="nofo--cover-page--medium",
        help_text="The cover style for the NOFO (eg, large image, medium image, no image).",
    )

    COACH_CHOICES = [
        ("emily", "Emily"),
        ("hannah", "Hannah"),
        ("julie", "Julie"),
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

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("published", "Published"),
    ]

    status = models.CharField(
        max_length=32,
        choices=STATUS_CHOICES,
        blank=False,
        default="draft",
        help_text="The status of this NOFO in the NOFO builder.",
    )

    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("nofos:nofo_edit", args=(self.id,))

    def get_first_subsection(self):
        return self.sections.first().subsections.first()


# TODO default lambda
# order = models.IntegerField(default=lambda: Section.objects.latest("order") + 1)
class Section(models.Model):
    nofo = models.ForeignKey(Nofo, on_delete=models.CASCADE, related_name="sections")
    name = models.TextField("Section name")
    html_id = models.CharField(
        max_length=511,
        blank=True,
    )
    order = models.IntegerField(null=True)

    has_section_page = models.BooleanField(
        "Has section page?",
        default=True,
        help_text="If true, this section will have its own page and icon in the ToC.",
    )

    class Meta:
        unique_together = ("nofo", "order")

    def __str__(self):
        nofo_id = "999"
        try:
            nofo_id = self.nofo.id
        except Nofo.DoesNotExist:
            pass

        return "({}) {}".format(nofo_id, self.name)


class Subsection(models.Model):
    section = models.ForeignKey(
        Section, on_delete=models.CASCADE, related_name="subsections"
    )
    name = models.TextField(
        "Subsection name", blank=True
    )  # Name can be blank if callout_box is true

    html_id = models.CharField(
        "HTML id attribute",
        max_length=511,
        blank=True,
    )

    html_class = models.CharField(
        "HTML class attribute",
        max_length=1023,
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
        ("h7", "Heading 7"),
    ]

    tag = models.CharField(
        max_length=2, choices=TAG_CHOICES, blank=True
    )  # Tag can be blank if callout_box is true

    callout_box = models.BooleanField(
        "Callout box",
        default=False,
        help_text="Make this subsection a callout box.",
    )

    body = MartorField("Content of subsection", blank=True)

    def __str__(self):
        return self.name or "(Unnamed subsection)"

    def clean(self):
        # Enforce 'name' when 'callout_box' is False
        if not self.callout_box and not self.name:
            raise ValidationError("Name is required when 'callout_box' is False.")

        # Enforce 'tag' when 'callout_box' is False
        if not self.callout_box and not self.tag:
            raise ValidationError("Tag is required when 'callout_box' is False.")

    def save(self, *args, **kwargs):
        self.full_clean()  # Call the clean method for validation
        super().save(*args, **kwargs)
