import re
import datetime


from markdownify import markdownify as md  # convert HTML to markdown
from slugify import slugify
from bs4 import Tag


from .models import Nofo, Section, Subsection


def add_caption_to_table(table):
    caption = None

    for s in table.previous_siblings:
        if s.name and len(s.text):
            caption = s.extract()  # remove element from the tree
            break

    if caption:
        caption.name = "caption"  # reassign tag to <caption>
        table.insert(0, caption)


def add_class_to_table(table):
    def _get_table_class(num_cols):
        if num_cols <= 2:
            return "table--small"
        elif num_cols <= 4:
            return "table--medium"

        return "table--large"

    row = table.find("tr")
    cols = row.find_all("th") + row.find_all("td")
    # maybe count rows also??

    return _get_table_class(len(cols))


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


def _get_first_sentence(body, lower=False):
    if body and len(body) and isinstance(body[0], Tag):
        first_sentence = body[0].get_text().strip()
        return first_sentence.lower() if lower else first_sentence

    return ""


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

            first_sentence_lowercase = _get_first_sentence(
                subsection.get("body", []), lower=True
            )
            name_lowercase = subsection.get("name", "Subsection X").lower()
            is_callout_box = name_lowercase.startswith(
                "key dates"
            ) or first_sentence_lowercase.startswith("the key facts")
            if is_callout_box:
                # rename the callout box if "key" isn't in the title
                if "key" not in name_lowercase:
                    subsection["name"] = _get_first_sentence(subsection.get("body", []))

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


def create_nofo(title, sections, nofo_number="NOFO #999"):
    nofo = Nofo(title=title)
    nofo.number = nofo_number
    nofo.save()
    return _build_nofo(nofo, sections)


def overwrite_nofo(nofo, sections):
    nofo.sections.all().delete()
    nofo.save()
    return _build_nofo(nofo, sections)


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
