import cssutils
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.forms import ValidationError
from django.urls import reverse
from django.utils import timezone
from martor.models import MartorField

from .utils import add_html_id_to_subsection

COACH_CHOICES = [
    ("aarti", "Aarti"),
    ("alex", "Alex"),
    ("emily", "Emily"),
    ("hannah", "Hannah"),
    ("idit", "Idit"),
    ("julie", "Julie"),
    ("july", "July"),
    ("mick", "Mick"),
    ("moira", "Moira"),
    ("morgan", "Morgan"),
    ("sara", "Sara"),
    ("shane", "Shane"),
]

DESIGNER_CHOICES = [
    ("bloom-abbey", "Abbey"),
    ("bloom-adam", "Adam"),
    ("bloom-emily-b", "Emily B"),
    ("bloom-emily-i", "Emily I"),
    ("bloom-jackie", "Jackie"),
    ("bloom-kevin", "Kevin"),
    ("bloom-yasmine", "Yasmine"),
    ("hrsa-betty", "Betty"),
    ("hrsa-doretha", "Doretha"),
    ("hrsa-gwen", "Gwen"),
    ("hrsa-ericka", "Ericka"),
    ("hrsa-jene", "Jene"),
    ("hrsa-randy", "Randy"),
    ("hrsa-stephanie", "Stephanie V"),
    ("hrsa-kieumy", "KieuMy"),
]


STATUS_CHOICES = [
    ("draft", "Draft"),
    ("active", "Active"),
    ("ready-for-qa", "Ready for QA"),
    ("review", "In review"),
    ("published", "Published"),
]


THEME_CHOICES = [
    ("landscape-cdc-blue", "CDC Landscape (Default)"),
    ("landscape-cdc-white", "CDC Landscape (Light)"),
    ("portrait-cdc-dop", "CDC Portrait (DOP)"),
    ("portrait-cdc-orr", "CDC Portrait (ORR)"),
    ("portrait-cdc-iod", "CDC Portrait (IOD)"),
    ("portrait-cdc-blue", "CDC Portrait (Default)"),
    ("portrait-cdc-white", "CDC Portrait (Light)"),
    ("portrait-acf-white", "ACF (Light)"),
    ("portrait-acl-white", "ACL (Default)"),
    ("portrait-aspr-white", "ASPR (Light)"),
    ("portrait-cms-blue", "CMS (Default)"),
    ("portrait-cms-white", "CMS (Light)"),
    ("portrait-hrsa-blue", "HRSA (Default)"),
    ("portrait-hrsa-white", "HRSA (Light)"),
    ("portrait-ihs-white", "IHS (Light)"),
]


class Nofo(models.Model):
    title = models.TextField(
        "NOFO title",
        blank=True,
        help_text="The official name for this NOFO. It will be public when the NOFO is published.",
    )

    filename = models.CharField(
        max_length=511,
        blank=True,
        null=True,
        help_text="The filename used to import this NOFO. If re-imported, this value is the most recent filename.",
    )

    short_name = models.CharField(
        max_length=511,
        blank=True,
        help_text="A name that makes it easier to find this NOFO in a list. It won’t be public.",
    )

    number = models.CharField(
        "Opportunity number",
        max_length=200,
        blank=True,
        help_text="The official opportunity number for this NOFO.",
    )

    group = models.CharField(
        max_length=16,
        choices=settings.GROUP_CHOICES,
        blank=False,
        default="bloom",
        help_text="The OpDiv grouping of this NOFO. The group is used to control access to a NOFO. The 'Bloomworks' group can be used to hide NOFOs from OpDiv users.",
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
        null=True,
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
        ("nofo--cover-page--hero", "Full coverage with image"),
        ("nofo--cover-page--medium", "Standard image"),
        ("nofo--cover-page--text", "Text only"),
    ]

    cover = models.CharField(
        max_length=32,
        choices=COVER_CHOICES,
        blank=False,
        default="nofo--cover-page--medium",
        help_text="The cover style for the NOFO.",
    )

    cover_image = models.CharField(
        "Cover image",
        max_length=511,
        blank=True,
        default="",
        help_text="Optional URL or path to the cover image.",
    )

    cover_image_alt_text = models.CharField(
        "Cover image alt text",
        max_length=511,
        blank=True,
        default="",
        help_text="Alternative text for the cover image.",
    )

    ICON_STYLE_CHOICES = [
        ("nofo--icons--border", "(Filled) Color background, white icon, white outline"),
        (
            "nofo--icons--solid",
            "(Outlined) White background, color icon, color outline",
        ),
        (
            "nofo--icons--thin",
            "(Thin) Thin icons with white background, color icon, color outline",
        ),
    ]

    icon_style = models.CharField(
        max_length=32,
        choices=ICON_STYLE_CHOICES,
        blank=False,
        default="nofo--icons--border",
        help_text="Defines the icon style on section cover pages.",
    )

    coach = models.CharField(
        max_length=16,
        choices=COACH_CHOICES,
        blank=True,
        help_text="The coach has the primary responsibility for editing this NOFO.",
    )

    designer = models.CharField(
        max_length=16,
        choices=DESIGNER_CHOICES,
        blank=True,
        help_text="The designer is responsible for the layout of this NOFO.",
    )

    status = models.CharField(
        max_length=32,
        choices=STATUS_CHOICES,
        blank=False,
        default="draft",
        help_text="The status of this NOFO in the NOFO Builder.",
    )

    archived = models.DateField(
        null=True,
        blank=True,
        default=None,
        help_text="Archived NOFOs are soft-deleted: they are not visible in the UI but can be recovered by superusers.",
    )

    group = models.CharField(
        max_length=16,
        choices=settings.GROUP_CHOICES,
        blank=False,
        default="bloom",
        help_text="The OpDiv grouping of this NOFO. The group is used to control access to a NOFO.",
    )

    inline_css = models.TextField(
        "Inline CSS",
        blank=True,
        null=True,
        help_text="Extra CSS to include for this specific NOFO.",
    )

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    def get_admin_url(self):
        """
        Returns the admin URL for this NOFO.
        """
        return reverse("admin:nofos_nofo_change", args=(self.id,))

    def get_absolute_url(self):
        """
        Returns the main edit view for this NOFO.
        """
        return reverse("nofos:nofo_edit", args=(self.id,))

    def get_first_subsection(self):
        return self.sections.first().subsections.order_by("order").first()

    def clean(self):
        if self.inline_css:
            # Parse the CSS to check for errors
            parser = cssutils.CSSParser(raiseExceptions=True)
            try:
                parser.parseString(self.inline_css)
            except Exception as e:
                raise ValidationError(f"Invalid CSS: {e}")

    def save(self, *args, **kwargs):
        if self.pk:
            # If the instance already exists, check if any field other than 'status' has changed
            original_nofo = Nofo.objects.get(pk=self.pk)
            for field in self._meta.fields:
                if field.name != "status" and getattr(
                    original_nofo, field.name
                ) != getattr(self, field.name):
                    # A field other than 'status' has changed, update the 'updated' field
                    self.updated = timezone.now()
                    break
        else:
            # If it's a new instance, set the 'updated' field to the current time
            self.updated = timezone.now()

        # Call the clean method for validation
        self.full_clean()
        super().save(*args, **kwargs)


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

    def get_previous_section(self):
        return (
            self.nofo.sections.filter(order__lt=self.order).order_by("-order").first()
        )

    def get_next_section(self):
        return self.nofo.sections.filter(order__gt=self.order).order_by("order").first()


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
        add_html_id_to_subsection(self)

        self.full_clean()  # Call the clean method for validation
        super().save(*args, **kwargs)

        # set "updated" field on Nofo
        if self.section and self.section.nofo:
            self.section.nofo.updated = timezone.now()
            self.section.nofo.save()

    def get_absolute_url(self):
        nofo_id = self.section.nofo.id
        return reverse("nofos:subsection_edit", args=(nofo_id, self.id))
