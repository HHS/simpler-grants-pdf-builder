from bs4 import NavigableString

# HTML tables


def add_caption_to_table(table):
    """
    Adds a caption to a BeautifulSoup table element.

    Searches previous sibling elements for a paragraph starting with "table: ",
    extracts it and inserts it as a <caption> element inside the table.
    If a caption is added, it also adds a class to the table.

    Args:
        table: A BeautifulSoup table element
    """
    caption = None
    # we want to look for paragraphs that start with "table: "
    caption_text = "table: "

    def _add_class_if_not_exists_to_tag(element, classname, tag_name=None):
        if classname not in element.get("class", []):
            if tag_name and element.name == tag_name:
                element["class"] = element.get("class", []) + [classname]

    for s in table.previous_siblings:
        if s.name and len(s.text):
            if s.text.lower().startswith(caption_text):
                s.string = s.text[len(caption_text) :]
                caption = s.extract()  # remove element from the tree
            break

    if caption:
        caption.name = "caption"  # reassign tag to <caption>
        table.insert(0, caption)
        _add_class_if_not_exists_to_tag(table, "table--with-caption", "table")


def add_class_to_table(table):
    """
    Adds a size class to a BeautifulSoup table based on column and row count.

    Counts the columns in the first row and the number of rows:
     - "table--small": 3 columns or less
     - "table--large": 4 columns or more
    """

    def _get_table_class(num_cols):
        if num_cols >= 4:
            return "table--large"

        return "table--small"

    if is_callout_box_table_markdown(table):
        return "table--callout-box"

    rows = table.find_all("tr")
    cols = rows[0].find_all("th") + rows[0].find_all("td")

    return _get_table_class(len(cols))


def find_elements_with_character(element, container, character="~"):
    # Recursively searches the element and its children for any strings containing the given character.
    # Any elements containing the character are added to the given container.
    # Parameters:
    #   element: The element to search through
    #   container: The list to add any found elements to
    #   character: The character to search for in strings
    if isinstance(element, NavigableString):
        if character in element:
            container.append(element.parent)
    else:
        for child in element.children:
            find_elements_with_character(child, container, character)


def get_parent_td(element):
    """
    Gets the parent <td> element for a given element, which may include itself.

    Traverses up the element's parents looking for a <td> tag.
    Returns the first parent <td> found, or False if none exists.
    """
    if element.name == "td":
        return element

    for parent in element.parents:
        if parent.name == "td":
            return parent

    return False


def is_callout_box_table_markdown(table):
    rows = table.find_all("tr")
    cols = rows[0].find_all("th") + rows[0].find_all("td")
    tds = table.find_all("td")

    return (
        len(cols) == 1  # 1 column
        and len(rows) == 2  # 2 rows (thead and tbody generated automatically)
        and len(tds) == 1  # 1 cell
        and tds[0]
        and tds[0].get_text().strip() == ""  # the cell is empty
    )


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
        ("before you begin", "0-before.svg"),
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
