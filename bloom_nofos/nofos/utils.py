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
            ("nofo--icons--border", "(Filled) Color background, white icon, white outline"),
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
        )
    ]
