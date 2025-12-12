import re

from bs4 import BeautifulSoup, NavigableString

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
        if s.name and s.name != "table" and len(s.text):
            if s.text.lower().startswith(caption_text):
                s.string = s.text  # strip spans
                caption = s.extract()  # remove element from the tree
            break

    if caption:
        caption.name = "caption"  # reassign tag to <caption>
        table.insert(0, caption)
        _add_class_if_not_exists_to_tag(table, "table--with-caption", "table")


def add_class_to_list(html_list):
    # Get the last list item
    final_list_item = html_list.find_all("li")[-1] if html_list.find_all("li") else None
    if final_list_item:
        # Check if the text length is less than 85 characters
        if len(final_list_item.get_text(strip=True)) < 85:
            # Add the classname
            _add_class_if_not_exists_to_tag(
                final_list_item, "avoid-page-break-before", "li"
            )


def add_class_to_nofo_title(nofo_title):
    if len(nofo_title) > 225:
        return "nofo--cover-page--title--h1--very-very-smol"

    if len(nofo_title) > 165:
        return "nofo--cover-page--title--h1--very-smol"

    if len(nofo_title) > 120:
        return "nofo--cover-page--title--h1--smaller"

    return "nofo--cover-page--title--h1--normal"


def _get_total_word_count(table_cells):
    word_count = 0

    for cell in table_cells:
        cell_text = cell.get_text()
        # Split the text into words based on whitespace and count them
        words = cell_text.split()
        word_count += len(words)

    return word_count


def add_class_to_table(table):
    """
    Adds a size class to a BeautifulSoup table based on column and row count.

    First checks if the table is a "callout box" using the `is_callout_box_table_markdown` function.
     - "table--callout-box": this table is a callout box

    Secondly, checks for content of table headings:
    - "table--large": th found with "Recommended For"
    - "table--criterion": th found with "Criterion"

    Finally, look at columns and word count:
    - "table--small": fewer than 4 columns and no words
    - "table--large": total word count exceeds 120 words
    - "table--small" for 2 columns or less
    - "table--large" for 3 columns or more
    """

    def _get_table_class(num_cols):
        if num_cols >= 3:
            return "table--large"

        return "table--small"

    if is_callout_box_table_markdown(table):
        return "table--callout-box"

    rows = table.find_all("tr")
    if rows:
        cols = rows[0].find_all("th") + rows[0].find_all("td")

        if table.find("th", string="Recommended For"):
            return "table--large"

        if table.find("th", string="Criterion"):
            return "table--criterion"

        word_count = _get_total_word_count(table.find_all("td"))

        if word_count == 0 and len(cols) < 4:
            return "table--small"
        elif word_count > 120:
            return "table--large"

        return _get_table_class(len(cols))

    return "table--invalid"


def add_class_to_table_rows(table_row):
    """
    Adds a size class to a BeautifulSoup table cell based on if the row is empty.
    """

    word_count = _get_total_word_count(table_row.find_all(["td", "th"]))

    if word_count == 0:
        return "table-row--empty"


def convert_paragraph_to_searchable_hr(p):
    def _create_hr_and_span(hr_class, span_text):
        hr_html = '<hr class="{} page-break--hr">'.format(hr_class)
        span_html = '<span class="page-break--hr--text">{}</span>'.format(span_text)
        return BeautifulSoup(hr_html, "html.parser"), BeautifulSoup(
            span_html, "html.parser"
        )

    if p.name == "p" and p.string in [
        "page-break",
        "page-break-before",
        "page-break-after",
        "column-break-before",
        "column-break-after",
    ]:
        # Change the tag name from 'p' to 'div'
        p.name = "div"

        if p.string == "page-break" or p.string == "page-break-before":
            p["class"] = "page-break--hr--container"
            hr, span = _create_hr_and_span("page-break-before", "[ ↓ page-break ↓ ]")

        if p.string == "page-break-after":
            p["class"] = "page-break--hr--container"
            hr, span = _create_hr_and_span("page-break-after", "[ ↓ page-break ↓ ]")

        if p.string == "column-break-before":
            p["class"] = "page-break--hr--container"
            hr, span = _create_hr_and_span(
                "column-break-before", "[ ← column-break-before ← ]"
            )

        if p.string == "column-break-after":
            p["class"] = "page-break--hr--container"
            hr, span = _create_hr_and_span(
                "column-break-after", "[ → column-break-after → ]"
            )

        p.clear()
        p.append(hr)
        p.append(span)


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


def filter_breadcrumb_sections(sections):
    """
    Filters a list of section objects to include only those whose names
    start with specific keywords: "step", "contacts", or "learn" (case-insensitive).
    """
    return [
        section
        for section in sections
        if section.name.lower().startswith(("step", "contacts", "learn"))
    ]


def get_breadcrumb_text(section_name):
    """
    Maps a section name to its corresponding breadcrumb link text.

    This function uses a predefined mapping to convert longer section names
    into concise breadcrumb link text. If no match is found, it returns a default
    placeholder ("⚠️ TODO ⚠️").

    Notes:
        - The mapping is case-insensitive.
        - Partial matches are used, so "Get Ready to Apply" will match "ready".
    """
    breadcrumb_text_map = {
        "review the opportunity": "Review",
        "review the funding opportunity": "Review",
        "ready": "Get Ready",
        "write your application": "Write",
        "understand review": "Understand",
        "prepare your application": "Prepare",
        "build your application": "Build",
        "learn about review": "Learn",
        "submit": "Submit",
        "learn what happens": "Award",
        "contacts": "Contacts",
    }

    # Find a match in name_map
    for key, value in breadcrumb_text_map.items():
        if key in section_name.lower():
            return value

    # Default case
    return "⚠️ TODO ⚠️"


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
    if rows:
        cols = rows[0].find_all("th") + rows[0].find_all("td")
        tds = table.find_all("td")

        return (
            len(cols) == 1  # 1 column
            and len(rows) == 2  # 2 rows (thead and tbody generated automatically)
            and len(tds) == 1  # 1 cell
            and tds[0]
            and tds[0].get_text().strip() == ""  # the cell is empty
        )

    return False


# Footnotes


def is_footnote_ref(a_tag):
    """
    Checks if the given a_tag is a footnote reference link
    by verifying it matches the expected footnote link format: eg, "[1]" or "[10]", or "↑"
    """
    text = a_tag.get_text().strip()
    if text == "↑":
        return True

    return (
        len(text) >= 3  # at least 3 characters
        and text.startswith("[")
        and text.endswith("]")
        and text[1:-1].isdigit()
    )


def get_footnote_type(a_tag):
    href = a_tag.get("href", "").strip()

    # HTML
    # Inline footnote links look like "<a href="#ref10">[10]</a>"
    # Endnote footnote links look like "<a href="#ftnt_ref10">[10]</a>"
    if href.startswith("#ref") or href.startswith("#ftnt"):
        return "html"

    # DOCX
    # Inline FOOTNOTE links look like "<a href="#footnote-1">[2]</a>"
    # Bottom-of-doc FOOTNOTE links look like "<a href="#footnote-ref-1">↑</a>"

    # Inline ENDNOTE links look like "<a href="#endnote-2" id="endnote-ref-2">[1]</a>"
    # Bottom-of-doc ENDNOTE links look like "<a href="#endnote-ref-2">↑</a>"
    if href.startswith(("#footnote", "#endnote")):
        return "docx"

    return None


def format_footnote_ref_html(a_tag):
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


def is_floating_callout_box(subsection):
    # maybe not the best idea long-term but it works for now
    floating_subsection_strings = [
        "Key facts",
        "Key Facts",
        "Key dates",
        "Key Dates",
        "Questions?",
        "Have questions?",
        "**Have questions?",
        "**Have** **questions?**",
    ]

    if subsection.name:
        return subsection.name.strip() in floating_subsection_strings

    for subsection_string in floating_subsection_strings:
        if subsection.body.strip().startswith(subsection_string):
            return True

    return False


def match_numbered_sublist(text):
    # Match patterns like:
    # - "1. "
    # - "8-15."
    # - "16 - 21."
    # - "22 through 25."
    # - "30 to 40. "
    # - "45—50. "
    pattern = r"^\d+(\s?(-|—|to|through)\s?\d+)?\.\s"

    # Check if the text matches any of the sublist numbering patterns
    return re.match(pattern, text)


def wrap_text_before_colon_in_strong(p, soup):
    if not ":" in p.get_text():
        return p

    # Initialize a flag to track when the colon is found
    found_colon = False
    # Create a strong tag
    strong_tag = soup.new_tag("strong")
    span_tag = soup.new_tag("span")

    # Iterate over contents, moving elements before the colon to the strong tag
    for content in p.contents[:]:
        if found_colon:
            span_tag.append(content.extract())
        else:
            if isinstance(content, str) and ":" in content:
                before_colon, after_colon = content.split(":", 1)
                strong_tag.append(before_colon + ":")
                # Replace the original content with what's after the colon
                span_tag.append(after_colon)
                found_colon = True  # Mark colon as found
            else:
                # Move content to strong tag if colon not yet found
                strong_tag.append(content.extract())

    # insert an extra space after the colon in the strong tag
    strong_tag.append(" ")

    # Insert the strong tag at the beginning of the paragraph
    p.clear()
    p.append(strong_tag)
    p.append(span_tag)
