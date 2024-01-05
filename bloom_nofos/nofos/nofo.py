import re
import datetime


from markdownify import markdownify as md  # convert HTML to markdown
from slugify import slugify


from .models import Nofo, Section, Subsection


def add_headings_to_nofo(nofo):
    new_ids = []

    # add ids to all section headings
    for section in nofo.sections.all():
        section_id = slugify(section.name)

        if section.html_id:
            new_ids.append({"old_id": section.html_id, "new_id": section_id})

        section.html_id = section_id
        section.save()

        # add ids to all subsection headings
        for subsection in section.subsections.all():
            subsection_id = "{}--{}".format(section_id, slugify(subsection.name))

            if subsection.html_id:
                new_ids.append({"old_id": subsection.html_id, "new_id": subsection_id})

            subsection.html_id = subsection_id
            subsection.save()

    # replace all old ids with new ids
    for section in nofo.sections.all():
        for subsection in section.subsections.all():
            body = subsection.body
            for ids in new_ids:
                subsection.body = body.replace(ids["old_id"], ids["new_id"])

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

            name_lowercase = subsection.get("name", "Subsection X").lower()
            is_callout_box = name_lowercase.startswith(
                "key dates"
            ) or name_lowercase.startswith("the key facts")

            model_subsection = Subsection(
                name=subsection.get("name", "Subsection X"),
                order=subsection.get("order", ""),
                tag=subsection.get("tag", "h6"),
                html_id=subsection.get("html_id"),
                callout_box=is_callout_box,
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


def get_subsections_from_sections(sections):
    heading_tags = ["h2", "h3", "h4", "h5", "h6"]

    def demote_tag(tag):
        if tag.name == "h6":
            return tag

        newTags = {
            "h2": "h3",
            "h3": "h4",
            "h4": "h5",
            "h5": "h6",
        }

        return newTags[tag.name]

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
            if tag.name in heading_tags:
                # create new subsection
                subsection = {
                    "name": tag.text,
                    "order": len(section["subsections"]) + 1,
                    "tag": demote_tag(tag),
                    "html_id": tag.get("id", ""),
                    "body": [],
                }

                section["subsections"].append(subsection)

            # if not a heading, add to existing subsection
            else:
                # convert first row of header cells into th elements
                if tag.name == "table":
                    convert_table_first_row_to_header_row(tag)

                if subsection:
                    subsection["body"].append(tag)

    return sections


def _suggest_by_startswith_string(soup, startswith_string):
    suggestion = ""
    regex = re.compile("^{}".format(startswith_string), re.IGNORECASE)
    element = soup.find(string=regex)
    if element:
        suggestion = regex.sub("", element.text)

    return suggestion.strip()


def suggest_nofo_opportunity_number(soup):
    nofo_number = 1
    try:
        nofo_number = Nofo.objects.latest("id").id + 1
    except Nofo.DoesNotExist:
        pass

    opportunity_number = "NOFO #{}".format(nofo_number)
    suggestion = _suggest_by_startswith_string(soup, "Opportunity Number:")
    return suggestion or opportunity_number


def suggest_nofo_tagline(soup):
    def _find_heading_by_text(soup, text):
        # Iterate through different heading levels
        for i in range(1, 7):
            heading = soup.find(f"h{i}", string=text)
            if heading:
                return heading

        return None

    summary_heading = _find_heading_by_text(soup, text="Summary")
    if summary_heading:
        previous_element = summary_heading.previous_sibling
        previous_text = previous_element.get_text().strip()

        if previous_element.name == "p" and ":" not in previous_text:
            return previous_text

    return ""


def suggest_nofo_theme(nofo_number):
    if "cdc-" in nofo_number.lower():
        return "landscape-cdc-blue"

    if "acf-" in nofo_number.lower():
        return "portrait-acf-blue"

    return "portrait-hrsa-blue"


def suggest_nofo_title(soup):
    nofo_title = "NOFO: {}".format(
        datetime.datetime.now().replace(microsecond=0).isoformat().replace("T", " ")
    )

    suggestion = _suggest_by_startswith_string(soup, "Opportunity Name:")
    return suggestion or nofo_title
