# HTML tables


def add_caption_to_table(table):
    """
    Adds a caption to a table from the text in previous siblings.

    Looks for the first previous sibling element with a name and text,
    extracts it to use as the caption, and inserts it into the table.
    """
    caption = None

    for s in table.previous_siblings:
        if s.name and len(s.text):
            caption = s.extract()  # remove element from the tree
            break

    if caption:
        caption.name = "caption"  # reassign tag to <caption>
        table.insert(0, caption)


def add_class_to_table(table):
    """
    Adds a size class to a BeautifulSoup table based on column count.

    Counts the columns in the first row and adds a class like "table--small",
    "table--medium", or "table--large" depending on the column count.
    """

    def _get_table_class(num_cols):
        if num_cols <= 2:
            return "table--small"
        elif num_cols <= 4:
            return "table--medium"

        return "table--large"

    row = table.find("tr")
    cols = row.find_all("th") + row.find_all("td")
    # maybe count rows also??

    return _get_table_class(len(cols))


# Icons


def get_icon_for_section(section_name="review the opportunity"):
    """
    Returns the icon filename for the given section name and theme.

    Looks up the icon filename from the predefined list of section name ->
    icon filename mappings. If no match is found, returns the default
    "review" icon.

    section_name: The name of the section to get the icon for.
    """
    icon_tuples = [
        ("review the opportunity", "1-review.svg"),
        ("ready", "2-get-ready.svg"),
        ("write", "3-write.svg"),
        ("learn about review", "4-learn.svg"),
        ("submit", "5-submit.svg"),
        ("learn what happens", "6-next.svg"),
        ("contacts", "7-contact.svg"),
    ]
    section_name = section_name.lower()

    for search_term, filename in icon_tuples:
        if search_term in section_name:
            return "img/figma-icons/{}".format(filename)

    # return 'review' by default if section name doesn't match
    return "img/figma-icons/1-review.svg"


# Footnotes


def is_footnote_ref(a_tag):
    """
    Checks if the given a_tag is a footnote reference link
    by verifying it matches the expected footnote link format: eg, "[1]" or "[10]"
    """
    text = a_tag.get_text().strip()
    return (
        len(text) >= 3  # at least 3 characters
        and text.startswith("[")
        and text.endswith("]")
        and text[1:-1].isdigit()
    )


def format_footnote_ref(a_tag):
    """
    Formats a footnote reference link tag to have the expected ID and href attributes
    based on whether it is an endnote or inline footnote reference.

    Inline footnote links look like "<a href="#ref10">[10]</a>"
    Endnote footnote links look like "<a href="#ftnt_ref10">[10]</a>"
    """
    footnote_text = a_tag.get_text().strip()
    footnote_number = footnote_text[1:-1]
    footnote_href = a_tag.get("href").strip()

    a_tag.string = footnote_text

    # these are the endnotes references
    if footnote_href.startswith("#ftnt_"):
        a_tag["id"] = "ftnt{}".format(footnote_number)

    # these are in the body of the document
    else:
        a_tag["id"] = "ftnt_ref{}".format(footnote_number)
        a_tag["href"] = "#ftnt{}".format(footnote_number)
