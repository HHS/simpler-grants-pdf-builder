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
    Adds a size class to a BeautifulSoup table based on column and row count.

    Counts the columns in the first row and the number of rows:
     - "table--small": 2 columns or less, 4 rows or less
     - "table--medium": 3-4 columns or5-6 rows
     - "table--large": 5 columns or more, 7 rows or more
    """

    def _get_table_class(num_cols, num_rows):
        if num_cols >= 5 or num_rows >= 7:
            return "table--large"

        elif num_cols >= 3 or num_rows >= 5:
            return "table--medium"

        return "table--small"

    rows = table.find_all("tr")
    cols = rows[0].find_all("th") + rows[0].find_all("td")

    return _get_table_class(len(cols), len(rows))


# Icons


def get_icon_for_section(section_name="review the opportunity", theme=""):
    """
    Returns the icon filename for the given section name and theme.

    Looks up the icon filename from the predefined list of section name ->
    icon filename mappings. If no match is found, returns the default
    "review" icon.

    section_name: The name of the section to get the icon for.
    """
    no_border = "/no-border" if "blue" in theme else ""
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
            return "img/figma-icons{}/{}".format(no_border, filename)

    # return 'review' by default if section name doesn't match
    return "img/figma-icons{}/1-review.svg".format(no_border)


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
