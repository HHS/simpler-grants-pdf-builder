import json
import re

from constance import config
from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.utils import timezone
from easyaudit.models import CRUDEvent
from slugify import slugify

from bloom_nofos.utils import is_docraptor_live_mode_active


def clean_string(string):
    """Cleans the given string by removing extra whitespace."""
    return re.sub(r"\s+", " ", string.strip())


def create_nofo_audit_event(event_type, nofo, user):
    # Define allowed event types
    allowed_event_types = ["nofo_import", "nofo_print", "nofo_reimport"]

    # Check if event_type is valid
    if event_type not in allowed_event_types:
        raise ValueError(
            f"Invalid event_type '{event_type}'. Allowed values are: {', '.join(allowed_event_types)}"
        )

    # Get current time
    now = timezone.now()
    changed_fields_json = {
        "action": event_type,
        "updated": [str(now.strftime("%Y-%m-%d %H:%M:%S.%f"))],
    }

    # Add print_mode if the event_type involves printing
    if event_type == "nofo_print":
        changed_fields_json["print_mode"] = [
            (
                "live"
                if is_docraptor_live_mode_active(config.DOCRAPTOR_LIVE_MODE)
                else "test"
            )
        ]

    # Create the audit log event
    CRUDEvent.objects.create(
        event_type=CRUDEvent.UPDATE,
        object_id=nofo.pk,
        content_type=ContentType.objects.get_for_model(nofo),
        object_repr=str(nofo),
        object_json_repr=serializers.serialize("json", [nofo]),
        changed_fields=json.dumps(changed_fields_json),
        user=user if user else None,
        user_pk_as_string=str(user.pk) if user else "",
        datetime=now,
    )


def create_subsection_html_id(counter, subsection):
    section_name = subsection.section.name
    return "{}--{}--{}".format(counter, slugify(section_name), slugify(subsection.name))


def add_html_id_to_subsection(subsection):
    """
    Assigns an `html_id` to a Subsection if not already set.
    The `html_id` is based on the subsection's order or primary key (if present).
    """
    if subsection.name and not subsection.html_id:
        # Use the primary key if available; otherwise, fall back to the order field
        counter = subsection.pk or subsection.order
        subsection.html_id = create_subsection_html_id(counter, subsection)


def get_icon_path_choices(theme):
    if theme == "portrait-acf-white":
        return [
            (
                "nofo--icons--border",
                "(Filled) Color background, white icon, white outline",
            ),
            (
                "nofo--icons--solid",
                "(Standard) White background, color icon, color outline",
            ),
            (
                "nofo--icons--thin",
                "(Thin) White background, color icon, color outline",
            ),
        ]

    return [
        ("nofo--icons--border", "(Filled) Color background, white icon, white outline"),
        (
            "nofo--icons--solid",
            "(Standard) White background, color icon, color outline",
        ),
    ]


def match_view_url(url):
    """
    Check if the given URL matches the pattern "/nofos/{integer}".

    Args:
    url (str): The URL to be checked.

    Returns:
    bool: True if the URL matches the pattern, False otherwise.
    """
    # Regular expression to match the specified pattern
    pattern = r"^/nofos/\d+$"

    return bool(re.match(pattern, url))


class StyleMapManager:
    def __init__(self, styles_to_ignore=None):
        self.styles = []
        self.styles_to_ignore = styles_to_ignore if styles_to_ignore is not None else []

    def add_style(self, style_rule, location_in_nofo, note=None):
        self.styles.append(
            {
                "style_rule": style_rule,
                "location_in_nofo": location_in_nofo,
                "note": note if note else None,
            }
        )

    def get_style_map(self):
        # This method will now just join all the individual style rules.
        return "\n".join(style["style_rule"] for style in self.styles)

    def get_styles_to_ignore(self):
        # Returns the list of styles that are currently set to be ignored
        return self.styles_to_ignore


# Pre-instantiate StyleMapManager with styles to ignore
style_map_manager = StyleMapManager(
    [
        "Bullet2",
        "customXmlDelRange",
        "Default",
        "FootnoteReference",
        "ListParagraph",
        "Listpara2",
        "non-row element in table",
        "Normal_0",
        "v:",
        "office-word:",
    ]
)

# run styles
style_map_manager.add_style(
    style_rule="r[style-name='normaltextrun'] => span",
    location_in_nofo="Step 2 > Grants.gov > You can see && Step 3 > Third party agreements",
    note="Don't do anything: body text + a header",
)
style_map_manager.add_style(
    style_rule="r[style-name='eop'] => span",
    location_in_nofo="Spans wrapping &nbsp sequences",
    note="Don't do anything, just whitespace",
)
style_map_manager.add_style(
    style_rule="r[style-name='contentcontrolboundarysink'] => span",
    location_in_nofo="Step 6 > Post-award requirements and administration > Reporting",
    note="Don't do anything, just whitespace",
)
style_map_manager.add_style(
    style_rule="r[style-name='criteria-linked-element_data-mode=export_criteria-score'] => span.linked-element",
    location_in_nofo="Step 4 > Maximum points > 20",
    note="Don't do anything: body text",
)
style_map_manager.add_style(
    style_rule="r[style-name='cf01'] => span",
    location_in_nofo="It's just in body text",
    note="Just plain body text",
)
style_map_manager.add_style(
    style_rule="r[style-name='cf11'] => span",
    location_in_nofo="It's just in body text",
    note="Just plain body text",
)
style_map_manager.add_style(
    style_rule="r[style-name='scxw144559721'] => span",
    location_in_nofo="It's just in body text",
    note="Just plain body text",
)
style_map_manager.add_style(
    style_rule="r[style-name='Body Text Char'] => span",
    location_in_nofo="It's just in body text",
    note="Don't do anything: regular body text.",
)
style_map_manager.add_style(
    style_rule="r[style-name='Style6 Char'] => span",
    location_in_nofo="Step 1 > Program description > Purpose",
    note="Just plain body text",
)
style_map_manager.add_style(
    style_rule="r[style-name='url'] => span",
    location_in_nofo="It's a url in the footnotes body text",
    note="It's a URL but it should be formatted as body text",
)
style_map_manager.add_style(
    style_rule="r[style-name='ui-provider'] => span:fresh",
    location_in_nofo="Step 1 > Program requirements and expectations > p",
    note="Don't do anything: not sure why this is formatted differently, but it's just body text.",
)
style_map_manager.add_style(
    style_rule="r[style-name='Intense Reference'] => span.intense-reference",
    location_in_nofo="Step 3 > Required format",
    note="Don't do anything: it's formatted as a header already, go with that.",
)
style_map_manager.add_style(
    style_rule="r[style-name='Placeholder Text'] => span.placeholder-text:fresh",
    location_in_nofo="Located in content controls",
    note="Print it out so we can see it, but this should not be in the document.",
)
style_map_manager.add_style(
    style_rule="r[style-name='Subtle Emphasis'] => strong.subtle-emphasis",
    location_in_nofo="Step 3 > Required format > Fonts/Spacing",
    note="Bold is safe, but they might possibly be headings.",
)
style_map_manager.add_style(
    style_rule="r[style-name='Heading 1 Char'] => span",
    location_in_nofo="Step 1 > Program description > Core Component approach > Core Component strategies and activities",
    note="Do nothing, it's whitespace",
)
style_map_manager.add_style(
    style_rule="r[style-name='Heading 3 Char'] => h3:fresh",
    location_in_nofo="Step 1 > Program description > Four core functions",
    note="This signifies an h3",
)
style_map_manager.add_style(
    style_rule="r[style-name='Heading 4 Char'] => h4:fresh",
    location_in_nofo="Step 3 > Project narrative > Areas of emphasis",
    note="This signifies an h4",
)
style_map_manager.add_style(
    style_rule="r[style-name='Heading 5 Char'] => h5:fresh",
    location_in_nofo="Step 1 > Cost-sharing commitments > Reduced Match",
    note="This signifies an h5",
)

# paragraph styles
style_map_manager.add_style(
    style_rule="p[style-name='heading 7'] => div[role='heading'][aria-level='7']",
    location_in_nofo="Step 1 > Summary > Funding Strategy > Component Funding > Overview",
    note="This is how we represent H7s",
)
# style_map_manager.add_style(
#     style_rule="p[style-name='Default'] => p",
#     location_in_nofo="Step 6 > Reporting > All content in table",
#     note="Don't do anything: this is being applied to paragraphs in a table and we don't need special styling for them.",
# )
style_map_manager.add_style(
    style_rule="p[style-name='Table'] => p",
    location_in_nofo="Step 3 > Other required forms > All table cells",
    note="Don't do anything: this is being applied to paragraphs in a table and we don't need special styling for them.",
)
style_map_manager.add_style(
    style_rule="p[style-name='Normal (Web)'] => p:fresh",
    location_in_nofo="Step 4 > Risk Review > p",
    note="Don't do anything: not sure why this is formatted differently, but it's just body text.",
)
style_map_manager.add_style(
    style_rule="p[style-name='div'] => p:fresh",
    location_in_nofo="Step 1 > Key facts > Name and number",
    note="Don't do anything: regular body text.",
)
style_map_manager.add_style(
    style_rule="p[style-name='paragraph'] => p:fresh",
    location_in_nofo="Step 1 > Eligibility > Who can apply",
    note="Don't do anything: regular body text.",
)
style_map_manager.add_style(
    style_rule="p[style-name='Body Text'] => p:fresh",
    location_in_nofo="Step 1 > Program description > Overview",
    note="Don't do anything: regular body text.",
)
style_map_manager.add_style(
    style_rule="p[style-name='pf0'] => p:fresh",
    location_in_nofo="Step 1 > Program description > Overview",
    note="Don't do anything: regular body text.",
)
style_map_manager.add_style(
    style_rule="p[style-name='Main Heading'] => p",
    location_in_nofo="Step 1 > Key facts > number",
    note="Don't do anything: regular body text (may not be true for all, but let's assume).",
)
style_map_manager.add_style(
    style_rule="p[style-name='Emphasis A'] => strong.emphasis",
    location_in_nofo="Step 2 > Grants.gov > Need Help?",
    note="Just bold the entire sentence",
)
style_map_manager.add_style(
    style_rule="p[style-name='Subhead2'] => strong.subhead",
    location_in_nofo="Step 1 > Eligility > Who can apply",
    note="Bold seems like the main thing we do here.",
)
style_map_manager.add_style(
    style_rule="p[style-name='Subhead2'] => strong.subhead",
    location_in_nofo="Step 1 > Eligility > Who can apply",
    note="Bold seems like the main thing we do here.",
)
style_map_manager.add_style(
    style_rule="p[style-name='Bullet Level 1'] => ul > li:fresh",
    location_in_nofo="This represents a bullet list improperly formatted",
    note="Convert them to li elements.",
)
style_map_manager.add_style(
    style_rule="p[style-name='No Spacing'] => span",
    location_in_nofo="This represents a non-breaking space",
    note="Convert to a non-breaking space.",
)
style_map_manager.add_style(
    style_rule="p[style-name='Instruction Box Heading'] => strong.instruction-box-heading:fresh",
    location_in_nofo="Instructions for NOFO writers > Heading",
    note="This text will be stripped out.",
)
style_map_manager.add_style(
    style_rule="p[style-name='Instruction Boxes'] => p:fresh",
    location_in_nofo="Instructions for NOFO writers > Body content",
    note="This text will be stripped out.",
)
