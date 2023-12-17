import re
import datetime


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


def suggest_nofo_title(soup):
    nofo_title = "NOFO: {}".format(
        datetime.datetime.now().replace(microsecond=0).isoformat().replace("T", " ")
    )

    title_regex = re.compile("^Opportunity Name:", re.IGNORECASE)
    title_element = soup.find(string=title_regex)
    if title_element:
        temp_title = title_regex.sub("", title_element.text)
        nofo_title = temp_title.strip() if temp_title else nofo_title

    return nofo_title
