import re

from slugify import slugify


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


def clean_string(string):
    """Cleans the given string by removing extra whitespace."""
    return re.sub("\s+", " ", string.strip())


def create_subsection_html_id(counter, subsection):
    section_name = subsection.section.name
    return "{}--{}--{}".format(counter, slugify(section_name), slugify(subsection.name))


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
style_map_manager = StyleMapManager(["ListParagraph", "Bullet2", "FootnoteReference"])

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
    style_rule="r[style-name='criteria-linked-element_data-mode=export_criteria-score'] => span.linked-element",
    location_in_nofo="Step 4 > Maximum points > 20",
    note="Don't do anything: body text",
)
style_map_manager.add_style(
    style_rule="r[style-name='Intense Reference'] => span.intense-reference",
    location_in_nofo="Step 3 > Required format",
    note="Don't do anything: it's formatted as a header already, go with that.",
)
style_map_manager.add_style(
    style_rule="r[style-name='Subtle Emphasis'] => strong.subtle-emphasis",
    location_in_nofo="Step 3 > Required format > Fonts/Spacing",
    note="Bold is safe, but they might possibly be headings.",
)
style_map_manager.add_style(
    style_rule="r[style-name='Heading 3 Char'] => h4:fresh",
    location_in_nofo="Step 1 > Program description > Four core functions",
    note="This signifies an h3, which we demote to h4",
)
style_map_manager.add_style(
    style_rule="r[style-name='Heading 5 Char'] => h6:fresh",
    location_in_nofo="Step 1 > Cost-sharing commitments > Reduced Match",
    note="This signifies an h5, which we demote to h6",
)

# paragraph styles
style_map_manager.add_style(
    style_rule="p[style-name='Table'] => p",
    location_in_nofo="Step 3 > Other required forms > All table cells",
    note="Don't do anything: this is being applied to paragraphs in a table and we don't need special styling for them.",
)
style_map_manager.add_style(
    style_rule="p[style-name='Normal (Web)'] => p",
    location_in_nofo="Step 4 > Risk Review > p",
    note="Don't do anything: not sure why this is formatted differently, but it's just body text.",
)
style_map_manager.add_style(
    style_rule="p[style-name='div'] => p",
    location_in_nofo="Step 1 > Key facts > Name and number",
    note="Don't do anything: regular body text.",
)
style_map_manager.add_style(
    style_rule="p[style-name='paragraph'] => p",
    location_in_nofo="Step 1 > Eligibility > Who can apply",
    note="Don't do anything: regular body text.",
)
style_map_manager.add_style(
    style_rule="p[style-name='Main Heading'] => p",
    location_in_nofo="Step 1 > Key facts > number",
    note="Don't do anything: regular body text (may not be true for all, but let's assume).",
)
style_map_manager.add_style(
    style_rule="p[style-name='Normal_0'] => p",
    location_in_nofo="Step 3 > Budget justification narrative > Applicants are encouraged...",
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
