import re
import datetime

from .models import Nofo


def add_caption_to_table(table):
    caption = None

    for s in table.previous_siblings:
        if s.name and len(s.text):
            caption = s.extract()  # remove element from the tree
            break

    if caption:
        caption.name = "caption"  # reassign tag to <caption>
        table.insert(0, caption)


def convert_table_first_row_to_header_row(table):
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


def suggest_nofo_title(soup):
    nofo_title = "NOFO: {}".format(
        datetime.datetime.now().replace(microsecond=0).isoformat().replace("T", " ")
    )

    suggestion = _suggest_by_startswith_string(soup, "Opportunity Name:")
    return suggestion or nofo_title
