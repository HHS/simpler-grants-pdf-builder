import json
import re
import uuid

from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.utils import timezone
from easyaudit.models import CRUDEvent
from slugify import slugify


def clean_string(string):
    """Cleans the given string by removing extra whitespace."""
    return re.sub(r"\s+", " ", string.strip())


def create_nofo_audit_event(event_type, document, user, is_test_pdf=True):
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
        changed_fields_json["print_mode"] = ["test" if is_test_pdf else "live"]

    # Create the audit log event
    CRUDEvent.objects.create(
        event_type=CRUDEvent.UPDATE,
        object_id=document.pk,
        content_type=ContentType.objects.get_for_model(document),
        object_repr=str(document),
        object_json_repr=serializers.serialize("json", [document]),
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
        # Use the order if available; otherwise, fall back to the primary key
        counter = subsection.order or subsection.pk
        subsection.html_id = create_subsection_html_id(counter, subsection)


def extract_highlighted_context(body, pattern, context_chars=100, group_distance=200):
    """
    Extracts and highlights context around matches in a string.

    Args:
        body (str): The full text to search in.
        pattern (str or compiled regex): Pattern to search for (case-insensitive).
        context_chars (int): Characters of context before/after each match group.
        group_distance (int): Max character distance between matches to be grouped.

    Returns:
        list of str: List of context HTML snippets with highlights.
    """
    if isinstance(pattern, str):
        pattern = re.compile(re.escape(pattern), re.IGNORECASE)

    matches = list(pattern.finditer(body))
    if not matches:
        return []

    highlight = (
        lambda m: f'<strong><mark class="bg-yellow">{m.group(0)}</mark></strong>'
    )

    # Group nearby matches
    groups = []
    group = [matches[0]]

    for prev, curr in zip(matches, matches[1:]):
        if curr.start() - prev.end() < group_distance:
            group.append(curr)
        else:
            groups.append(group)
            group = [curr]
    groups.append(group)

    # Build highlighted context snippets
    results = []
    for g in groups:
        start = max(0, g[0].start() - context_chars)
        end = min(len(body), g[-1].end() + context_chars)
        snippet = body[start:end]
        if start > 0:
            snippet = "…" + snippet
        if end < len(body):
            snippet += "…"
        results.append(pattern.sub(highlight, snippet))

    return results


def replace_text_include_markdown_links(text, old_value, new_value):
    if not text:
        return text

    pattern = re.compile(re.escape(old_value), re.IGNORECASE)
    return pattern.sub(new_value, text)


def replace_text_exclude_markdown_links(text, old_value, new_value):
    if not text:
        return text

    # Find all markdown links: [text](url)
    link_pattern = re.compile(r"\[.*?\]\([^)]+\)", re.DOTALL)
    matches = list(link_pattern.finditer(text))

    # Build a list of protected ranges (the URLs only)
    protected_ranges = []
    for match in matches:
        link_text = match.group()
        # Find the position of the URL inside the link
        url_start = match.start() + link_text.find("](") + 2
        url_end = match.end() - 1  # exclude closing )
        protected_ranges.append((url_start, url_end))

    def is_inside_protected(pos):
        return any(start <= pos < end for start, end in protected_ranges)

    # Do a regex replacement, skipping protected ranges
    pattern = re.compile(re.escape(old_value), re.IGNORECASE)

    def replacement(match):
        start = match.start()
        if is_inside_protected(start):
            return match.group(0)  # Don't replace inside URLs
        return new_value

    return pattern.sub(replacement, text)


def strip_markdown_links(text):
    """
    Remove markdown links of the format ](...) from text.
    This removes the link portion but keeps the link text.
    """
    if not text:
        return text
    # Remove link URLs: ](anything)
    return re.sub(r"\]\([^)]*\)", "]", text)


def get_icon_path_choices(theme):
    if theme == "portrait-acf-white":
        return [
            (
                "nofo--icons--border",
                "(Filled) Color background, white icon, white outline",
            ),
            (
                "nofo--icons--solid",
                "(Outlined) White background, color icon, color outline",
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
            "(Outlined) White background, color icon, color outline",
        ),
    ]


def match_view_url(url):
    """
    Check if the given URL matches the pattern "/nofos/{uuid}".

    Args:
    url (str): The URL to be checked.

    Returns:
    bool: True if the URL matches the pattern, False otherwise.
    """
    # Extract the UUID part from the URL
    if not url.startswith("/nofos/"):
        return False

    uuid_part = url[len("/nofos/") :]

    try:
        uuid.UUID(uuid_part)
        return True
    except ValueError:
        return False


class StyleMapManager:
    def __init__(self, styles_to_ignore=None):
        self.styles = []
        self.styles_to_ignore = styles_to_ignore if styles_to_ignore is not None else []

    def add_style(self, style_rule, location_in_nofo=None, note=None):
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
        "BulletLevel2",
        "customXmlDelRange",
        "FootnoteReference",
        "ListParagraph",
        "Listpara2",
        "non-row element in table",
        "Normal_0",
        "v:",
        "w:",
        "office-word:",
    ]
)

# Explicit list styles
style_map_manager.add_style(
    style_rule="p[style-name='Bullet 3'] => ul|ol > li > ul|ol > li > ul > li:fresh",
    location_in_nofo="This represents a double nested bullet list improperly formatted",
    note="Convert them to li elements.",
)
style_map_manager.add_style(
    style_rule="p[style-name='Bullet 2 Calibri'] => ul|ol > li > ul > li:fresh",
    note="Bullet list 2",
)
style_map_manager.add_style(
    style_rule="p[style-name='Bullet 2'] => ul|ol > li > ul > li:fresh",
    note="Bullet list 2",
)


# list styles
style_map_manager.add_style(
    style_rule="p:unordered-list(1) => ul > li:fresh",
    note="Bullet list 1",
)
style_map_manager.add_style(
    style_rule="p:unordered-list(2) => ul|ol > li > ul > li:fresh",
    note="Bullet list 2",
)
style_map_manager.add_style(
    style_rule="p:unordered-list(3) => ul|ol > li > ul|ol > li > ul > li:fresh",
    note="Bullet list 3",
)
style_map_manager.add_style(
    style_rule="p:unordered-list(4) => ul|ol > li > ul|ol > li > ul|ol > li > ul > li:fresh",
    note="Bullet list 4",
)
style_map_manager.add_style(
    style_rule="p:unordered-list(5) => ul|ol > li > ul|ol > li > ul|ol > li > ul|ol > li > ul > li:fresh",
    note="Bullet list 5",
)
style_map_manager.add_style(
    style_rule="p:unordered-list(6) => ul|ol > li > ul|ol > li > ul|ol > li > ul|ol > li > ul|ol > li > ul > li:fresh",
    note="Bullet list 6",
)
style_map_manager.add_style(
    style_rule="p:ordered-list(1) => ol > li:fresh",
    note="Numbered list 1",
)
style_map_manager.add_style(
    style_rule="p:ordered-list(2) => ul|ol > li > ol > li:fresh",
    note="Numbered list 2",
)
style_map_manager.add_style(
    style_rule="p:ordered-list(3) => ul|ol > li > ul|ol > li > ol > li:fresh",
    note="Numbered list 3",
)
style_map_manager.add_style(
    style_rule="p:ordered-list(4) => ul|ol > li > ul|ol > li > ul|ol > li > ol > li:fresh",
    note="Numbered list 4",
)
style_map_manager.add_style(
    style_rule="p:ordered-list(5) => ul|ol > li > ul|ol > li > ul|ol > li > ul|ol > li > ol > li:fresh",
    note="Numbered list 5",
)
style_map_manager.add_style(
    style_rule="p:ordered-list(6) => ul|ol > li > ul|ol > li > ul|ol > li > ul|ol > li > ul|ol > li > ol > li:fresh",
    note="Numbered list 6",
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
    style_rule="r[style-name='findhit'] => span",
    location_in_nofo="Step 4 > Criteria > Budget and budget justification",
    note="Don't do anything: body text",
)
style_map_manager.add_style(
    style_rule="r[style-name='cf21'] => span",
    location_in_nofo="Step 1 > Data, monitoring, and evaluation > Indirect costs",
    note="Don't do anything: body text",
)
style_map_manager.add_style(
    style_rule="r[style-name='Default'] => span",
    location_in_nofo="Contacts and Support > Agency contacts > phone number",
    note="Don't do anything: body text",
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
    style_rule="r[style-name='Style Bold'] => strong.style-bold",
    location_in_nofo="All over the place",
    note="Most of the time the intent here is bold text.",
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
    style_rule="r[style-name='Heading 2 Char'] => h2:fresh",
    location_in_nofo="Step 1 > Related work",
    note="This signifies an h2",
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
style_map_manager.add_style(
    style_rule="r[style-name='Heading 6 Char'] => h6:fresh",
    location_in_nofo="Step 1 > Purpose > Strategies and activities >  Strategy 1:",
    note="This signifies an h6",
)

# paragraph styles
style_map_manager.add_style(
    style_rule="p[style-name='heading 7'] => div[role='heading'][aria-level='7']",
    location_in_nofo="Step 1 > Summary > Funding Strategy > Component Funding > Overview",
    note="This is how we represent H7s",
)
style_map_manager.add_style(
    style_rule="p[style-name='heading 8'] => div.heading-8",
    location_in_nofo="Step 1 > Approach > Strategies and activities > Component 1 > Required activities (years 1 and 2)",
    note="This is an H8, which we don't formally support",
)
style_map_manager.add_style(
    style_rule="p[style-name='Default'] => p",
    location_in_nofo="Step 6 > Reporting > All content in table",
    note="Don't do anything: this is being applied to paragraphs in a table and we don't need special styling for them.",
)
style_map_manager.add_style(
    style_rule="p[style-name='Table'] => p",
    location_in_nofo="Step 3 > Other required forms > All table cells",
    note="Don't do anything: this is being applied to paragraphs in a table and we don't need special styling for them.",
)
style_map_manager.add_style(
    style_rule="p[style-name='Table Paragraph'] => p",
    location_in_nofo="Step 1 > Approach > Table: strategies and outcomes > All paragraphs in table cells",
    note="Don't do anything: this is being applied to paragraphs in a table and we don't need special styling for them.",
)
style_map_manager.add_style(
    style_rule="p[style-name='Table Head'] => span",
    location_in_nofo="Step 4 > Critera > table headings",
    note="This is the paragraph _inside of a_ table heading.",
)
style_map_manager.add_style(
    style_rule="p[style-name='Do not use main'] => p:fresh",
    location_in_nofo="Step 1 > Empty paragraph between Have questions? and Key Dates",
    note="Don't do anything: just an empty return.",
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
    style_rule="p[style-name='p_0'] => p:fresh",
    location_in_nofo="Step 1 > Work plan > Text inside of a table",
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
    style_rule="p[style-name='Bullet'] => ul > li:fresh",
    location_in_nofo="This represents a bullet list improperly formatted",
    note="Convert them to li elements.",
)
style_map_manager.add_style(
    style_rule="p[style-name='Bullet Level 1'] => ul > li:fresh",
    location_in_nofo="This represents a bullet list improperly formatted",
    note="Convert them to li elements.",
)
style_map_manager.add_style(
    style_rule="p[style-name='List Bullet1'] => ul > li:fresh",
    location_in_nofo="This represents a bullet list improperly formatted",
    note="Convert them to li elements.",
)
style_map_manager.add_style(
    style_rule="p[style-name='No Spacing'] => span",
    location_in_nofo="This represents a non-breaking space",
    note="Convert to a non-breaking space.",
)
style_map_manager.add_style(
    style_rule="p[style-name='Do not use bullet'] => p",
    location_in_nofo="Step 1 > Approach > Organizational capacity",
    note="This is just a regular paragraph, from what I can tell.",
)
style_map_manager.add_style(
    style_rule="p[style-name='Instructions'] => p:fresh",
    location_in_nofo="Step 1 > Program description > Background overview > List items",
    note="These are lists in the document we have seen, but the p:list rules above will catch them first",
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
