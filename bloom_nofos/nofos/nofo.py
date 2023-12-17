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
