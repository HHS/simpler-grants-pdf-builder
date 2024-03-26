from django.db import models
from django.forms import ValidationError
from django.urls import reverse
from django.utils import timezone
from martor.models import MartorField

from .utils import create_subsection_html_id

THEME_CHOICES = [
    ("landscape-cdc-blue", "CDC Landscape (Default)"),
    ("landscape-cdc-white", "CDC Landscape (Light)"),
    ("portrait-cdc-dop", "CDC Portrait (DOP)"),
    ("portrait-cdc-orr", "CDC Portrait (ORR)"),
    ("portrait-cdc-blue", "CDC Portrait (Default)"),
    ("portrait-cdc-white", "CDC Portrait (Light)"),
    ("portrait-acf-white", "ACF (Light)"),
    ("portrait-acl-white", "ACL (Default)"),
    ("portrait-aspr-white", "ASPR (Light)"),
    ("portrait-cms-white", "CMS (Light)"),
    ("portrait-hrsa-blue", "HRSA (Default)"),
    ("portrait-hrsa-white", "HRSA (Light)"),
    ("portrait-ihs-white", "IHS (Light)"),
]


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

    theme = models.CharField(
        max_length=32,
        choices=THEME_CHOICES,
        blank=False,
        default="portrait-hrsa-blue",
        help_text="The theme sets the orientation and colour pallete for this NOFO.",
    )

    COVER_CHOICES = [
        ("nofo--cover-page--hero", "Hero (large) image"),
        ("nofo--cover-page--medium", "Small image"),
        ("nofo--cover-page--text", "No image, large text"),
    ]

    cover = models.CharField(
        max_length=32,
        choices=COVER_CHOICES,
        blank=False,
        default="nofo--cover-page--medium",
        help_text="The cover style for the NOFO (eg, large image, medium image, no image).",
    )

    ICON_STYLE_CHOICES = [
        ("nofo--icons--border", "Color background, white icon, white outline (Filled)"),
        (
            "nofo--icons--solid",
            "White background, color icon, color outline (Standard)",
        ),
    ]

    icon_style = models.CharField(
        max_length=32,
        choices=ICON_STYLE_CHOICES,
        blank=False,
        default="nofo--icons--border",
        help_text="Defines the icon style on section cover pages.",
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

    DESIGNER_CHOICES = [
        ("adam", "Adam"),
        ("kevin", "Kevin"),
        ("emily", "Emily"),
        ("yasmine", "Yasmine"),
    ]

    designer = models.CharField(
        max_length=16,
        choices=DESIGNER_CHOICES,
        blank=True,
        help_text="The designer is responsible for the layout of this NOFO.",
    )

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("review", "In review"),
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
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("nofos:nofo_edit", args=(self.id,))

    def get_first_subsection(self):
        return self.sections.first().subsections.first()


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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # set "updated" field on Nofo
        if self.nofo:
            self.nofo.updated = timezone.now()
            self.nofo.save()

    def __str__(self):
        nofo_id = "999"
        try:
            if self.nofo.number:
                nofo_id = self.nofo.number
        except Nofo.DoesNotExist:
            pass

        return "({}) {}".format(nofo_id, self.name)


class Subsection(models.Model):
    section = models.ForeignKey(
        Section, on_delete=models.CASCADE, related_name="subsections"
    )
    name = models.TextField("Subsection name", blank=True)

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

    tag = models.CharField(max_length=2, choices=TAG_CHOICES, blank=True)

    callout_box = models.BooleanField(
        "Callout box",
        default=False,
        help_text="Make this subsection a callout box.",
    )

    body = MartorField("Content of subsection", blank=True)

    def __str__(self):
        return self.name or "(Unnamed subsection)"

    def clean(self):
        # Enforce 'tag' when 'name' is False
        if self.name and not self.tag:
            raise ValidationError("Tag is required when 'name' is present.")

    def save(self, *args, **kwargs):
        if self.name and not self.html_id:
            counter = self.pk or self.order
            self.html_id = create_subsection_html_id(counter, self)

        self.full_clean()  # Call the clean method for validation
        super().save(*args, **kwargs)

        # set "updated" field on Nofo
        if self.section and self.section.nofo:
            self.section.nofo.updated = timezone.now()
            self.section.nofo.save()

    def get_absolute_url(self):
        nofo_id = self.section.nofo.id
        return reverse("nofos:subsection_edit", args=(nofo_id, self.id))
