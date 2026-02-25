import uuid

import cssutils
from bloom_nofos.middleware import get_current_user
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.db import models, transaction
from django.forms import ValidationError
from django.urls import reverse
from django.utils import timezone
from django.utils.dateformat import format
from martor.models import MartorField

from .utils import add_html_id_to_subsection

BYB_CHOICES = [
    ("full", "Full BYB page"),
    ("sole_source", "Sole Source Justification"),
    ("none", "No BYB page"),
]

COACH_CHOICES = [
    ("laura", "Laura W"),
    ("julie", "Julie H"),
    ("moira", "Moira"),
    ("sara_d", "Sara D"),
    ("sara_t", "Sara T"),
]

DESIGNER_CHOICES = [
    ("bloom-adam", "Adam"),
    ("bloom-ben-b", "Ben B"),
    ("bloom-jana", "Jana"),
    ("bloom-yasmine", "Yasmine"),
    ("hrsa-betty", "Betty"),
    ("hrsa-dvora", "Dvora"),
    ("hrsa-ericka", "Ericka"),
    ("hrsa-jene", "Jene"),
    ("hrsa-jennifer", "Jennifer"),
    ("hrsa-kerry", "Kerry"),
    ("hrsa-kieumy", "KieuMy"),
    ("hrsa-lynda", "Lynda"),
    ("hrsa-marco", "Marco"),
    ("hrsa-randy", "Randy"),
    ("hrsa-stephanie", "Stephanie V"),
]


STATUS_CHOICES = [
    ("draft", "Draft"),
    ("active", "Active"),
    ("ready-for-qa", "Ready for QA"),
    ("review", "In review"),
    ("doge", "Dep Sec"),
    ("published", "Published"),
    ("paused", "Paused"),
    ("cancelled", "Cancelled"),
]


THEME_CHOICES = [
    ("landscape-cdc-blue", "CDC Landscape (Default)"),
    ("landscape-cdc-white", "CDC Landscape (Light)"),
    ("portrait-cdc-ncipc1", "CDC Portrait (NCIPC Blue)"),
    ("portrait-cdc-ncipc2", "CDC Portrait (NCIPC Teal)"),
    ("portrait-cdc-dghp", "CDC Portrait (DGHP)"),
    ("portrait-cdc-dhp", "CDC Portrait (DHP)"),
    ("portrait-cdc-iod", "CDC Portrait (IOD)"),
    ("portrait-cdc-orr", "CDC Portrait (ORR)"),
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
    ("portrait-samhsa-white", "SAMHSA (Light)"),
    ("portrait-nih-white", "NIH (Light)"),
]


class BaseNofo(models.Model):
    class Meta:
        abstract = True
        ordering = ["-updated"]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    filename = models.CharField(
        max_length=511,
        validators=[MaxLengthValidator(511)],
        blank=True,
        null=True,
        help_text="The filename used to import this document. If re-imported, this value is the most recent filename.",
    )

    group = models.CharField(
        max_length=16,
        validators=[MaxLengthValidator(16)],
        choices=settings.GROUP_CHOICES,
        blank=False,
        default="bloom",
        help_text="The OpDiv group for this document. The group controls access to a document. The 'Bloomworks' group hides documents from OpDiv users.",
    )

    opdiv = models.CharField(
        "Operating Division",
        max_length=511,
        validators=[MaxLengthValidator(511)],
        blank=False,
        help_text="The HHS operating division (eg, HRSA, CDC)",
    )

    status = models.CharField(
        max_length=32,
        validators=[MaxLengthValidator(32)],
        choices=STATUS_CHOICES,
        blank=False,
        default="draft",
        help_text="The status of this document in the NOFO Builder.",
    )

    archived = models.DateField(
        null=True,
        blank=True,
        default=None,
        help_text="Archived documents are soft-deleted: they are not visible in the UI but can be recovered by superusers.",
    )

    successor = models.ForeignKey(
        "self",  # self-referential foreign key
        on_delete=models.CASCADE,  # If a NOFO is deleted, also delete history
        null=True,
        blank=True,
        related_name="ancestors",
    )

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now_add=True)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="The last logged-in user who modified this document.",
    )

    @property
    def is_nofo(self):
        return isinstance(self, Nofo)

    @property
    def created_display(self):
        # Timezone-aware conversion
        created_localtime = timezone.localtime(self.created)

        today = timezone.localtime().date()
        created_date = created_localtime.date()

        if created_date != today:
            return format(created_localtime, "M j")

        return (
            f"{format(created_localtime, 'M j')}, {format(created_localtime, 'g:i A')}"
        )

    @property
    def updated_display(self):
        # Timezone-aware conversion
        updated_localtime = timezone.localtime(self.updated)

        today = timezone.localtime().date()
        updated_date = updated_localtime.date()

        if updated_date != today:
            return format(updated_localtime, "M j")

        return (
            f"{format(updated_localtime, 'M j')}, {format(updated_localtime, 'g:i A')}"
        )

    @property
    def updated_by_display(self):
        """Get a name for display of the BaseNofo.updated_by User object"""
        user = self.updated_by
        if not user:
            return ""

        return getattr(user, "full_name", None) or getattr(user, "email", None)

    def __str__(self):
        return "({}) {}".format(self.id, self.title or "Untitled")

    def get_first_subsection(self):
        return (
            self.sections.order_by("order")
            .first()
            .subsections.order_by("order")
            .first()
        )

    def save(self, *args, **kwargs):
        if self.pk and self.__class__.objects.filter(pk=self.pk).exists():
            # If the instance already exists, check if any field other than 'status' has changed
            original_document = self.__class__.objects.get(pk=self.pk)
            for field in self._meta.fields:
                if field.name != "status" and getattr(
                    original_document, field.name
                ) != getattr(self, field.name):
                    # A field other than 'status' has changed, update the 'updated' field
                    self.updated = timezone.now()
                    user = get_current_user()
                    self.updated_by = user if (user and user.is_authenticated) else None
                    break

        else:
            # If it's a new instance, set the 'updated' field to the current time
            self.updated = timezone.now()
            user = get_current_user()
            self.updated_by = user if (user and user.is_authenticated) else None

        # Call the clean method for validation
        self.full_clean()
        super().save(*args, **kwargs)

    def touch_updated(self):
        """
        Atomically update `updated` (and `updated_by`, if present) without
        calling save(), to avoid recursion or expensive validation.
        """
        user = get_current_user()
        updates = {"updated": timezone.now()}
        if user and user.is_authenticated:
            updates["updated_by"] = user
        else:
            # If you prefer to *not* clear when no user, comment this out
            updates["updated_by"] = None

        self.__class__.objects.filter(pk=self.pk).update(**updates)


class Nofo(BaseNofo):
    class Meta:
        verbose_name = "NOFO"
        verbose_name_plural = "NOFOs"

    title = models.TextField(
        "NOFO title",
        max_length=250,
        validators=[MaxLengthValidator(250)],
        blank=True,
        help_text="The official name for this NOFO. It will be public when the NOFO is published.",
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

    subagency = models.CharField(
        "Subagency",
        max_length=511,
        validators=[MaxLengthValidator(511)],
        blank=True,
        help_text="The subagency within the agency (eg, Division of Medicine and Dentistry)",
    )

    subagency2 = models.CharField(
        "Subagency 2",
        max_length=511,
        validators=[MaxLengthValidator(511)],
        blank=True,
        null=True,
        help_text="Another subagency within the agency (eg, Division of Medicine and Dentistry) collaborating on this NOFO",
    )

    application_deadline = models.CharField(
        "Application deadline",
        max_length=200,
        validators=[MaxLengthValidator(200)],
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
        validators=[MaxLengthValidator(32)],
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
        validators=[MaxLengthValidator(32)],
        choices=COVER_CHOICES,
        blank=False,
        default="nofo--cover-page--medium",
        help_text="The cover style for the NOFO.",
    )

    cover_image = models.CharField(
        "Cover image",
        max_length=511,
        validators=[MaxLengthValidator(511)],
        blank=True,
        default="",
        help_text="Optional URL or path to the cover image.",
    )

    cover_image_alt_text = models.CharField(
        "Cover image alt text",
        max_length=511,
        validators=[MaxLengthValidator(511)],
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
        validators=[MaxLengthValidator(32)],
        choices=ICON_STYLE_CHOICES,
        blank=False,
        default="nofo--icons--border",
        help_text="Defines the icon style on section cover pages.",
    )

    coach = models.CharField(
        max_length=16,
        validators=[MaxLengthValidator(16)],
        choices=COACH_CHOICES,
        blank=True,
        help_text="The coach has the primary responsibility for editing this NOFO.",
    )

    designer = models.CharField(
        max_length=16,
        validators=[MaxLengthValidator(16)],
        choices=DESIGNER_CHOICES,
        blank=True,
        help_text="The designer is responsible for the layout of this NOFO.",
    )

    modifications = models.DateField(
        null=True,
        blank=True,
        default=None,
        help_text="If this NOFO has post-publishing modifications. Adds a message to the cover page and a “Modifications” section to the end of the NOFO.",
    )

    inline_css = models.TextField(
        "Inline CSS",
        blank=True,
        null=True,
        help_text="Extra CSS to include for this specific NOFO.",
    )

    before_you_begin = models.CharField(
        "Before You Begin page",
        max_length=20,
        choices=BYB_CHOICES,
        default="full",
        help_text=(
            "Controls how the 'Before you begin' page is presented. Choices are 'Full', 'Sole Source' (for 1 applicant), and 'None'."
        ),
    )

    def __str__(self):
        return "({}) {}".format(self.id, self.title or self.short_name)

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

    def clean(self):
        super().clean()
        errors = {}

        # Validate title or number is present and not just whitespace
        title_empty = not self.title or not self.title.strip()
        number_empty = not self.number or not self.number.strip()

        if title_empty and number_empty:
            errors["title"] = (
                "Either title or number must be provided and cannot be empty"
            )
            errors["number"] = (
                "Either title or number must be provided and cannot be empty"
            )

        if errors:
            raise ValidationError(errors)

        if self.inline_css:
            # Parse the CSS to check for errors
            parser = cssutils.CSSParser(raiseExceptions=True)
            try:
                parser.parseString(self.inline_css)
            except Exception as e:
                raise ValidationError("Invalid CSS: {}".format(e))


class BaseSection(models.Model):
    class Meta:
        abstract = True

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    name = models.TextField(
        "Section name",
        max_length=250,
        validators=[MaxLengthValidator(250)],
    )
    html_id = models.CharField(max_length=511, validators=[MaxLengthValidator(511)])
    order = models.IntegerField(null=True)

    has_section_page = models.BooleanField(
        "Has section page?",
        default=True,
        help_text="If true, this section will have its own page and icon in the ToC.",
    )

    html_class = models.CharField(
        "HTML class attribute",
        max_length=1023,
        validators=[MaxLengthValidator(1023)],
        blank=True,
        default="",
    )

    def __str__(self):
        return "({}) {}".format(self.document_id or "999", self.name)

    def get_previous_section(self):
        return (
            self.get_sibling_queryset()
            .filter(order__lt=self.order)
            .order_by("-order")
            .first()
        )

    def get_next_section(self):
        return (
            self.get_sibling_queryset()
            .filter(order__gt=self.order)
            .order_by("order")
            .first()
        )

    def insert_order_space(self, insert_at_order):
        """
        Inserts an empty space in the ordering of Subsection instances within a Section.
        All Subsection instances with an order greater than or equal to `insert_at_order`
        will have their order incremented by 1, making room for a new instance at `insert_at_order`.

        :param section_id: ID of the Section in which to insert the space.
        :param insert_at_order: The order number at which to insert the space.
        """
        with transaction.atomic():
            # Fetch the Subsections to be updated, in reverse order
            subsections_to_update = (
                self.get_subsection_model()
                .objects.filter(section_id=self.id, order__gte=insert_at_order)
                .order_by("-order")
            )

            # Increment their order by 1
            for subsection in subsections_to_update:
                # Directly incrementing to avoid conflict
                self.get_subsection_model().objects.filter(pk=subsection.pk).update(
                    order=models.F("order") + 1
                )

    def save(self, *args, **kwargs):
        if not self.order:
            self.order = self.get_next_order(self.get_document())

        super().save(*args, **kwargs)

        document = self.get_document()
        if document:
            document.touch_updated()

    @classmethod
    def get_next_order(cls, document):
        """
        Get the next available order number for a section in this NOFO or ContentGuide.
        """
        last_section = (
            cls.objects.filter(**{cls.get_document_type(): document})
            .order_by("-order")
            .first()
        )

        return (last_section.order + 1) if last_section else 1

    @classmethod
    def get_document_type(cls):
        field_names = [f.name for f in cls._meta.fields]
        if "nofo" in field_names:
            return "nofo"
        elif "content_guide" in field_names:
            return "content_guide"
        raise ValueError("Document field not found")

    def get_document(self):
        raise NotImplementedError("Subclasses must implement get_document.")

    def get_sibling_queryset(self):
        raise NotImplementedError("Subclasses must implement get_sibling_queryset.")

    def get_subsection_model(self):
        raise NotImplementedError("Subclasses must implement get_subsection_model.")


class Section(BaseSection):
    class Meta:
        ordering = ["order"]
        unique_together = ("nofo", "order")

    nofo = models.ForeignKey(
        "nofos.Nofo",
        on_delete=models.CASCADE,
        related_name="sections",
    )

    @property
    def document_id(self):
        return self.nofo.id

    @property
    def subsections(self):
        return self.nofo_subsections.all()

    def get_document(self):
        return self.nofo

    def get_sibling_queryset(self):
        return self.nofo.sections.all()

    def get_subsection_model(self):
        return Subsection

    def get_absolute_url(self):
        return reverse(
            "nofos:section_detail",
            kwargs={"pk": self.nofo.pk, "section_pk": self.pk},
        )


class BaseSubsection(models.Model):
    class Meta:
        abstract = True

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    name = models.TextField(
        "Subsection name",
        max_length=400,
        blank=True,
        validators=[MaxLengthValidator(400)],
    )

    html_id = models.CharField(
        "HTML id attribute",
        max_length=511,
        validators=[MaxLengthValidator(511)],
        blank=True,
    )

    html_class = models.CharField(
        "HTML class attribute",
        max_length=1023,
        validators=[MaxLengthValidator(1023)],
        blank=True,
        default="",
    )

    order = models.IntegerField(null=True)

    TAG_CHOICES = [
        ("h2", "Heading 2"),
        ("h3", "Heading 3"),
        ("h4", "Heading 4"),
        ("h5", "Heading 5"),
        ("h6", "Heading 6"),
        ("h7", "Heading 7"),
    ]

    tag = models.CharField(
        max_length=2,
        validators=[MaxLengthValidator(2)],
        choices=TAG_CHOICES,
        blank=True,
    )

    callout_box = models.BooleanField(
        "Callout box",
        default=False,
        help_text="Make this subsection a callout box.",
    )

    body = MartorField("Content of subsection", blank=True)

    def __str__(self):
        return self.name or "(Unnamed subsection)"

    def get_document(self):
        """Return the document object (Nofo or ContentGuide) this subsection belongs to."""
        return self.section.get_document()

    def clean(self, *args, **kwargs):
        # Enforce 'tag' when 'name' is False
        if self.name and not self.tag:
            raise ValidationError("Tag is required when 'name' is present.")

        super().clean(*args, **kwargs)

    def save(self, *args, **kwargs):
        add_html_id_to_subsection(self)

        self.full_clean()  # Call the clean method for validation
        super().save(*args, **kwargs)

        # set "updated" field on Nofo/ContentGuide
        document = self.get_document()
        if document:
            document.touch_updated()

    def get_absolute_url(self):
        nofo_id = self.section.nofo.id
        return reverse("nofos:subsection_edit", args=(nofo_id, self.id))

    def is_matching_subsection(self, other_subsection):
        """
        Determines whether this subsection matches another subsection.

        This method is used to compare two subsections from different NOFOs to determine if they represent
        the same structural element within a document. This function checks for:

        1. Different NOFOs: If the subsections belong to the same NOFO, they are distinct and cannot match.
        2. Same section name: If they belong to different sections, they cannot match.
        3. Same subsection name: If both subsections have names, they are considered a match if their names are identical.
        4. Unnamed Subsections Check: If neither subsection has a name, they are compared based on adjacency.
            i. Recursively check **previous** and **next** subsections to determine whether they align.
            ii. If a named subsection is encountered in either direction, it is used as an anchor for comparison.
            iii. If both previous and next subsections match, the unnamed subsection is considered a match.

        The adjacency check is implemented in `_are_adjacent_matching()`, which ensures that recursion proceeds only
        in one direction (either "previous" or "next") at a time, preventing infinite loops.

        Parameters:
            other_subsection (Subsection): The subsection from another NOFO to compare against.

        Returns:
            bool: True if the subsections are considered equivalent, False otherwise.
        """

        def _are_adjacent_matching(subsection_self, subsection_other, direction):
            """Helper function to check if adjacent subsections match while ensuring directionality."""

            get_adjacent_func_name = "get_{}_subsection".format(direction)
            get_adjacent_func_self = getattr(subsection_self, get_adjacent_func_name)
            get_adjacent_func_other = getattr(subsection_other, get_adjacent_func_name)

            self_adjacent = get_adjacent_func_self()
            other_adjacent = get_adjacent_func_other()

            # If neither has an adjacent subsection, assume they match
            if not self_adjacent and not other_adjacent:
                return True

            # If one has an adjacent subsection and the other doesn't, they don't match
            if bool(self_adjacent) != bool(other_adjacent):
                return False

            # If adjacent subsections have names, compare names directly
            if self_adjacent.name and other_adjacent.name:
                return self_adjacent.name == other_adjacent.name

            # If still unnamed, continue checking in the same direction only
            return _are_adjacent_matching(self_adjacent, other_adjacent, direction)

        # 1. If in the same NOFO, they can't "match" because they are two distinct subsections
        if self.get_document().id == other_subsection.get_document().id:
            return False

        # 2. If in different sections, they can't "match" because they live in different parts of the NOFO
        if self.section.name != other_subsection.section.name:
            return False

        # 3. If both have names, check if they match
        if self.name and other_subsection.name:
            return self.name == other_subsection.name

        # 4. If neither has a name, check previous and next subsections
        return _are_adjacent_matching(
            self, other_subsection, "previous"
        ) and _are_adjacent_matching(self, other_subsection, "next")

    def get_previous_subsection(self):
        """Returns the previous subsection in the same section."""
        return (
            self.section.subsections.filter(order__lt=self.order)
            .order_by("-order")
            .first()
        )

    def get_next_subsection(self):
        """Returns the next subsection in the same section."""
        return (
            self.section.subsections.filter(order__gt=self.order)
            .order_by("order")
            .first()
        )


class Subsection(BaseSubsection):
    class Meta:
        ordering = ["order"]
        unique_together = ("section", "order")

    section = models.ForeignKey(
        Section, on_delete=models.CASCADE, related_name="subsections"
    )
