import datetime
import re

from bs4 import Tag
from markdownify import MarkdownConverter
from slugify import slugify

from .models import Nofo, Section, Subsection


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


# Create shorthand method for conversion
def md(html, **options):
    return ListInATableConverter(**options).convert(html)


def add_headings_to_nofo(nofo):
    new_ids = []
    # add counter because subheading titles can repeat, resulting in duplicate IDs
    counter = 1

    # add ids to all section headings
    for section in nofo.sections.all():
        section_id = "{}".format(slugify(section.name))

        if section.html_id:
            new_ids.append({"old_id": section.html_id, "new_id": section_id})

        section.html_id = section_id
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

    return nofo


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
            html_id=section.get("html_id"),
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
                sections.append(
                    {
                        "name": tag.text,
                        "order": section_num + 1,
                        "html_id": tag.get("id", ""),
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
                "name": heading_tag.text,
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
                # skip empty elements
                if len(tag.get_text().strip()):
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
    nofo_number = 1
    try:
        nofo_number = Nofo.objects.latest("id").id + 1
    except Nofo.DoesNotExist:
        pass

    opportunity_number_default = "NOFO #{}".format(nofo_number)
    suggestion = _suggest_by_startswith_string(soup, "Opportunity Number:")
    return suggestion or opportunity_number_default


def suggest_nofo_application_deadline(soup):
    nofo_application_deadline_default = "Monday, January 1, 2024"

    suggestion = _suggest_by_startswith_string(soup, "Application Deadline:")
    return suggestion or nofo_application_deadline_default


def suggest_nofo_theme(nofo_number):
    if "cdc-" in nofo_number.lower():
        return "landscape-cdc-blue"

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


def suggest_nofo_tagline(soup):
    suggestion = _suggest_by_startswith_string(soup, "Tagline:")
    return suggestion or ""


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


def decompose_empty_tags(soup):
    """
    This function mutates the soup!

    Removes empty HTML tags from the BeautifulSoup `soup`.

    Iterates over all body descendants and `li` tags, removing any that have no textual content.
    Intended to clean up HTML extracted from PDFs or other sources that may contain many meaningless tags.
    """
    body_descendents = soup.select("body > *")

    for tag in body_descendents:
        if not tag.get_text().strip() and tag.name not in ["br", "hr"]:
            tag.decompose()

    lis = soup.find_all("li")
    for li in lis:
        if not li.get_text().strip():
            li.decompose()
