import datetime
import re
import markdown
from urllib.parse import parse_qs, urlparse
from django.db import transaction

from bs4 import BeautifulSoup, NavigableString, Tag
from markdownify import MarkdownConverter
from slugify import slugify

from .models import Nofo, Section, Subsection
from .utils import clean_string

DEFAULT_NOFO_OPPORTUNITY_NUMBER = "NOFO #999"


class ListInATableConverter(MarkdownConverter):
    """
    Leave ULs and OLs TDs as HTML
    """

    def convert_ol(self, el, text, convert_as_inline):
        for parent in el.parents:
            if parent.name == "td":
                return str(el)

        return super().convert_ol(el, text, convert_as_inline)

    def convert_ul(self, el, text, convert_as_inline):
        for parent in el.parents:
            if parent.name == "td":
                return str(el)

        return super().convert_ul(el, text, convert_as_inline)

    def convert_p(self, el, text, convert_as_inline):
        # if we are in a table cell, and that table cell contains multiple children, return the string
        if el.parent.name == "td":
            if len(list(el.parent.children)) > 1:
                return str(el)

        return super().convert_p(el, text, convert_as_inline)


# Create shorthand method for conversion
def md(html, **options):
    return ListInATableConverter(**options).convert(html)


@transaction.atomic
def add_headings_to_nofo(nofo):
    new_ids = []
    # add counter because subheading titles can repeat, resulting in duplicate IDs
    counter = 1

    # add ids to all section headings
    for section in nofo.sections.all():
        section_id = "{}".format(slugify(section.name))

        if section.html_id and len(section.html_id):
            new_ids.append({"old_id": section.html_id, "new_id": section_id})

        section.html_id = section_id

        if not section.html_id or len(section.html_id) == 0:
            raise ValueError("html_id blank for section: {}".format(section.name))

        section.save()

        # add ids to all subsection headings
        for subsection in section.subsections.all():
            subsection_id = "{}--{}--{}".format(
                counter, section_id, slugify(subsection.name)
            )

            if subsection.html_id:
                new_ids.append({"old_id": subsection.html_id, "new_id": subsection_id})

            subsection.html_id = subsection_id
            subsection.save()
            counter += 1

    # replace all old ids with new ids
    for section in nofo.sections.all():
        for subsection in section.subsections.all():
            for ids in new_ids:
                subsection.body = subsection.body.replace(ids["old_id"], ids["new_id"])

            subsection.save()


def add_newline_to_ref_numbers(text):
    """
    Adds a newline character after a pattern that matches 'ref' followed by a one or two-digit number and a parenthesis.

    Args:
    text (str): The input string.

    Returns:
    str: The modified string with newline characters added after the specified pattern.
    """
    # Regular expression pattern to match 'ref' followed by a one or two-digit number and a parenthesis
    pattern = r"(ref\d{1,2}\))"

    # Replace the found pattern with itself followed by a newline
    modified_text = re.sub(pattern, r"\1\n", text)

    return modified_text


def format_endnotes(md_body):
    """
    Processes and formats the endnotes in a Markdown body text.

    This function performs two primary tasks:
    1. Removes non-breaking space characters (nbsp) from the Markdown text.
    2. Splits the Markdown text into endnotes based on newline characters and
       adds a newline character after any pattern matching 'ref' followed by a
       one or two-digit number and a parenthesis (like 'ref10)', 'ref1)', etc.).

    Args:
    md_body (str): A string representing the Markdown text to be processed.

    Returns:
    str: The processed and formatted Markdown text with formatted endnotes.
    """
    # remove non-breaking spaces
    md_body = md_body.replace("\xa0", "")

    endnotes = md_body.split("\n")
    for i, endnote in enumerate(endnotes):
        endnotes[i] = add_newline_to_ref_numbers(endnote)

    return "\n".join(endnotes)


def _build_nofo(nofo, sections):
    for section in sections:
        model_section = Section(
            name=section.get("name", "Section X"),
            order=section.get("order", ""),
            html_id=section.get("html_id", None),
            has_section_page=section.get("has_section_page"),
            nofo=nofo,
        )
        model_section.save()

        for subsection in section.get("subsections", []):
            md_body = ""
            html_body = [str(tag).strip() for tag in subsection.get("body", [])]

            if html_body:
                md_body = md("".join(html_body))

            if subsection.get("name") == "Endnotes":
                md_body = format_endnotes(md_body)

            model_subsection = Subsection(
                name=subsection.get("name", ""),
                order=subsection.get("order", ""),
                tag=subsection.get("tag", ""),
                html_id=subsection.get("html_id"),
                callout_box=subsection.get("is_callout_box", False),
                body=md_body,  # body can be empty
                section=model_section,
            )
            model_subsection.save()

    return nofo


def create_nofo(title, sections):
    nofo = Nofo(title=title)
    nofo.number = "NOFO #999"
    nofo.save()
    return _build_nofo(nofo, sections)


def overwrite_nofo(nofo, sections):
    nofo.sections.all().delete()
    nofo.save()
    return _build_nofo(nofo, sections)


def convert_table_first_row_to_header_row(table):
    # Converts the first row of cells in the given table
    # to header cells by changing the <td> tags to <th>.
    # Assumes the first row is a header row.
    first_row = table.find("tr")
    if first_row:
        first_row_cells = first_row.find_all("td")
        for cell in first_row_cells:
            cell.name = "th"


def get_sections_from_soup(soup):
    # build a structure that looks like our model
    sections = []
    section_num = -1

    for tag in soup.find_all(True):
        if tag.name == "h1":
            section_num += 1

        if section_num >= 0:
            if len(sections) == section_num:
                # add an empty array at a new index
                section_name = clean_string(tag.text)

                has_section_page = not any(
                    word.lower() in section_name.lower()
                    for word in ["Appendix", "Glossary", "Endnotes", "References"]
                )

                sections.append(
                    {
                        "name": section_name,
                        "order": section_num + 1,
                        "html_id": tag.get("id", ""),
                        "has_section_page": has_section_page,
                        "body": [],
                    }
                )
            else:
                sections[section_num]["body"].append(tag)

    return sections


def is_in_table(tag):
    """
    Checks if the given tag is inside a table element.

    Iterates through the tag's parent elements, returning True if any parent is a table element.
    """
    for parent in tag.parents:
        if parent.name == "table":
            return True
    return False


def get_subsections_from_sections(sections):
    heading_tags = ["h2", "h3", "h4", "h5", "h6"]

    def demote_tag(tag):
        newTags = {"h2": "h3", "h3": "h4", "h4": "h5", "h5": "h6", "h6": "h7"}

        return newTags[tag.name]

    def is_callout_box_table(table):
        # NOTE: after this goes through the markdown parser, it has 2 rows, but for now it is just 1
        rows = table.find_all("tr")
        cols = rows[0].find_all("th") + rows[0].find_all("td")
        tds = table.find_all("td")

        return (
            len(cols) == 1  # 1 column
            and len(rows) == 1  # 1 row
            and len(tds) == 1  # 1 cell
        )

    def extract_first_header(td):
        for tag_name in heading_tags:
            header_element = td.find(tag_name)
            if header_element:
                # remove from the dom
                return header_element.extract()
        return False

    def get_subsection_dict(heading_tag, order, is_callout_box=False, body=None):
        if heading_tag:
            return {
                "name": clean_string(heading_tag.text),
                "order": order,
                "tag": demote_tag(heading_tag),
                "html_id": heading_tag.get("id", ""),
                "is_callout_box": is_callout_box,
                "body": body or [],
            }

        return {
            "name": "",
            "order": order,
            "tag": "",
            "html_id": "",
            "is_callout_box": True,  # has to be True if there is no heading tag
            "body": body or [],
        }

    # h1s are gone since last method
    subsection = None
    for section in sections:
        subsection = None
        section["subsections"] = []
        # remove 'body' key
        body = section.pop("body", None)

        body_descendents = [
            tag for tag in body if tag.parent.name in ["body", "[document]"]
        ]

        for tag in body_descendents:
            # NOTE: that unless a new section is triggered, a callout box will just absorb stuff behind it.
            if tag.name == "table" and is_callout_box_table(tag):
                # pass in the first heading we find in the 1 table cell, else False
                td = tag.find("td")
                # make the td a div so that it can live on its own
                td.name = "div"
                subsection = get_subsection_dict(
                    heading_tag=extract_first_header(td),
                    order=len(section["subsections"]) + 1,
                    is_callout_box=True,
                    body=td,
                )
                section["subsections"].append(subsection)

            elif tag.name in heading_tags:
                # create new subsection
                subsection = get_subsection_dict(
                    heading_tag=tag, order=len(section["subsections"]) + 1
                )

                section["subsections"].append(subsection)

            # if not a heading or callout_box table add to existing subsection
            else:
                # convert first row of header cells into th elements
                if tag.name == "table":
                    convert_table_first_row_to_header_row(tag)

                if subsection:
                    if subsection.get("is_callout_box", False):
                        raise Exception(
                            "Extra content after callout box with no home, please check the HTML. Name: {}, previous name: {}, tag: {}".format(
                                subsection.get("name"),
                                section["subsections"][-2].get("name"),
                                tag,
                            )
                        )

                    subsection["body"].append(tag)

    return sections


def _suggest_by_startswith_string(soup, startswith_string):
    suggestion = ""
    regex = re.compile("^{}".format(startswith_string), re.IGNORECASE)
    element = soup.find(string=regex)

    # look for the paragraph
    if element and element.name != "p":
        for parent in element.parents:
            if parent.name == "p":
                element = parent
                break

    if element:
        suggestion = regex.sub("", element.text)

    return suggestion.strip()


def suggest_nofo_opportunity_number(soup):
    opportunity_number_default = DEFAULT_NOFO_OPPORTUNITY_NUMBER
    suggestion = _suggest_by_startswith_string(soup, "Opportunity Number:")
    return suggestion or opportunity_number_default


def suggest_nofo_application_deadline(soup):
    nofo_application_deadline_default = "Monday, January 1, 2024"

    suggestion = _suggest_by_startswith_string(soup, "Application Deadline:")
    return suggestion or nofo_application_deadline_default


def suggest_nofo_theme(nofo_number):
    if "cdc-" in nofo_number.lower():
        return "portrait-cdc-blue"

    if "acf-" in nofo_number.lower():
        return "portrait-acf-blue"

    return "portrait-hrsa-blue"


def suggest_nofo_title(soup):
    nofo_title_default = "NOFO: {}".format(
        datetime.datetime.now().replace(microsecond=0).isoformat().replace("T", " ")
    )

    suggestion = _suggest_by_startswith_string(soup, "Opportunity Name:")
    return suggestion or nofo_title_default


def suggest_nofo_opdiv(soup):
    suggestion = _suggest_by_startswith_string(soup, "Opdiv:")
    return suggestion or ""


def suggest_nofo_agency(soup):
    suggestion = _suggest_by_startswith_string(soup, "Agency:")
    return suggestion or ""


def suggest_nofo_subagency(soup):
    suggestion = _suggest_by_startswith_string(soup, "Subagency:")
    return suggestion or ""


def suggest_nofo_subagency2(soup):
    suggestion = _suggest_by_startswith_string(soup, "Subagency2:")
    return suggestion or ""


def suggest_nofo_tagline(soup):
    suggestion = _suggest_by_startswith_string(soup, "Tagline:")
    return suggestion or ""


def suggest_nofo_author(soup):
    suggestion = _suggest_by_startswith_string(soup, "Metadata Author:")
    return suggestion or ""


def suggest_nofo_subject(soup):
    suggestion = _suggest_by_startswith_string(soup, "Metadata Subject:")
    return suggestion or ""


def suggest_nofo_keywords(soup):
    suggestion = _suggest_by_startswith_string(soup, "Metadata Keywords:")
    return suggestion or ""


def get_logo(opdiv="cdc", colour="blue"):
    if not colour or not opdiv:
        raise ValueError("opdiv and colour cannot be empty")

    if opdiv == "cdc":
        colour = colour if colour != "dop" else "white"
        return "img/logos/{0}/{1}/{0}-logo.svg".format(opdiv, colour)

    return "img/logos/cdc/blue/cdc-logo.svg".format(opdiv, colour)


def join_nested_lists(soup):
    """
    This function mutates the soup!

    Joins nested unordered lists (UL tags) in the provided BeautifulSoup soup.

    Iterates through all UL tags in the soup. For each UL tag, checks if the previous sibling is also a UL tag.
    If so, calls _join_lists() to join the two lists by:

    1. If the two UL tags have the same "class" attribute, extends the previous UL with the current UL's LI tags, then decomposes the current UL.

    2. If the classes differ, finds the last LI tag in the previous UL. If that LI contains a nested UL, recursively calls _join_lists on that nested UL and the current UL. Otherwise, appends the current UL to the previous LI.

    This mutates the original soup to remove nested ULs and join ULs with the same class.

    Returns the mutated soup.
    """

    def _get_list_classname(tag):
        for classname in tag.get("class"):
            if classname.startswith("lst-"):
                return classname
        return None

    def _get_previous_element(tag):
        for ps in tag.previous_siblings:
            if isinstance(ps, Tag):
                return ps
        return None

    def _join_lists(ul, previous_ul):
        if _get_list_classname(ul) == _get_list_classname(previous_ul):
            # if classes match, join these lists
            previous_ul.extend(ul.find_all("li"))
            ul.decompose()
            return

        # okay: classes do not match
        # get the last li in the previous list
        last_tag_in_previous_list = previous_ul.find_all("li", recursive=False)[-1]

        # see if there is a ul in there
        nested_ul = last_tag_in_previous_list.find("ul")
        if nested_ul:
            return _join_lists(ul, nested_ul)

        # if there is not, append to the last li
        last_tag_in_previous_list.append(ul)
        return

    for ul in soup.find_all("ul"):
        # check previous sibling
        previous_element = _get_previous_element(ul)
        if previous_element and previous_element.name == "ul":
            _join_lists(ul, previous_element)

    return soup


def remove_google_tracking_info_from_links(soup):
    """
    This function mutates the soup!

    It looks through all the link elements and whenever it finds one with
    Google tracking information, it returns the original URL.

    For example:
    - Before: https://www.google.com/url?q=https://www.cdc.gov/grants/additional-requirements/ar-25.html&sa=D&source=editors&ust=1706211338137807&usg=AOvVaw3QRecqJEvdFcL93eoqk6HD
    - After: https://www.cdc.gov/grants/additional-requirements/ar-25.html

    URLs that don't start with "https://www.google.com/url?" aren't modified
    """

    def _get_original_url(modified_url):
        parsed_url = urlparse(modified_url)
        query_params = parse_qs(parsed_url.query)
        original_url = query_params.get("q", [None])[0]
        return original_url

    for a in soup.find_all("a"):
        href = a.get("href", "")
        if href.startswith("https://www.google.com/url?"):
            a["href"] = _get_original_url(href)


def find_broken_links(nofo):
    """
    This function mutates the soup!

    Identifies and returns a list of broken links within a given Nofo.

    A broken link is defined as an anchor (`<a>`) element whose `href` attribute value starts with "#h." or "#id."
    This means that someone created an internal link to a header, and then later the header was deleted or otherwise
    modified so the original link doesn't point anywhere.

    Args:
        nofo (Nofo): A Nofo object which contains sections and subsections. Each subsection's body is expected
                     to be in markdown format.

    Returns:
        list of dict: A list of dictionaries, where each dictionary contains information about a broken link,
                      including the section and subsection it was found in, the text of the link, and the `href`
                      attribute of the link. The structure is as follows:
                      [
                          {
                              "section": <Section object>,
                              "subsection": <Subsection object>,
                              "link_text": "text of the link",
                              "link_href": "href of the link"
                          },
                          ...
                      ]
    """

    # Define a function that checks if an 'href' attribute starts with '#h.' or '#id.'
    def _href_starts_with_h(tag):
        return tag.name == "a" and (
            tag.get("href", "").startswith("#h.")
            or tag.get("href", "").startswith("#id.")
        )

    broken_links = []

    for section in nofo.sections.all().order_by("order"):
        for subsection in section.subsections.all().order_by("order"):
            soup = BeautifulSoup(
                markdown.markdown(subsection.body, extensions=["extra"]), "html.parser"
            )

            for link in soup.find_all(_href_starts_with_h):
                broken_links.append(
                    {
                        "section": section,
                        "subsection": subsection,
                        "link_text": link.get_text(),
                        "link_href": link["href"],
                    }
                )

    return broken_links


def combine_consecutive_links(soup):
    """
    This function mutates the soup!

    Modifies the BeautifulSoup object by combining consecutive <a> tags with the same href into a single <a> tag
    and ensures there's no whitespace between an <a> tag and following punctuation.

    This function performs three main tasks:
    1. It unwraps <span> tags that contain only an <a> tag, removing unnecessary <span> wrappers.
    2. It merges consecutive <a> tags that share the same href attribute, optionally inserting a space between merged text if
       the original tags were separated by whitespace. This helps maintain natural spacing in the text.
    3. After merging <a> tags, the function also removes any whitespace between the end of an <a> tag and the following
       punctuation (.,;!?), if present. This is crucial for ensuring correct grammar and readability in the resulting HTML.

    Args:
        soup (BeautifulSoup): A BeautifulSoup object containing the HTML to be processed.
    """

    # First, unwrap <span> tags that only contain <a> tags
    for span in soup.find_all("span"):
        if len(span.contents) == 1 and span.a:
            span.unwrap()

    # Now, merge consecutive <a> tags with the same href
    links = soup.find_all("a")
    for link in links:
        next_sibling = link.next_sibling

        # Determine if there's whitespace between this and the next <a> tag
        whitespace_between = False
        if isinstance(next_sibling, NavigableString) and next_sibling.strip() == "":
            whitespace_between = True
            if next_sibling.next_sibling and next_sibling.next_sibling.name == "a":
                next_sibling = next_sibling.next_sibling

        if (
            next_sibling
            and next_sibling.name == "a"
            and link["href"] == next_sibling["href"]
        ):
            # If there's whitespace, add a space before merging texts
            separator = " " if whitespace_between else ""
            link.string = link.get_text() + separator + next_sibling.get_text()
            # Remove the next link
            next_sibling.extract()

    # Remove spaces between the end a link and punctuation
    punctuation = {".", ",", ";", "!", "?"}
    for link in soup.find_all("a"):
        # Check if the link has a next sibling and it's a NavigableString containing only whitespace
        if (
            link.next_sibling
            and isinstance(link.next_sibling, NavigableString)
            and link.next_sibling.strip() == ""
        ):
            # Now check if there's another sibling after the whitespace and it's a punctuation mark
            next_to_whitespace = link.next_sibling.next_sibling
            if (
                next_to_whitespace
                and next_to_whitespace.string
                and next_to_whitespace.string[0] in punctuation
            ):
                # Remove the whitespace by replacing it with an empty string
                link.next_sibling.replace_with("")


def decompose_empty_tags(soup):
    """
    This function mutates the soup!

    Removes empty HTML tags from the BeautifulSoup `soup`.

    Iterates over all body descendants and `li` tags, removing any that have no textual content.
    Intended to clean up HTML extracted from PDFs or other sources that may contain many meaningless tags.

    It will, however, keep in place: brs, hrs, and tags that contain imgs.
    """
    body_descendents = soup.select("body > *")

    for tag in body_descendents:
        if not tag.get_text().strip() and tag.name not in ["br", "hr"]:
            # images have no content but should not be stripped out
            if len(tag.find_all("img")) == 0:
                tag.decompose()

    lis = soup.find_all("li")
    for li in lis:
        if not li.get_text().strip():
            li.decompose()


def clean_table_cells(soup):
    """
    This function mutates the soup!

    Cleans the content of all table cells in a Nofo.

    This function performs two main operations on each table cell (`<td>` and `<th>` elements) within a given BeautifulSoup object:
    1. Unwraps all `<span>` elements, effectively removing the `<span>` tags but keeping their contents intact in the cell.
    2. Replaces all non-breaking space characters (`\xa0`, also known as `&nbsp;` in HTML) with regular space characters.

    These operations are applied to ensure that the text within table cells is normalized for further processing or display, without unnecessary `<span>` tags or non-standard whitespace characters.

    Parameters:
    soup (BeautifulSoup): A BeautifulSoup object containing the HTML content to be cleaned. This object is modified in place.

    Returns:
    None: The function modifies the BeautifulSoup object in place and does not return a value.

    Example:
    >>> from bs4 import BeautifulSoup
    >>> html_content = "<table><tr><td><span>Example</span>\xa0Text and <a href='https://groundhog-day.com'>a link</a></td></tr></table>"
    >>> soup = BeautifulSoup(html_content, 'html.parser')
    >>> clean_table_cells(soup)
    >>> str(soup)
    '<table><tr><td>Example Text and <a href='https://groundhog-day.com'>a link</a></td></tr></table>'
    """
    for cell in soup.find_all(["td", "th"]):
        # strip spans but keep their content
        for span in cell.find_all("span"):
            span.unwrap()

        # replace newlines with regular spaces
        for text in cell.find_all(text=True):
            if "\xa0" in text:
                updated_text = text.replace("\xa0", " ")
                text.replace_with(updated_text)


def replace_src_for_inline_images(soup):
    """
    This function mutates the soup!

    Replaces the src attribute for inline images in the soup to use static image paths based on the NOFO number.

    Iterates over all img tags in the soup. If an img has a src attribute, it extracts the filename, and replaces the src with a path prefixed by the NOFO number from suggest_nofo_opportunity_number().

    For example with NOFO number "HRSA-24-017":

    - Before: images/image1.png
    - After: /static/img/inline/hrsa-24-017/image1.png
    """
    nofo_number = suggest_nofo_opportunity_number(soup)

    if nofo_number and nofo_number != DEFAULT_NOFO_OPPORTUNITY_NUMBER:
        for img in soup.find_all("img"):
            if img.get("src"):
                img_src = img["src"]
                img_filename = img_src.split(
                    "/"
                ).pop()  # get the last part of the filename
                img["src"] = "/static/img/inline/{}/{}".format(
                    nofo_number.lower(), img_filename
                )


def add_endnotes_header_if_exists(soup):
    """
    This function mutates the soup!

    Adds a header for endnotes if final <hr> tag has no style attribute.

    Checks if the last <hr> tags in the soup has no style attribute.
    If so, takes the last <hr> tag, converts it to a <h1> tag with the text
    "Endnotes" to add a header before the endnotes.
    """
    hrs = soup.find_all("hr")
    if len(hrs):
        hr = hrs.pop()
        if not hr.get("style"):
            hr.name = "h1"
            hr.string = "Endnotes"

            # create another new tag
            subsection_header = soup.new_tag("h2")
            subsection_header.string = "Select the endnote number to jump to the related section in the document."
            hr.insert_after(subsection_header)


def escape_asterisks_in_table_cells(soup):
    """
    This function mutates the soup!

    Replaces "*" with "\*" in table cells, unless the asterisk is already preceded by a backslash.

    This is to solve the problem where "required" elements in tables end up becoming <em> elements by accident.
    """

    # Match asterisks not preceded by a backslash
    pattern = re.compile(r"(?<!\\)\*")

    for cell in soup.find_all("td"):
        for content in cell.find_all(text=True):
            # Use the regex pattern to replace '*' with '\*' only if '*' is not already preceded by '\'
            escaped_content = pattern.sub(r"\\*", content)
            content.replace_with(escaped_content)
