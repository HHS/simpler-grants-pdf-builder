from bs4 import NavigableString

# HTML tables


def _add_class_if_not_exists_to_tag(element, classname, tag_name):
    """
    Adds the given class to the element if it does not already exist.
    Checks if the classname exists in the element's "class" attribute
    and adds it if missing. Also checks if tag_name matches the element's name.
    """
    if classname not in element.get("class", []):
        if tag_name and element.name == tag_name:
            element["class"] = element.get("class", []) + [classname]


def _add_class_if_not_exists_to_tags(element, classname, tag_names):
    """
    Adds the given class to the element if it does not already exist.
    Checks if the classname exists in the element's "class" attribute
    and adds it if missing. Also checks if tag_name matches the element's name.
    """
    for tag_name in tag_names.split("|"):
        _add_class_if_not_exists_to_tag(element, classname, tag_name)


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

    for s in table.previous_siblings:
        if s.name and len(s.text):
            if s.text.lower().startswith(caption_text):
                s.string = s.text  # strip spans
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
        if num_cols >= 3:
            return "table--large"

        return "table--small"

    def _get_total_word_count(table):
        word_count = 0

        for cell in table.find_all("td"):
            cell_text = cell.get_text()
            # Split the text into words based on whitespace and count them
            words = cell_text.split()
            word_count += len(words)

        return word_count

    if is_callout_box_table_markdown(table):
        return "table--callout-box"

    rows = table.find_all("tr")
    cols = rows[0].find_all("th") + rows[0].find_all("td")

    if table.find("th", string="Recommended For"):
        return "table--large"

    word_count = _get_total_word_count(table)

    if word_count == 0:
        if len(cols) > 3:
            return "table--large table--empty"

        return "table--small table--empty"

    elif word_count > 120:
        return "table--large"

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


def _get_icon_path_from_theme(theme, section, nofo_number="", nofo_icon_path=""):
    """
    Returns the path to the given theme's icons.

    Note that icon style is determined by the opdiv, the colour, and the nofo section.
    """
    # Note: split out this logic if it starts getting too complicated
    colour = theme.split("-")[-1]
    opdiv = theme.split("-")[-2]

    # med-blue icons for the table of contents in this one NOFO
    if nofo_number and nofo_number.lower() == "cdc-rfa-dp-24-0023":
        if section == "toc":
            return "img/figma-icons/med-blue-border"

    if section == "toc":
        if nofo_icon_path:
            return nofo_icon_path

        if "orr" in theme:
            return "img/figma-icons/orr-blue-border"
        if colour == "white":
            if "ihs" in theme:
                return "img/figma-icons/ihs-blue-border"
            elif "acf" in theme:
                return "img/figma-icons/acf-black-border"
            elif opdiv == "acl":
                return "img/figma-icons/acl-blue-border"
            else:
                return "img/figma-icons/med-blue-border"
        else:
            return "img/figma-icons/white-icon"

    if section == "before_you_begin":
        if "dop" in theme:
            return "img/figma-icons/dop-teal-border"
        if "orr" in theme:
            return "img/figma-icons/orr-blue-border"
        if opdiv == "ihs":
            return "img/figma-icons/ihs-blue-border"
        if opdiv == "acl":
            return "img/figma-icons/acl-blue-border"
        if opdiv == "acf":
            return "img/figma-icons/acf-black-border"
        if opdiv == "hrsa":
            return "img/figma-icons/dark-blue-border"
        elif opdiv == "cms":
            return "img/figma-icons/cms-blue-border"
        else:
            return "img/figma-icons/med-blue-border"

    if section == "callout_box":
        if "dop" in theme:
            return "img/figma-icons/dop"
        if "orr" in theme:
            return "img/figma-icons/black-icon"
        if opdiv == "ihs":
            return "img/figma-icons/ihs-blue-border"
        if opdiv == "acf":
            return "img/figma-icons/acf-black-border"
        if opdiv == "acl":
            return "img/figma-icons/black-icon"
        if colour == "white":
            return "img/figma-icons/dark-blue-border"

    if section == "section_cover":
        if opdiv == "ihs":
            return "img/figma-icons/ihs-blue-border"
        if opdiv == "acf":
            return "img/figma-icons/acf-black-border"
        if opdiv == "acl":
            return "img/figma-icons/acl-blue-border"
        if theme == "portrait-cms-white":
            return "img/figma-icons/cms-blue-border"

        elif "cdc-white" in theme:
            return "img/figma-icons/med-blue-border"

    return "img/figma-icons/white-border"


def get_icon_from_theme(
    icon_name="review the opportunity",
    theme="portrait-cdc-blue",
    section="section_cover",
    nofo_number="",
    nofo_icon_path="",
):
    """
    Returns the icon filename for the given section name and theme.

    Looks up the icon filename from the predefined list of section name ->
    icon filename mappings. If no match is found, returns the default
    "review" icon.

    Uses the theme to return the path to the icon.

    section_name: The name of the section to get the icon for.
    """
    icon_tuples = [
        ("adobe", "00-adobe-pdf.svg"),
        ("before you begin", "0-before.svg"),
        ("review the opportunity", "1-review.svg"),
        ("ready", "2-get-ready.svg"),
        ("write", "3-write.svg"),
        ("prepare your application", "3-write.svg"),
        ("learn about review", "4-learn.svg"),
        ("submit", "5-submit.svg"),
        ("learn what happens", "6-next.svg"),
        ("contacts", "7-contact.svg"),
    ]
    icon_name = icon_name.lower()

    icon_path = _get_icon_path_from_theme(theme, section, nofo_number, nofo_icon_path)

    for search_term, filename in icon_tuples:
        if search_term in icon_name:
            return "{}/{}".format(icon_path, filename)

    # return 'review' by default if section name doesn't match
    return "{}/1-review.svg".format(icon_path)


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
