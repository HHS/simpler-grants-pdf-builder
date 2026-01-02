import datetime
import json
import logging
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import parse_qs, urlparse

import cssutils
import mammoth
import markdown
import requests
from bloom_nofos.s3.utils import (
    get_image_url_from_s3,
    remove_file_from_s3,
    upload_file_to_s3,
)
from bs4 import BeautifulSoup, NavigableString, Tag
from constance import config
from django.conf import settings
from django.db import transaction
from django.forms import ValidationError
from django.urls import reverse_lazy
from django.utils.html import escape
from slugify import slugify

from .models import Nofo, Section, Subsection
from .nofo_markdown import md
from .utils import (
    add_html_id_to_subsection,
    clean_string,
    create_subsection_html_id,
    extract_highlighted_context,
    replace_text_exclude_markdown_links,
    replace_text_include_markdown_links,
    strip_markdown_links,
    style_map_manager,
)

DEFAULT_NOFO_OPPORTUNITY_NUMBER = "NOFO #999"

# More realistic browser-like request headers (Firefox) for HTTP requests
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:131.0) Gecko/20100101 Firefox/131.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
}

###########################################################
#################### NOFO IMPORT FUNCS ####################
###########################################################


def parse_uploaded_file_as_html_string(uploaded_file):
    """
    Given an uploaded file, return raw HTML as a string.
    Raise a ValidationError if invalid or missing.
    """
    if not uploaded_file:
        raise ValidationError("Oops! No fos uploaded.")

    content_type = uploaded_file.content_type

    if content_type == "text/html":
        # Decode the HTML file
        return uploaded_file.read().decode("utf-8")

    elif (
        content_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        # Convert DOCX to HTML
        try:
            doc_to_html_result = mammoth.convert_to_html(
                uploaded_file, style_map=style_map_manager.get_style_map()
            )
        except Exception as e:
            raise ValidationError(f"Error importing .docx file: {e}")

        # If strict mode, check for warnings
        if config.WORD_IMPORT_STRICT_MODE:
            warnings = [
                m.message
                for m in doc_to_html_result.messages
                if m.type == "warning"
                and all(
                    style_ignore not in m.message
                    for style_ignore in style_map_manager.get_styles_to_ignore()
                )
            ]
            if warnings:
                warnings_str = "<ul><li>{}</li></ul>".format("</li><li>".join(warnings))
                raise ValidationError(
                    f"<p>Mammoth warnings found. These styles are not recognized by our style map:</p>{warnings_str}"
                )

        return doc_to_html_result.value

    else:
        raise ValidationError("Please import a .docx or HTML file.")


def process_nofo_html(soup, top_heading_level):
    """
    Takes a soup object, cleans it up and mutates it, and returns a modified soup object.
    """
    soup = add_body_if_no_body(soup)

    # When DEBUG is True, write out the soup to a local debug file
    if settings.DEBUG:
        # Build a path to your _temp folder in fixtures (create if needed)
        debug_dir = os.path.join(settings.BASE_DIR, "nofos", "fixtures", "_temp")
        # create dir if not exists
        os.makedirs(debug_dir, exist_ok=True)

        output_file_path = os.path.join(debug_dir, "debug_output.html")
        with open(output_file_path, "w", encoding="utf-8") as file:
            file.write(str(soup))

    instructions_tables = decompose_instructions_tables(soup)
    normalize_whitespace_img_alt_text(soup)
    join_nested_lists(soup)
    add_strongs_to_soup(soup)
    preserve_bookmark_links(soup)
    preserve_heading_links(soup)
    preserve_table_heading_links(soup)
    clean_heading_tags(soup)
    clean_table_cells(soup)
    unwrap_empty_elements(soup)
    decompose_empty_tags(soup)
    combine_consecutive_links(soup)
    remove_google_tracking_info_from_links(soup)
    add_endnotes_header_if_exists(soup, top_heading_level)
    unwrap_nested_lists(soup)
    preserve_bookmark_targets(soup)

    soup = add_em_to_de_minimis(soup)

    return soup, instructions_tables


###########################################################
#################### UTILITY FUNCS ####################
###########################################################


def replace_chars(file_content):
    replacement_chars = [
        # both of these are nonbreaking space
        ("\xa0", " "),
        ("&nbsp;", " "),
        # from (☐) U+2610 BALLOT BOX to (◻) U+25FB WHITE MEDIUM SQUARE
        ("\u2610", "\u25fb"),
        # from (¨) U+00A8 DIAERESIS to (◻) U+25FB WHITE MEDIUM SQUARE
        ("\u00a8", "\u25fb"),
        # from () U+007F DELETE to (◻) U+25FB WHITE MEDIUM SQUARE
        ("\u007f", "\u25fb"),
    ]

    for _from, _to in replacement_chars:
        file_content = file_content.replace(_from, _to)

    return file_content


def replace_links(file_content):
    # grants.gov/web links are broken and don't redirect _and_ say they are 200 🙄
    replacement_chars = [
        (
            "www.grants.gov/web/grants/search-grants.html",
            "grants.gov/search-grants",
        ),
        (
            "www.grants.gov/web/grants/forms/sf-424-family.html",
            "grants.gov/forms/forms-repository/sf-424-family",
        ),
        (
            "www.cdc.gov/grants/dictionary/index.html",
            "www.cdc.gov/grants/dictionary-of-terms/",
        ),
    ]

    for _from, _to in replacement_chars:
        file_content = file_content.replace(_from, _to)

    return file_content


###########################################################
##################### BUILD THE NOFO ######################
###########################################################


@transaction.atomic
def add_headings_to_document(
    document, SectionModel=Section, SubsectionModel=Subsection
):
    new_ids = []
    # collect sections and subsections in arrays to facilitate bulk updating
    sections_to_update = []
    subsections_to_update = []
    # add counter because subheading titles can repeat, resulting in duplicate IDs
    counter = 1

    # add ids to all section headings
    for section in document.sections.all():
        section_id = "{}".format(slugify(section.name))

        if section.html_id and len(section.html_id):
            new_ids.append({"old_id": section.html_id, "new_id": section_id})

        section.html_id = section_id

        if not section.html_id or len(section.html_id) == 0:
            raise ValueError("html_id blank for section: {}".format(section.name))

        sections_to_update.append(section)

        # add ids to all subsection headings
        for subsection in section.subsections.all():
            subsection_id = create_subsection_html_id(counter, subsection)

            if subsection.html_id:
                new_ids.append({"old_id": subsection.html_id, "new_id": subsection_id})
                if "&" in subsection.html_id:
                    new_ids.append(
                        {
                            "old_id": subsection.html_id.replace("&", "&amp;"),
                            "new_id": section_id,
                        }
                    )

            subsection.html_id = subsection_id
            subsections_to_update.append(subsection)
            counter += 1

    # Bulk update sections and subsections
    SectionModel.objects.bulk_update(sections_to_update, ["html_id"])
    SubsectionModel.objects.bulk_update(subsections_to_update, ["html_id"])
    # Reset the subsections list to avoid duplication
    subsections_to_update = []

    # Precompile regex patterns for all new_ids
    compiled_patterns = [
        {
            # Case-insensitive match to replace old_id value with new_id in hrefs
            "href_pattern": re.compile(
                r'href="#{}"'.format(re.escape(ids["old_id"])), re.IGNORECASE
            ),
            # Pattern to match old_id in hash links (like anchor links) case insensitively
            "hash_pattern": re.compile(
                r"\(#{}\)".format(re.escape(ids["old_id"])), re.IGNORECASE
            ),
            "new_id": ids["new_id"],
        }
        for ids in new_ids
    ]

    # replace all old ids with new ids
    for section in document.sections.all():
        for subsection in section.subsections.all():
            for patterns in compiled_patterns:
                # Use precompiled patterns
                subsection.body = patterns["href_pattern"].sub(
                    'href="#{}"'.format(patterns["new_id"]), subsection.body
                )
                subsection.body = patterns["hash_pattern"].sub(
                    "(#{})".format(patterns["new_id"]), subsection.body
                )

            subsections_to_update.append(subsection)

    SubsectionModel.objects.bulk_update(subsections_to_update, ["body"])


def add_page_breaks_to_headings(document):
    """
    Assign 'page-break-before' to subsections whose name matches a target
    heading and whose parent section name contains the specified substring.

    Example:
        ("eligibility", "step 1") will match a subsection named "Eligibility"
        inside a section named "Step 1: Review the Opportunity".
    """
    page_break_headings = [
        ("eligibility", "step 1"),
        ("program description", "step 1"),
        ("application checklist", "step 5"),
    ]

    for section in document.sections.all():
        section_name = (section.name or "").lower()
        for subsection in section.subsections.all():
            for match_subsection, match_section in page_break_headings:
                # subsection name must match exactly (case insensitive)
                if subsection.name and subsection.name.lower() == match_subsection:
                    # section name must be a substring
                    if match_section in section_name:
                        subsection.html_class = "page-break-before"
                        subsection.save()


def _build_document(document, sections, SectionModel, SubsectionModel):
    def _get_document_field_name(SectionModel, document):
        """
        Return the field name that should be used to attach `document` to SectionModel.
        """
        # ContentGuideSection has this method
        if hasattr(SectionModel, "get_document_field_name_for"):
            return SectionModel.get_document_field_name_for(document)

        # NOFO Section has "nofo", Compare docs have "document"
        return "nofo" if hasattr(SectionModel, "nofo") else "document"

    def _get_validation_message(validation_error, obj):
        obj_type = obj._meta.verbose_name.title()
        name_max_length = obj._meta.get_field("name").max_length

        if validation_error.message_dict.get("name", []):
            intro_message = (
                f"<strong>Found a {obj_type} name exceeding {name_max_length} characters in length.</strong> "
                "This often means a paragraph was incorrectly styled as a heading.\n\n"
            )
            error_message = f"- **Error message**: {validation_error.messages}\n"
            object_type_message = f"- **Type**: {obj_type}\n"
            object_order_message = f"- **{obj_type} order**: {obj.order}\n"
            object_name_message = f"- **{obj_type} name**: {obj.name}\n\n"
            outro_message = f"Note that there may also be other mistagged headings further down in this document."

            return (
                f"{intro_message}"
                f"{error_message}"
                f"{object_type_message}"
                f"{object_order_message}"
                f"{object_name_message}"
                f"{outro_message}"
            )

        # Generic fallback if it's not a name-related length error
        return str(validation_error)

    sections_to_create = []
    subsections_to_create = []

    for section in sections:
        # Generate a default html_id based on section name and order
        section_name = section.get("name", "Section X")
        section_order = section.get("order", "")
        default_html_id = f"{section_order}--{slugify(section_name)}"

        object_name = _get_document_field_name(SectionModel, document)
        section_obj = SectionModel(
            name=section_name,
            order=section_order,
            html_id=section.get("html_id") or default_html_id,
            has_section_page=section.get("has_section_page"),
            html_class=section.get("html_class", ""),
            **{object_name: document},
        )
        try:
            section_obj.full_clean()
        except ValidationError as e:
            raise ValidationError(_get_validation_message(e, section_obj)) from e

        sections_to_create.append(section_obj)

    # Bulk create sections and retrieve them
    created_sections = SectionModel.objects.bulk_create(sections_to_create)
    # Map created sections to their names for subsection linking
    section_mapping = {section.name: section for section in created_sections}
    for section in sections:
        model_section = section_mapping.get(section.get("name", "Section X"))
        if not model_section:
            continue

        for subsection in section.get("subsections", []):
            subsection_md_body = get_as_markdown(subsection.get("body", []))

            subsection_fields = {
                "name": subsection.get("name", ""),
                "order": subsection.get("order", ""),
                "tag": subsection.get("tag", ""),
                "html_id": subsection.get("html_id"),
                "callout_box": subsection.get(
                    "is_callout_box", subsection.get("callout_box", False)
                ),
                "html_class": subsection.get("html_class", ""),
                "body": subsection_md_body,  # body can be empty
                "section": model_section,
            }

            if hasattr(SubsectionModel, "comparison_type"):
                subsection_fields["comparison_type"] = subsection.get(
                    "comparison_type", "body"
                )

            if hasattr(SubsectionModel, "instructions"):
                instructions_md_body = get_as_markdown(
                    subsection.get("instructions", "")
                )
                subsection_fields["instructions"] = instructions_md_body
                if hasattr(SubsectionModel, "optional"):
                    is_optional = (
                        "section is only required if" in instructions_md_body.lower()
                    )
                    subsection_fields["optional"] = is_optional

            subsection_obj = SubsectionModel(**subsection_fields)

            if hasattr(SubsectionModel, "extract_variables"):
                variables = subsection_obj.extract_variables()
                # If variables are detected, edit_mode = "variables"
                if variables:
                    subsection_obj.edit_mode = "variables"
                    serializable_variables = {
                        key: var.to_dict() for key, var in variables.items()
                    }
                    subsection_obj.variables = json.dumps(serializable_variables)
                # If no variables, and subsection is optional, then edit_mode = "full"
                elif subsection_obj.optional:
                    subsection_obj.edit_mode = "full"

                # Otherwise, default edit_mode = "locked" remains

            add_html_id_to_subsection(subsection_obj)
            try:
                subsection_obj.full_clean()
            except ValidationError as e:
                raise ValidationError(_get_validation_message(e, subsection_obj)) from e

            subsections_to_create.append(subsection_obj)

    SubsectionModel.objects.bulk_create(subsections_to_create)
    return document


def get_as_markdown(html_or_string):
    md_body = ""

    # if content is a string, it's not HTML
    if isinstance(html_or_string, str):
        return html_or_string

    else:
        html_body = [str(tag).strip() for tag in html_or_string]
        if html_body:
            md_body = md("".join(html_body), escape_misc=False)
            # strip excess newlines, then add 1 trailing newline
            md_body = md_body.strip() + "\n"

    return md_body


def create_nofo(title, sections, opdiv):
    nofo = Nofo(title=title)
    nofo.number = "NOFO #999"
    nofo.opdiv = opdiv
    nofo.save()
    try:
        return _build_document(nofo, sections, Section, Subsection)
    except ValidationError as e:
        nofo.delete()
        e.nofo = nofo
        raise e


def _get_subsection_section_key(section_name, subsection):
    """
    Helper function to generate a unique key for a subsection based on section name and subsection content.
    Returns a string in format "section_name|subsection_name" or empty string if no valid key can be generated.
    """
    if hasattr(subsection, "name"):
        subsection_name = subsection.name
        body = subsection.body if hasattr(subsection, "body") else None
    else:
        subsection_name = subsection.get("name", "")
        body = subsection.get("body", "")

    if not subsection_name and body:
        # If no name, use first line of body as fallback
        if isinstance(body, list):
            body = "".join(str(item) for item in body)

        body = str(body).strip()
        if body:
            # Convert markdown to HTML for consistent comparison
            html = markdown.markdown(body)
            soup = BeautifulSoup(str(html), "html.parser")
            subsection_name = soup.get_text().split("\n")[0].strip()

    if not subsection_name:
        return ""

    return f"{section_name}|{subsection_name}"


def preserve_subsection_metadata(nofo, new_sections):
    """
    Preserves page break classes from existing subsections.
    Only preserves metadata for subsections that exist in both old and new versions.

    Args:
        nofo: The NOFO being reimported
        new_sections: The reimported sections to replace existing sections

    Returns:
        dict: Mapping of section+subsection names to their page break classes
    """
    preserved_page_breaks = {}

    # Create lookup dict for new sections
    new_section_lookup = {}
    for section in new_sections:
        section_name = section.get("name", "")
        for subsection in section.get("subsections", []):
            try:
                key = _get_subsection_section_key(section_name, subsection)
                if key:
                    new_section_lookup[key] = True
            except Exception:
                continue

    # Store page break classes from existing sections if they exist in new sections
    for section in nofo.sections.all():
        for subsection in section.subsections.all():
            try:
                name_key = _get_subsection_section_key(section.name, subsection)
                if name_key and name_key in new_section_lookup:
                    # Extract only page break classes
                    html_class = getattr(subsection, "html_class", "") or ""
                    classes = html_class.split()
                    page_break_classes = [
                        c for c in classes if c.startswith("page-break")
                    ]
                    if page_break_classes:
                        preserved_page_breaks[name_key] = " ".join(page_break_classes)
            except Exception:
                continue

    return preserved_page_breaks


def restore_subsection_metadata(nofo, preserved_page_breaks):
    """
    Restores page break classes to the new subsections after reimport.

    Args:
        nofo: The NOFO being reimported
        preserved_page_breaks: Mapping of section+subsection names to page break classes

    Returns:
        nofo: The updated NOFO object
    """
    subsections_to_update = []

    try:
        for section in nofo.sections.all():
            for subsection in section.subsections.all():
                try:
                    name_key = _get_subsection_section_key(section.name, subsection)
                    if name_key:
                        page_break_classes = preserved_page_breaks.get(name_key)

                        if page_break_classes:
                            html_class = getattr(subsection, "html_class", "") or ""
                            existing_classes = [
                                c
                                for c in html_class.split()
                                if not c.startswith("page-break")
                            ]
                            all_classes = existing_classes + page_break_classes.split()
                            subsection.html_class = " ".join(all_classes).strip()
                            subsections_to_update.append(subsection)
                except Exception:
                    continue

        # Bulk update all modified subsections
        if subsections_to_update:
            Subsection.objects.bulk_update(subsections_to_update, ["html_class"])
    except Exception:
        pass

    return nofo


def overwrite_nofo(nofo, sections):
    nofo.sections.all().delete()
    nofo = _build_document(nofo, sections, Section, Subsection)
    nofo.save()  # Save after sections are added
    return nofo


def convert_table_first_row_to_header_row(table):
    # Converts the first row of cells in the given table
    # to header cells by changing the <td> tags to <th>.
    # Assumes the first row is a header row.
    first_row = table.find("tr")
    if first_row:
        first_row_cells = first_row.find_all("td")
        for cell in first_row_cells:
            cell.name = "th"


def convert_table_with_all_ths_to_a_regular_table(table):
    """
    Converts a table with all rows in the thead and th cells to a standard table structure.

    This function checks if the table has a thead, no tbody, and more than one row in the thead.
    If these conditions are met, it creates a tbody after the thead and moves all rows except
    the first one to the tbody. Additionally, it converts all th cells in the tbody to td cells.
    """
    # if there are cells with "rowspan" not equal to 1, return early
    cells_with_rowspan = table.find_all(
        lambda tag: (tag.name == "td" or tag.name == "th") and tag.has_attr("rowspan")
    )
    for cell in cells_with_rowspan:
        if cell["rowspan"] != "1":
            return

    thead = table.find("thead")
    tbody = table.find("tbody")

    # Check if thead exists, tbody does not exist, and thead contains more than one row
    if thead and not tbody and len(thead.find_all("tr")) > 1:
        # Create a new tbody element as a string and parse it into a BeautifulSoup tag
        new_tbody = BeautifulSoup("<tbody></tbody>", "html.parser").tbody
        table.append(new_tbody)

        # Move all rows except the first one to the new tbody
        rows = thead.find_all("tr")
        for row in rows[1:]:
            # Convert th cells to td cells
            for th in row.find_all("th"):
                th.name = "td"
            new_tbody.append(row.extract())


def get_sections_from_soup(soup, top_heading_level="h1"):
    # build a structure that looks like our model
    sections = []
    section_num = -1

    for tag in soup.find_all(True):
        if tag.name == top_heading_level:
            section_num += 1

        if section_num >= 0:
            if len(sections) == section_num:
                # add an empty array at a new index
                section_name = clean_string(tag.text)

                has_section_page = not any(
                    word.lower() in section_name.lower()
                    for word in [
                        "Appendix",
                        "Appendices",
                        "Glossary",
                        "Endnotes",
                        "References",
                        "Modifications",
                    ]
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


def is_callout_box_table(table):
    """
    Determines if a given HTML table element represents a callout box.
    This function checks the following conditions:
    - The table contains exactly one row.
    - The row contains exactly one cell, which must be either all 'th' or all 'td' but not a mix.
    - There is either one 'th' or one 'td' in the entire table.

    NOTE: after this goes through the markdown parser, it has 2 rows, but for now it is just 1

    Returns:
    - bool: True if the table matches the criteria for a callout box table, False otherwise.
    """

    rows = table.find_all("tr")

    if not rows:
        return False

    cols = rows[0].find_all("th") + rows[0].find_all("td")
    ths = table.find_all("th")
    tds = table.find_all("td")

    return (
        len(cols) == 1  # 1 column
        and len(rows) == 1  # 1 row
        and (
            (len(tds) == 1 and not len(ths)) or (len(ths) == 1 and not len(tds))
        )  # 1 th OR 1 td, not both
    )


def get_subsections_from_sections(sections, top_heading_level="h1"):
    if_demote_headings = top_heading_level == "h1"
    heading_tags = ["h3", "h4", "h5", "h6"]

    # if top_heading_level is h1, then include h2s in the list
    if if_demote_headings:
        heading_tags = ["h2"] + heading_tags

    def _demote_tag(tag_name):
        newTags = {
            "h2": "h3",
            "h3": "h4",
            "h4": "h5",
            "h5": "h6",
            "h6": "h7",
            "div": "h7",
        }

        return newTags[tag_name]

    def extract_first_header(td):
        for tag_name in heading_tags:
            header_element = td.find(tag_name)
            if header_element:
                # remove from the dom
                return header_element.extract()
        return False

    def get_subsection_dict(heading_tag, order, is_callout_box, body=None):
        if heading_tag:
            tag_name = (
                _demote_tag(heading_tag.name)
                if if_demote_headings
                else heading_tag.name
            )
            if tag_name == "div" and is_h7(heading_tag):
                tag_name = "h7"

            return {
                "name": clean_string(heading_tag.text),
                "order": order,
                "tag": tag_name,
                "html_id": heading_tag.get("id", ""),
                "is_callout_box": is_callout_box,
                "body": body or [],
            }

        return {
            "name": "",
            "order": order,
            "tag": "",
            "html_id": "",
            "is_callout_box": is_callout_box,
            "body": body or [],
        }

    def get_empty_subsection(order):
        return get_subsection_dict(heading_tag=None, order=order, is_callout_box=False)

    for section in sections:
        section["subsections"] = []
        # remove 'body' key
        body = section.pop("body", None)

        body_descendents = [
            tag for tag in body if tag.parent.name in ["body", "[document]"]
        ]

        for tag in body_descendents:
            # handle callout boxes
            if tag.name == "table" and is_callout_box_table(tag):
                # Grab the first td or th
                cell = tag.find("td")
                if not cell:
                    cell = tag.find("th")

                # make the td a div so that it can live on its own
                cell.name = "div"
                callout_box_subsection = get_subsection_dict(
                    heading_tag=extract_first_header(cell),
                    order=len(section["subsections"]) + 1,
                    is_callout_box=True,
                    body=cell,
                )
                section["subsections"].append(callout_box_subsection)

            elif tag.name in heading_tags or is_h7(tag):
                # create new subsection
                heading_subsection = get_subsection_dict(
                    heading_tag=tag,
                    order=len(section["subsections"]) + 1,
                    is_callout_box=False,
                )

                section["subsections"].append(heading_subsection)

            # if not a heading or callout_box table add to existing subsection
            else:
                # convert first row of header cells into th elements
                if tag.name == "table":
                    # make sure the first row is a header row
                    convert_table_first_row_to_header_row(tag)
                    # if all rows are in a thead, move them to a tbody
                    convert_table_with_all_ths_to_a_regular_table(tag)

                if not len(section["subsections"]):
                    # create new empty subsection if there are no other ones in this section
                    section["subsections"].append(get_empty_subsection(1))

                # get latest subsection
                subsection = section["subsections"][-1]
                if subsection.get("is_callout_box", False):
                    # create new empty subsection after a callout box
                    section["subsections"].append(
                        get_empty_subsection(len(section["subsections"]) + 1)
                    )

                section["subsections"][-1]["body"].append(tag)

    return sections


###########################################################
#################### NOFO COVER IMAGE FUNCS ###############
###########################################################


def get_cover_image(nofo):
    """
    Returns a cover_image string based on specific conditions to ensure it is correctly formatted for web display or template rendering.

    This function follows a priority order for resolving cover images:

    1. **S3 Images (Highest Priority)**: First attempts to retrieve the image from S3 using get_image_url_from_s3().
       - Only valid image files are returned (ContentType must start with "image/")
       - Supports all image formats: JPEG, PNG, GIF, WebP, SVG, BMP, TIFF, etc.
       - Returns a presigned S3 URL if the image exists and is valid

    2. **External URLs**: If the image path starts with "http", it's treated as an external URL and returned as-is.

    3. **Static Asset Processing**: For local static assets, the path is normalized:
       - If starts with "/static/img/", removes the "/static/" prefix
       - If starts with "/img/", corrects it to start with "img/"
       - If contains no slashes, assumes filename only and prefixes with "img/cover-img/"
       - Otherwise returns the path unchanged

    4. **Default Fallback**: If no cover image is set, defaults to "img/cover.jpg"

    Args:
        nofo: NOFO object with cover_image attribute

    Returns:
        str: The resolved cover image path/URL

    Security:
        S3 images are validated for security - only files with image ContentType are accessible.
    """
    logger = logging.getLogger("s3")

    if nofo.cover_image:
        s3_url = get_image_url_from_s3(nofo.cover_image)
        if s3_url:
            logger.info(f"Cover image found in S3")
            return s3_url

        if nofo.cover_image.startswith("http"):
            logger.info(f"Cover image provided by external source: {nofo.cover_image}")
            return nofo.cover_image

        asset = nofo.cover_image
        if nofo.cover_image.startswith("/"):
            asset = asset.replace("/static/", "").replace("/img/", "img/")
        elif "/" not in nofo.cover_image:
            asset = "img/cover-img/{}".format(asset)

        logger.info(f"Cover image provided by static asset: {asset}")
        return asset

    return "img/cover.jpg"


def upload_cover_image_to_s3(nofo, uploaded_file, alt_text=""):
    """
    Uploads a cover image to S3 and updates the NOFO.

    Args:
        nofo: The NOFO object to update
        uploaded_file: The uploaded file from request.FILES
        alt_text: Optional alt text for the image

    Returns:
        bool: True if upload and update succeed.

    Raises:
        ValidationError: If file validation fails for the following reasons:
        - File size exceeds 5MB
        - File type is not allowed
        - File extension is not allowed
    """
    # Validate file size (5MB limit)
    max_size = 5 * 1024 * 1024  # 5MB in bytes
    if uploaded_file.size > max_size:
        raise ValidationError(
            f"File size ({uploaded_file.size / (1024*1024):.1f}MB) exceeds maximum allowed size (5MB)."
        )

    # Validate file type
    allowed_types = ["image/png", "image/jpg", "image/jpeg"]
    if uploaded_file.content_type not in allowed_types:
        raise ValidationError(
            f"Invalid file type: {uploaded_file.content_type}. Please upload a valid image file."
        )

    # Validate file extension
    allowed_extensions = [".png", ".jpg", ".jpeg"]
    file_extension = "." + uploaded_file.name.lower().split(".")[-1]
    if file_extension not in allowed_extensions:
        raise ValidationError(
            f"Invalid file extension: {file_extension}. Allowed extensions: {', '.join(allowed_extensions)}"
        )

    # Rename file to have NOFO name
    uploaded_file.name = (
        f"{nofo.number or nofo.title.replace(' ', '-')}{file_extension}".lower()
    )

    # Upload file to S3
    s3_key = upload_file_to_s3(uploaded_file, key_prefix="img/cover-img")

    # Update the NOFO with the S3 key and alt text
    nofo.cover_image = s3_key
    nofo.cover_image_alt_text = alt_text or nofo.cover_image_alt_text or ""
    nofo.save()

    return True


def remove_cover_image_from_s3(nofo):
    """
    Removes the cover image from S3 and updates the NOFO.
    """
    cover_image = nofo.cover_image

    nofo.cover_image = ""
    nofo.cover_image_alt_text = ""
    nofo.save()

    if cover_image:
        remove_file_from_s3(cover_image)


###########################################################
############ FIND THINGS IN THE NOFO DOCUMENT #############
###########################################################


def get_step_2_section(nofo):
    """
    Retrieves the section that either contains 'Step 2' in its name,
    or falls back to the section with order=2. If neither exist, returns None.
    """
    sections = nofo.sections.all()

    # Try to get section containing "Step 2" (case-insensitive)
    step_2_section = sections.filter(name__icontains="Step 2").first()

    # If no match, try to get section with order=2
    if not step_2_section:
        step_2_section = sections.filter(order=2).first()

    return step_2_section  # Returns None if nothing matches


def _get_next_subsection(section, subsection, with_tag=False):
    """
    Recursively find the next subsection in the given section based on the order.
    Optionally requires that the subsection has a non-empty tag.

    Returns:
        Subsection or None: The next subsection that meets the criteria or None if no such subsection exists.
    """
    next_subsection = (
        section.subsections.filter(order__gt=subsection.order).order_by("order").first()
    )

    if not next_subsection:
        return None

    if with_tag and not next_subsection.tag:
        return _get_next_subsection(section, next_subsection, with_tag=True)
    else:
        return next_subsection


def find_same_or_higher_heading_levels_consecutive(nofo):
    """
    This function will identify any headings that immediately follow each other (no subsection.body) and are the same level
    """
    same_or_higher_heading_levels = []
    for section in nofo.sections.all().order_by("order"):
        for subsection in section.subsections.all().order_by("order"):
            # check if no body
            if not subsection.body.strip():
                next_subsection = _get_next_subsection(section, subsection)

                if next_subsection and subsection.name and next_subsection.name:
                    # Checking tag levels
                    current_level = int(subsection.tag[1])  # Convert 'h3' to 3
                    next_level = int(next_subsection.tag[1])  # Convert 'h4' to 4

                    if current_level == next_level:
                        same_or_higher_heading_levels.append(
                            {
                                "subsection": next_subsection,
                                "name": next_subsection.name,
                                "error": "Repeated heading level: two {} headings in a row.".format(
                                    next_subsection.tag
                                ),
                            }
                        )

                    elif current_level > next_level:
                        same_or_higher_heading_levels.append(
                            {
                                "subsection": next_subsection,
                                "name": next_subsection.name,
                                "error": "Incorrectly nested heading level: {} immediately followed by a larger {}.".format(
                                    subsection.tag, next_subsection.tag
                                ),
                            }
                        )

    return same_or_higher_heading_levels


def find_incorrectly_nested_heading_levels(nofo):
    """
    This function will identify any headings that are incorrectly nested (ie, that skip 1 or more levels (eg, "h3" and then "h5", which skips "h4"))
    """
    incorrect_levels = {
        "h2": ["h4", "h5", "h6", "h7"],
        "h3": ["h5", "h6", "h7"],
        "h4": ["h6", "h7"],
        "h5": ["h7"],
        "h6": [],
        "h7": [],
    }

    incorrectly_nested_heading_levels = []
    for section in nofo.sections.all().order_by("order"):
        subsections = section.subsections.all().order_by("order")

        if subsections:
            # check that first subsection is not incorrectly nested
            first_subsection = subsections.first()
            if first_subsection and first_subsection.tag in incorrect_levels["h2"]:
                incorrectly_nested_heading_levels.append(
                    {
                        "subsection": first_subsection,
                        "name": first_subsection.name,
                        "error": "Incorrectly nested heading level: h2 ({}) followed by an {}.".format(
                            section.name, first_subsection.tag
                        ),
                    }
                )

            # check the rest of the subsections
            for subsection in subsections:
                next_subsection = _get_next_subsection(
                    section, subsection, with_tag=True
                )

                if next_subsection:
                    if (
                        subsection.name
                        and next_subsection.name
                        and next_subsection.tag in incorrect_levels[subsection.tag]
                    ):
                        incorrectly_nested_heading_levels.append(
                            {
                                "subsection": next_subsection,
                                "name": next_subsection.name,
                                "error": "Incorrectly nested heading level: {} followed by an {}.".format(
                                    subsection.tag, next_subsection.tag
                                ),
                            }
                        )

    return incorrectly_nested_heading_levels


def _update_link_statuses(all_links):
    logging.basicConfig(
        level=logging.WARNING
    )  # You can adjust the level to DEBUG, ERROR, etc.
    logger = logging.getLogger(__name__)

    def check_link_status(link):
        try:
            # First try HEAD request
            response = requests.head(
                link["url"], timeout=5, allow_redirects=True, headers=REQUEST_HEADERS
            )

            # If we get certain error codes that often work with GET, retry with GET
            if response.status_code in [403, 405, 500, 501, 502, 503]:
                try:
                    response = requests.get(
                        link["url"],
                        timeout=5,
                        allow_redirects=True,
                        headers=REQUEST_HEADERS,
                    )
                except requests.RequestException:
                    # If GET also fails, use original HEAD response
                    pass

            link["status"] = response.status_code
            if len(response.history):
                link["redirect_url"] = response.url
        except requests.RequestException as e:
            link["error"] = "Error: " + str(e)
            # print out warning to console if not running tests
            if not "test" in sys.argv:
                logger.warning(
                    "Request failed for URL: {} - {}".format(link["url"], link["error"])
                )

        return link

    with ThreadPoolExecutor(max_workers=8) as executor:
        # Submit all tasks and create a dictionary to track future to link mapping
        future_to_link = {
            executor.submit(check_link_status, link): link for link in all_links
        }

        for future in as_completed(future_to_link):
            link = future_to_link[future]
            try:
                result = future.result()
                # Update the link in all_links with the result
                link.update(result)
            except Exception as e:
                print(f"Error checking link {link['url']}: {e}")


def get_nofo_action_links(nofo):
    # Canonical action builders
    def _link_compare(nofo):
        return {
            "key": "compare",
            "label": "Compare NOFO",
            "href": reverse_lazy("compare:compare_duplicate", args=[nofo.pk]),
            "external": True,
        }

    def _link_reimport(nofo):
        return {
            "key": "reimport",
            "label": "Re-import NOFO",
            "href": reverse_lazy("nofos:nofo_import_overwrite", args=[nofo.pk]),
        }

    def _link_delete(nofo):
        return {
            "key": "delete",
            "label": "Delete NOFO",
            "href": reverse_lazy("nofos:nofo_archive", args=[nofo.pk]),
            "danger": True,
        }

    def _link_find_replace(nofo):
        return {
            "key": "find-replace",
            "label": "Find & Replace",
            "href": reverse_lazy("nofos:nofo_find_replace", args=[nofo.pk]),
        }

    # Status → allowed actions
    _STATUS_ACTIONS = {
        "draft": ("find_replace", "compare", "reimport", "delete"),
        "active": ("find_replace", "compare", "reimport"),
        "ready-for-qa": ("find_replace", "compare", "reimport"),
        "review": (
            "find_replace",
            "compare",
        ),
        "doge": (
            "find_replace",
            "compare",
        ),  # Deputy Secretary review
        "published": (),  # no actions ("modifications" is not part of this)
        "paused": (
            "find_replace",
            "compare",
        ),
        "cancelled": (),
    }

    status = (nofo.status or "").lower()
    actions = _STATUS_ACTIONS.get(status, ())

    # Assemble in order
    link_builders = {
        "find_replace": lambda: _link_find_replace(nofo),
        "compare": lambda: _link_compare(nofo),
        "reimport": lambda: _link_reimport(nofo),
        "delete": lambda: _link_delete(nofo),
    }

    links = []
    for key in actions:
        build = link_builders.get(key)
        if build:
            links.append(build())

    return links


def find_external_link(url):
    """
    Fetches the content of a given URL and returns relevant information, including the HTML title, status code, and escaped HTML content.

    Parameters:
        url (str): The URL to be fetched.

    Returns:
        dict: A dictionary containing the following keys:
            - 'url' (str): The original URL that was fetched.
            - 'status_code' (int): The HTTP status code returned by the server.
            - 'title' (str): The title of the HTML page, or 'No Title Found' if no title is present.
            - 'content' (str): The escaped HTML content of the page.
            or
            - 'url' (str): The original URL that was fetched.
            - 'error' (str): If an exception occurs, the error message is returned instead of other fields.

    This function sends a GET request to the provided URL, extracts and returns key metadata such as the page title,
    and HTML content. If the request fails, it returns an error message with details.
    The HTML content is escaped to prevent XSS vulnerabilities when used in an unsafe context.
    """

    def _extract_title(html):
        """
        Extracts the <title> from the HTML content.
        """
        soup = BeautifulSoup(html, "html.parser")
        title_tag = soup.find("title")
        return title_tag.string if title_tag else "No Title Found"

    logging.basicConfig(
        level=logging.WARNING
    )  # You can adjust the level to DEBUG, ERROR, etc.
    logger = logging.getLogger(__name__)

    try:
        sess = requests.session()
        response = sess.get(url, headers=REQUEST_HEADERS)
        response.raise_for_status()
        # Safely escape the content to prevent XSS
        content = escape(response.text)
        title = _extract_title(response.text)
        return {
            "url": url,
            "status_code": response.status_code,
            "title": title,
            "content": content,
        }

    except requests.RequestException as e:
        error_string = "Error: " + str(e)
        # print out warning to console if not running tests
        if not "test" in sys.argv:
            logger.warning("Request failed for URL: {} - {}".format(url, error_string))

        return {"url": url, "error": error_string}


def find_external_links(nofo, with_status=False):
    """
    Returns a list of external hyperlink references found within the markdown content of a NOFO.

    This function processes the markdown content of each subsection, converts it to HTML using BeautifulSoup and markdown libraries, and searches for all 'a' tags (hyperlinks). It then filters these links to include only those that are external (not part of the 'nofo.rodeo' domain).

    Parameters:
        nofo (Nofo instance): The NOFO object whose sections and subsections are to be scanned for external links.
        with_status (bool): A flag indicating whether to update the status of each link (e.g., check if the link is live, if it redirects, etc.) by calling the `_update_link_statuses` function.

    Returns:
        list: A list of dictionaries. Each dictionary represents an external link and contains the following keys:
            - 'url' (str): The URL of the link.
            - 'domain' (str): The hostname extracted from the URL.
            - 'section' (Section instance): The section object where the link was found.
            - 'subsection' (Subsection instance): The subsection object where the link was found.
            - 'status' (str): A placeholder for the status of the link; it remains empty unless updated externally.
            - 'error' (str): A placeholder for any error associated with the link; it remains empty unless updated externally.
            - 'redirect_url' (str): A placeholder for the URL where the link redirects; it remains empty unless updated externally.
    """
    all_links = []

    sections = nofo.sections.all().order_by("order")
    for section in sections:
        subsections = section.subsections.all().order_by("order")

        for subsection in subsections:
            soup = BeautifulSoup(
                markdown.markdown(subsection.body, extensions=["extra"]),
                "html.parser",
            )
            links = soup.find_all("a")
            for link in links:
                url = link.get("href", "#")

                if url.startswith("http"):
                    if not "nofo.rodeo" in url:
                        all_links.append(
                            {
                                "url": url,
                                "link_text": link.get_text(),
                                "domain": urlparse(url).hostname,
                                "section": section,
                                "subsection": subsection,
                                "status": "",
                                "error": "",
                                "redirect_url": "",
                            }
                        )

    if with_status:
        _update_link_statuses(all_links)

    return all_links


def find_broken_links(nofo):
    """
    Identifies and returns a list of broken links within a given Nofo.

    A broken link is defined as an anchor (`<a>`) element whose `href` attribute value starts with "#h.", "#id.", "/", "https://docs.google.com", "#_heading", or "_bookmark".
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

    # Define a function that checks if an 'href' attribute starts with any of these
    def _href_starts_with_h(tag):
        return tag.name == "a" and (
            tag.get("href", "").startswith("/")
            or tag.get("href", "").startswith("#")
            or tag.get("href", "").startswith("https://docs.google.com")
            or tag.get("href", "") == "about:blank"
            or tag.get("href", "").startswith("bookmark")
            or tag.get("href", "").startswith("file://")
        )

    broken_links = []
    all_ids = _get_all_id_attrs_for_nofo(nofo)

    for section in nofo.sections.all().order_by("order"):
        for subsection in section.subsections.all().order_by("order"):

            soup = BeautifulSoup(
                markdown.markdown(subsection.body, extensions=["extra"]), "html.parser"
            )

            all_links = soup.find_all("a")

            for link in all_links:
                if link.attrs.get("href") in all_ids:
                    # skip all '#' ids that exist (if not, they are caught in the next step)
                    pass
                elif _href_starts_with_h(link):
                    broken_links.append(
                        {
                            "section": section,
                            "subsection": subsection,
                            "link_text": link.get_text(),
                            "link_href": link["href"],
                        }
                    )

    return broken_links


def get_side_nav_links(nofo):
    """
    Generate a list of dictionaries for the side navigation menu in the NOFO editor.

    Args:
        nofo: The NOFO instance whose sections will be included in the navigation.

    Returns:
        list: A list of dictionaries, each representing a navigation link. Each dictionary
              contains:
                - 'id': The HTML id of the section (used as an anchor in the page).
                - 'name': The display name of the section.

    Example:
        [
            {'id': 'summary-box-key-information', 'name': 'NOFO Summary'},
            {'id': 'section-1-html-id', 'name': 'Section 1 Name'},
            ...
        ]
    """
    if nofo.sections.count() == 0:
        return []

    side_nav_links = [{"id": "summary-box-key-information", "name": "NOFO Summary"}]

    for section in nofo.sections.all().order_by("order"):
        side_nav_links.append({"id": section.html_id, "name": section.name})

    return side_nav_links


###########################################################
#################### SUGGEST VAR FUNCS ####################
###########################################################


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
    nofo_application_deadline_default = "[WEEKDAY, MONTH DAY, YEAR]"

    suggestion = _suggest_by_startswith_string(soup, "Application Deadline:")
    return suggestion or nofo_application_deadline_default


def suggest_nofo_cover(nofo_theme):
    if any(prefix in nofo_theme.lower() for prefix in ["acf-", "acl-", "hrsa-"]):
        return "nofo--cover-page--text"

    return "nofo--cover-page--medium"


def suggest_nofo_theme(nofo_number):
    if "cdc-" in nofo_number.lower():
        return "portrait-cdc-blue"

    if "acf-" in nofo_number.lower():
        return "portrait-acf-white"

    if "acl-" in nofo_number.lower():
        return "portrait-acl-white"

    if "cms-" in nofo_number.lower():
        return "portrait-cms-white"

    if "ihs-" in nofo_number.lower():
        return "portrait-ihs-white"

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


def suggest_nofo_cover_image(nofo):
    cover_img = "img/cover-img/{}.jpg".format(nofo.number.lower())
    if os.path.exists(os.path.join(settings.STATIC_ROOT, cover_img)):
        return cover_img

    if "pepfar" in nofo.title.lower():
        return "img/cover-img/cdc-pepfar.jpg"

    return ""


def suggest_all_nofo_fields(nofo, soup):
    first_time_import = (
        not nofo.number or nofo.number == DEFAULT_NOFO_OPPORTUNITY_NUMBER
    )

    nofo_number = suggest_nofo_opportunity_number(soup)  # guess the NOFO number
    nofo.number = nofo_number
    nofo.application_deadline = suggest_nofo_application_deadline(
        soup
    )  # guess the NOFO application deadline
    nofo.opdiv = suggest_nofo_opdiv(soup)  # guess the NOFO OpDiv
    nofo.agency = suggest_nofo_agency(soup)  # guess the NOFO Agency
    nofo.subagency = suggest_nofo_subagency(soup)  # guess the NOFO Subagency
    nofo.subagency2 = suggest_nofo_subagency2(soup)  # guess NOFO Subagency 2
    nofo.tagline = suggest_nofo_tagline(soup)  # guess the NOFO tagline
    nofo.author = suggest_nofo_author(soup)  # guess the NOFO author
    nofo.subject = suggest_nofo_subject(soup)  # guess the NOFO subject
    nofo.keywords = suggest_nofo_keywords(soup)  # guess the NOFO keywords

    if not nofo.cover_image:
        nofo.cover_image = suggest_nofo_cover_image(nofo)  # guess NOFO cover image

    nofo_title = suggest_nofo_title(soup)  # guess the NOFO title
    # reset title only if there is a title and it's not the default title, or current nofo.title is empty
    if nofo_title:
        if not nofo.title or not nofo_title.startswith("NOFO: "):
            nofo.title = nofo_title

    # do not reset these during import
    if first_time_import:
        nofo.theme = suggest_nofo_theme(nofo.number)  # guess the NOFO theme
    if first_time_import:
        nofo.cover = suggest_nofo_cover(nofo.theme)  # guess the NOFO cover


###########################################################
#################### MUTATE HTML FUNCS ####################
###########################################################


def add_body_if_no_body(soup):
    """
    This function mutates the soup!

    Checks for a body tag. If there is no body, it wraps all the html in a body tag.
    """
    if not soup.body:
        soup = BeautifulSoup("<body>{}</body>".format(str(soup)), "html.parser")

    return soup


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
        if tag.get("class"):
            for classname in tag.get("class"):
                if classname.startswith("lst-"):
                    return classname
        return None

    def _get_previous_element(tag):
        for ps in tag.previous_siblings:
            if isinstance(ps, Tag):
                return ps
        return None

    def _join_lists(lst, previous_lst):
        if _get_list_classname(lst) == _get_list_classname(previous_lst):
            # if classes match, join these lists
            previous_lst.extend(lst.find_all("li"))
            lst.decompose()
            return

        # okay: classes do not match
        # get the last li in the previous list
        last_tag_in_previous_list = previous_lst.find_all("li", recursive=False)[-1]

        # see if there is a ul/ol in there
        nested_lst = last_tag_in_previous_list.find(["ul", "ol"])
        if nested_lst:
            return _join_lists(lst, nested_lst)

        # if there is not, append to the last li
        last_tag_in_previous_list.append(lst)
        return

    for lst in soup.find_all(["ul", "ol"]):
        if lst.get("class"):
            # check previous sibling
            previous_element = _get_previous_element(lst)
            if previous_element and previous_element.name in ["ul", "ol"]:
                _join_lists(lst, previous_element)

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


def _get_all_id_attrs_for_nofo(nofo):
    """
    Extracts all unique HTML 'id' attributes from a given Nofo.
    This includes 'id' attributes defined in the 'html_id' field of sections and subsections,
    as well as any 'id' attributes found within the HTML content of the subsection.body.
    """
    # Initialize a set to collect all unique ids
    all_ids = set()

    for section in nofo.sections.all():
        all_ids.add(section.html_id)

        for subsection in section.subsections.all():
            if subsection.html_id:
                all_ids.add(subsection.html_id)

            # Use BeautifulSoup to parse the HTML body and find all ids
            if subsection.body:
                soup = BeautifulSoup(
                    markdown.markdown(subsection.body, extensions=["extra"]),
                    "html.parser",
                )
                for element in soup.find_all(id=True):
                    all_ids.add(element["id"])

    return {"#" + item for item in all_ids}


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

    def _append_next_sibling(link):
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
            and link.get("href") == next_sibling.get("href")
        ):
            # If there's whitespace, add a space before merging texts
            separator = " " if whitespace_between else ""
            link.string = link.get_text() + separator + next_sibling.get_text()
            # Remove the next link
            next_sibling.extract()
            return True

        return False

    # Now, merge consecutive <a> tags with the same href
    # Keep looping on the link so that multiple consecutive links will all be joined together
    links = soup.find_all("a")
    for link in links:
        while _append_next_sibling(link):
            pass

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

    Iterates over all body descendants, `p`, and `li` tags, removing any that have no textual content.
    Intended to clean up HTML extracted from PDFs or other sources that may contain many meaningless tags.

    It will, however, keep in place: brs, hrs, and tags that contain imgs.
    """
    body_descendents = soup.select("body > *")

    for tag in body_descendents:
        if not tag.get_text().strip() and tag.name not in ["br", "hr"]:
            # images have no content but should not be stripped out
            if len(tag.find_all("img")) == 0:
                tag.decompose()

    def _decompose_empty_elements(element):
        if not element.get_text().strip():
            children = element.find_all(recursive=False)  # Get children
            if not any(child.name == "img" for child in children):
                element.decompose()

    # remove all list items and paragraphs that are empty
    elements = soup.find_all(["li", "p"])
    for element in elements:
        _decompose_empty_elements(element)


def unwrap_empty_elements(soup):
    """
    This function mutates the soup!

    Unwraps empty span, strong, sup, a, and em tags from the BeautifulSoup `soup`.
    """
    elements = soup.find_all(
        ["em", "span", "strong", "sup"], string=lambda t: not t or not t.strip()
    )
    for el in elements:
        el.unwrap()


def clean_table_cells(soup):
    """
    This function mutates the soup!

    Cleans the content of all table cells in a Nofo.

    This function performs two main operations on each table cell (`<td>` and `<th>` elements) within a given BeautifulSoup object:
    1. Unwraps all `<span>` elements, effectively removing the `<span>` tags but keeping their contents intact in the cell.

    These operations are applied to ensure that the text within table cells is normalized for further processing or display, without unnecessary `<span>` tags or non-standard whitespace characters.

    Parameters:
    soup (BeautifulSoup): A BeautifulSoup object containing the HTML content to be cleaned. This object is modified in place.

    Returns:
    None: The function modifies the BeautifulSoup object in place and does not return a value.

    Example:
    >>> from bs4 import BeautifulSoup
    >>> html_content = "<table><tr><td><span>Example</span> Text and <a href='https://groundhog-day.com'>a link</a></td></tr></table>"
    >>> soup = BeautifulSoup(html_content, 'html.parser')
    >>> clean_table_cells(soup)
    >>> str(soup)
    '<table><tr><td>Example Text and <a href='https://groundhog-day.com'>a link</a></td></tr></table>'
    """
    for cell in soup.find_all(["td", "th"]):
        # strip spans but keep their content
        for span in cell.find_all("span"):
            span.unwrap()


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
                if ";base64" not in img.get("src")[:40]:
                    img_src = img["src"]
                    img_filename = img_src.split("/").pop()  # pop the filepath
                    img["src"] = "/static/img/inline/{}/{}".format(
                        nofo_number.lower(), img_filename
                    )


def add_endnotes_header_if_exists(soup, top_heading_level="h1"):
    """
    This function mutates the soup!

    If no "Endnotes" header exists, look for a list of endnotes and add a header if found.

    If this is the Google Docs HTML export, we look for a final <hr> without a style tag.
    Adds a header for endnotes if final <hr> tag has no style attribute.

    Checks if the last <hr> tags in the soup has no style attribute.
    If so, takes the last <hr> tag, converts it to a <h1> tag with the text
    "Endnotes" to add a header before the endnotes.

    If this is a docx export, we look for a final <ol> where the first <li> has an id that
    starts with "footnote" or "endnote".

    In this case, we create a new h1 with the text "Endnotes" and
    insert it before the ol.
    """

    def _match_endnotes(tag):
        return (tag.name == "h1" or tag.name == "h2") and tag.text == "Endnotes"

    def _find_google_doc_html_endnotes(soup):
        hrs = soup.find_all("hr")
        if len(hrs):
            last_hr = hrs.pop()
            if not last_hr.get("style"):
                return last_hr

        return False

    def _find_docx_html_endnotes(soup):
        # Find the endnotes in a docx export
        ols = soup.find_all("ol")
        if ols:
            last_ol = ols.pop()
            # Check if the first li in the ol starts with the id "footnote" or "endnote"
            first_li = last_ol.find("li")
            if first_li and first_li.get("id", "").startswith(("footnote", "endnote")):
                return last_ol

        return False

    if soup.find(_match_endnotes):
        return

    # Find the endnotes in Google Docs HTML export
    last_hr = _find_google_doc_html_endnotes(soup)
    if last_hr:
        # Repurpose the hr element as an h1 element
        last_hr.name = top_heading_level
        last_hr.string = "Endnotes"

    else:
        # Else, find the endnotes in Google Docs HTML export
        last_ol = _find_docx_html_endnotes(soup)
        if last_ol:
            # Create the h1 element
            heading_tag = soup.new_tag(top_heading_level)
            heading_tag.string = "Endnotes"

            # Insert the h1 element before the ol
            last_ol.insert_before(heading_tag)


def _get_font_size_from_cssText(cssText):
    """
    Extracts the font-size value from a CSS text block.

    This function parses a CSS text block and extracts the font size specified in it.
    If the font size is specified in points (pt), it returns the size as an integer.
    Otherwise, it returns the font size as a string.

    Note that the font-size rule definitely exists when the block is passed in.
    """
    font_size = [rule for rule in cssText.split("\n") if "font-size" in rule]

    font_size = font_size.pop().split(":")[1].strip(" ;")
    if "pt" in font_size:
        try:
            return int(font_size.strip("pt"))
        except ValueError:
            pass

    return font_size


def _get_classnames_for_font_weight_bold(styles_as_text):
    """
    Extracts class names from CSS text that have a font-weight: 700
    and filters out classes with a font size of 18pt or larger.

    Returns a set of class names that match the criteria
    (bold font weight and optionally font size less than 18pt).
    """
    cssutils.log.setLevel(logging.CRITICAL)
    stylesheet = cssutils.parseString(styles_as_text)

    include_rule = "font-weight: 700"
    matching_classes = set()

    for rule in stylesheet:
        if isinstance(rule, cssutils.css.CSSStyleRule):
            for selector in rule.selectorList:
                if selector.selectorText.startswith(
                    "."
                ):  # Make sure it's a class selector
                    class_name = selector.selectorText[1:]
                    if include_rule in rule.style.cssText:
                        font_size = ""

                        if "font-size" in rule.style.cssText:
                            font_size = _get_font_size_from_cssText(rule.style.cssText)

                        # exclude classes with font-size >= 18pt
                        if font_size and isinstance(font_size, int) and font_size >= 18:
                            pass
                        else:
                            matching_classes.add(class_name)

    return matching_classes


def add_strongs_to_soup(soup):
    """
    This function mutates the soup!

    Wraps elements with a specified class in a <strong> tag, excluding elements
    in the first row of a table.

    This function searches for elements with class names that indicate bold font
    weight (as determined by the _get_classnames_for_font_weight_bold function) and
    wraps them in a <strong> tag to preserve them once we convert the HTML to markdown.
    Elements in the first row of a table (inside a <td> within the first <tr>) are excluded
    from this because table headings are already bolded.
    """
    style_tag = soup.find("style")
    if style_tag:
        matching_classes = _get_classnames_for_font_weight_bold(style_tag.get_text())

        for class_name in matching_classes:
            for element in soup.find_all(class_=class_name):
                # Check if the element is inside a <td> in the first row of a table
                parent_tr = element.find_parent("tr")
                if parent_tr and parent_tr.find_previous_sibling() is None:
                    continue
                element.wrap(soup.new_tag("strong"))


def add_em_to_de_minimis(soup):
    def _replace_de_minimis(match):
        # Check if the matched string is already inside an <em> tag
        if match.group(0).startswith("<em>") and match.group(0).endswith("</em>"):
            return match.group(0)  # return the match unchanged
        return f"<em>{match.group(0)}</em>"  # Wrap in <em> tags if not already wrapped

    # Correct the regex to prevent changing already wrapped instances
    new_html = re.sub(
        r"(?<!<em>)de minimis(?!<\/em>)",
        _replace_de_minimis,
        str(soup),
        flags=re.IGNORECASE,
    )

    # Return soup object
    return BeautifulSoup(new_html, "html.parser")


def clean_heading_tags(soup):
    """
    This function mutates the soup!

    Finds all headings, it will:
    - Unwrap span tags in the heading
    - Collapse multiple spaces into one
    - Trim leading and trailing spaces
    """
    # Find all headings (h1, h2, ..., h6)
    headings = soup.find_all(re.compile("^h[1-6]$"))

    for heading in headings:
        # Unwrap spans
        for span in heading.find_all("span"):
            span.unwrap()

        # Get the text content of the heading
        text = heading.get_text()

        # Collapse multiple spaces into one
        text = re.sub(r"\s+", " ", text)

        # Trim whitespace from the front and back
        text = text.strip()

        # Replace the original heading text with the cleaned text
        heading.string = text


def _change_existing_anchor_links_to_new_id(soup, element, new_id):
    """
    Update all anchor links in the provided BeautifulSoup object that point to
    the original ID of the specified element to point to new_id.

    Example:
        Given an element <div id="section1"> and a new_id "section2", all
        links in the document with href="#section1" will be changed to
        href="#section2".
    """
    old_id = element.attrs.get("id")
    if old_id:
        links_to_old_id = soup.find_all("a", href="#{}".format(old_id))
        for old_link in links_to_old_id:
            old_link["href"] = "#{}".format(new_id)


def preserve_bookmark_links(soup):
    """
    This function mutates the soup!

    Preserves bookmark links by transferring the 'name' attribute from empty <a> tags to be the ID of the following paragraph elements.

    This function searches for all <a> tags with an ID that starts with "#bookmark". If such an <a> tag is empty (i.e., contains no text),
    the function transfers the 'id' attribute to the 'id' attribute on the next element if that element is a paragraph.

    Empty <a> tags are removed in a later step.
    """
    # Find all <a> tags with an id starting with "#bookmark"
    bookmark_id_anchors = soup.find_all(
        "a", href=lambda x: x and x.startswith("#bookmark")
    )

    bookmark_ids = set([link["href"][1:] for link in bookmark_id_anchors])

    for bookmark_id in bookmark_ids:
        # Find the corresponding anchor tag with the same name, and check if it's empty
        a = soup.find("a", id=bookmark_id)
        if a and not a.text.strip():
            next_elem = a.find_next()
            if next_elem and next_elem.name == "p" and a.attrs.get("id"):
                _change_existing_anchor_links_to_new_id(soup, next_elem, a["id"])
                # Transfer the id to the next paragraph element, replacing any existing id
                next_elem["id"] = a["id"]

                # Find the closest preceding heading
                prev_elem = a.find_previous()
                while prev_elem:
                    if prev_elem.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                        # we want the heading level to be 1 more than the last heading
                        level = int(prev_elem.name[1]) + 1
                        next_elem["class"] = next_elem.get("class", []) + [
                            "bookmark-level-{}".format(level)
                        ]
                        break
                    prev_elem = prev_elem.find_previous()

                # If no preceding heading is found, assign a generic class
                if not prev_elem:
                    next_elem["class"] = next_elem.get("class", []) + ["bookmark"]

                a.decompose()  # Remove the empty <a> tag
        if not a:
            broken_link = next(
                (
                    link
                    for link in bookmark_id_anchors
                    if bookmark_id in link.get("href")
                )
            )

            # add two underscores so that we can identify this link later as a dead link
            broken_link["href"] = "#__{}".format(bookmark_id)


def preserve_bookmark_targets(soup):
    """
    This function mutates the soup!

    Adjusts empty bookmark links in an HTML document to preserve their target IDs while cleaning up the document structure.

    This function processes all empty <a> tags in the provided BeautifulSoup object that meet the following criteria:
    - Have an 'id' attribute (which does not start with an underscore)
    - Do not contain an 'href' or any text content

    For each matching <a> tag:
    1. The function prepends "nb_bookmark_" to the <a> tag's 'id'.
    2. It searches for any other <a> tags in the document with an 'href' attribute pointing to the original 'id' and updates their 'href' to the new prefixed 'id'.
    3. If the parent of the empty <a> tag does not have an 'id', the new prefixed 'id' is copied to the parent element.
    4. The original empty <a> tag is then removed from the document.
    """
    empty_links = [
        a for a in soup.find_all("a", id=True, href=False) if not a.text.strip()
    ]
    for link in empty_links:
        if not link.get("id", "").startswith("_"):
            original_id = link.get("id", "")
            new_id = "nb_bookmark_{}".format(original_id)

            link["id"] = new_id  # Update the id of the empty <a> tag

            matching_links = soup.find_all("a", href="#{}".format(original_id))
            for matching_link in matching_links:
                # replace hrefs of existing links to new id
                matching_link["href"] = "#{}".format(new_id)

            if link.parent and not link.parent.get("id", None):
                # Copy the id from the <a> tag to the parent
                link.parent["id"] = new_id
                # Remove the <a> tag from the document
                link.decompose()


def is_h7(tag):
    """
    Checks if a tag is an H7 heading (div with heading role and aria-level).
    """
    return (
        tag.name == "div"
        and tag.get("role") == "heading"
        and tag.has_attr("aria-level")
    )


def preserve_heading_links(soup):
    """
    This function mutates the soup!

    Preserves heading links by transferring IDs from empty <a> tags to their parent heading elements.
    Also preserves heading links by transferring IDs from empty <a> tags that immediately precede headings
    (either as standalone elements or as part of a <p> tag containing only <a> elements) to those heading elements.

    This function processes the following cases:
    1. Empty <a> tags that are direct children of heading tags.
    2. Empty <a> tags that are direct siblings preceding heading tags.
    3. Empty <a> tags nested within a <p> tag that directly precedes a heading tag.
       - The <p> tag must contain only valid <a> tags (i.e., tags with an "id" attribute and no text).

    If such an <a> tag is empty (i.e., contains no text), the function transfers the ID from the <a> tag to the heading
    element and removes the empty <a> tag from the soup.

    This ensures that headings retain their linkable IDs, even after empty <a> tags are removed during HTML cleanup.
    """

    def _is_valid_anchor(element):
        """
        Checks if an element is a valid anchor (<a> tag).
        A valid anchor must:
        - Be an <a> tag.
        - Have an 'id' attribute.
        - Contain no text or other content.
        """
        return (
            element.name == "a"
            and element.attrs.get("id")
            and not element.get_text(strip=True)
        )

    def _is_valid_anchor_or_paragraph_containing_anchors(element):
        """
        Checks if an element is a valid anchor or paragraph.
        - Valid anchor: <a> tag with no text and an ID.
        - Valid paragraph: <p> tag containing only <a> tags with IDs, and no text.
        """
        if _is_valid_anchor(element):
            return True
        if element.name == "p":
            # Ensure the <p> tag has no text content and all children are valid <a> tags
            if not element.get_text(strip=True):
                children = element.find_all(recursive=False)  # Direct children only
                return all(_is_valid_anchor(child) for child in children)
        return False

    def _transfer_id_and_decompose(heading, anchor):
        if heading and anchor.attrs.get("id"):
            _change_existing_anchor_links_to_new_id(soup, heading, anchor["id"])
            # Transfer the id to the parent element, replacing any existing id
            heading["id"] = anchor["id"]
            anchor.decompose()  # Remove the empty <a> tag

    # Get all headings (h1-h6 and h7s)
    headings = []

    # Find regular heading tags
    for tag in ["h1", "h2", "h3", "h4", "h5", "h6"]:
        headings.extend(soup.find_all(tag))

    # Find H7 divs
    headings.extend(soup.find_all(is_h7))

    # Process all headings
    for heading in headings:
        # Store found empty anchors
        heading_id_anchors = []
        preceding_id_anchors = []

        # Find empty <a> tags immediately preceding the heading
        previous_sibling = heading.find_previous_sibling()

        # Traverse back through preceding siblings
        while previous_sibling and _is_valid_anchor_or_paragraph_containing_anchors(
            previous_sibling
        ):
            if previous_sibling.name == "a":
                # Append single valid <a> tag
                preceding_id_anchors.append(previous_sibling)
            elif previous_sibling.name == "p":
                # For valid <p>, add all <a> children
                preceding_id_anchors.extend(
                    previous_sibling.find_all("a", recursive=False)
                )
            previous_sibling = previous_sibling.find_previous_sibling()

        # Process all preceding empty <a> tags
        for preceding_anchor in reversed(preceding_id_anchors):
            if not preceding_anchor.text.strip():
                _transfer_id_and_decompose(heading=heading, anchor=preceding_anchor)

        # Find direct child anchor tags that are empty
        for a in heading.find_all("a", recursive=False):
            if a.get_text(strip=True) == "" and not a.contents:
                heading_id_anchors.append(a)

        # Process all internal empty <a> tags
        for heading_anchor in heading_id_anchors:
            # Check if the <a> tag is empty
            if not heading_anchor.text.strip():
                _transfer_id_and_decompose(heading=heading, anchor=heading_anchor)


def preserve_table_heading_links(soup):
    """
    This function mutates the soup!

    Preserves table heading ids by transferring IDs from empty <a> tags to their parent paragraph elements.
    A "table heading" in this function is a paragraph that immediately precedes a table.

    This function searches for all <p> tags that immediately precede a table,
    then finds all empty <a> tags (i.e., contains no text).
    Once found, it transfers the ID to the parent <p> element and removes the empty <a> tag.

    Empty <a> tags are removed in a later step, so these were getting screened out and then we were losing the link to the heading.
    """
    table_id_anchors = []

    # Iterate through all tables
    tables = soup.find_all("table")
    for table in tables:
        # Get the previous sibling if a paragraph (or None)
        paragraph = table.find_previous_sibling("p")
        if paragraph:
            # Find all empty <a> tags within the paragraph
            empty_links = [a for a in paragraph.find_all("a") if not a.text.strip()]
            for a in empty_links:
                table_id_anchors.append(a)

    for a in table_id_anchors:
        # Check if the <a> tag is empty
        if not a.text.strip():
            parent = a.parent
            if parent and a.attrs.get("id"):
                a_id = "table-heading--{}".format(a["id"])
                _change_existing_anchor_links_to_new_id(soup, parent, a_id)
                _change_existing_anchor_links_to_new_id(soup, a, a_id)
                # Transfer the id to the parent element, replacing any existing id
                parent["id"] = a_id
                a.decompose()  # Remove the empty <a> tag


def unwrap_nested_lists(soup):
    def _has_only_nested_ul(li):
        # Check if li has exactly one child which is a ul
        children = li.find_all(recursive=False)
        if len(children) == 1 and children[0].name == "ul":
            # Ensure there is no direct text in the li
            for content in li.contents:
                if isinstance(content, NavigableString) and content.strip():
                    return False
            return True
        return False

    for li in soup.find_all("li"):
        if _has_only_nested_ul(li):
            li.unwrap()

    for ul in soup.select("ul > ul"):
        ul.unwrap()


def decompose_instructions_tables(soup):
    """
    This function mutates the soup!
    Remove tables from a BeautifulSoup object that contain specific instructional text,
    and return them as a list of extracted HTML snippets for later use.

    This function iterates through all the <table> elements in the BeautifulSoup object.
    If a table contains text that starts with "Instructions for NOFO writers:",
    it is removed from the soup object.
    """
    instructions_tables = []
    tables = soup.find_all("table")
    instructions_tables = []
    for table in tables:
        cells = table.find_all("td")
        if len(cells) == 1:
            table_text_lowercase = table.get_text().lower()
            if (
                table_text_lowercase.startswith("instructions for nofo writers")
                or table_text_lowercase.startswith("instructions for new nofo team")
                or re.match(r".+-specific instructions", table_text_lowercase)
            ):
                instructions_tables.append(table.extract())

    return instructions_tables


def add_instructions_to_subsections(sections, instructions_tables):
    """
    This function adds instructions derived from extracted instructions tables to their
    corresponding subsections. Instructions are matched to subsections based on matching names.
    Instructions are considered to belong to the first subsection with a name, whose name
    appears in the instruction table text. Instructions can only belong to a single subsection, and
    every subsection can only have one instruction.

    Instrucions are parsed from one-cell tables with the outer table elements stripped away.

    NOTE: Only used in ComposerImportView.

    Args:
        sections (list): A list of section dictionaries, each containing a list of subsections.
        instructions_tables (list): A list of BeautifulSoup table elements containing instructions.

    Returns:
        None: The function modifies the sections in place.
    """

    def _extract_instructions_title(instructions_body):
        """
        Extract and return the instructions title (text after the first colon) or None.
        """
        logger = logging.getLogger(__name__)

        try:
            node = instructions_body.find(
                string=re.compile(
                    r"^(instructions for nofo writers|instructions for new nofo team)",
                    re.IGNORECASE,
                )
            )

            if not node:
                raise ValueError("No instructions title line found")

            title_text = str(node).strip()

            if ":" not in title_text:
                raise ValueError("Instructions title is missing a colon")

            # Split on first colon
            _, title = title_text.split(":", 1)
            title = title.strip()

            if not title:
                raise ValueError("Instructions title is empty after colon")

            return title

        except Exception as e:
            logger.warning(
                "Failed to extract expected instructions title from instructions body.",
                extra={
                    "error": str(e),
                    "instructions": instructions_body,
                },
            )
            return None

    def _normalize_title(title: str):
        """Trim and remove trailing parentheses, then normalize case for comparison."""
        REMOVE_TRAILING_PARENS_REGEX = r"\s*\(.*\)\s*$"

        normalized = title.strip()
        normalized = re.sub(REMOVE_TRAILING_PARENS_REGEX, "", normalized)
        return normalized.casefold()

    logger = logging.getLogger(__name__)
    all_subsections = [
        subsection
        for section in sections
        for subsection in section.get("subsections", [])
    ]
    # For each instruction table
    for instruction_table in instructions_tables:
        # Take only the inner content of the instruction table, discarding outer one-cell table
        instructions_body = BeautifulSoup(
            instruction_table.find("td").decode_contents(), "html.parser"
        )

        instructions_title = _extract_instructions_title(instructions_body)
        if not instructions_title:
            continue  # Skip if we couldn't extract a title

        # Remove anything trailing in parens
        instructions_title = _normalize_title(instructions_title)

        # Check each subsection for a matching name
        found_match = False
        for subsection in all_subsections:
            if name := subsection.get("name", ""):
                # Get the subsection name, less any trailing parens
                subsection_name = _normalize_title(name)
                if subsection_name == instructions_title:
                    # If subsection already has instructions, skip it -- only one set of instructions per subsection
                    # This is unexpected
                    if "instructions" in subsection:
                        continue

                    subsection["instructions"] = instructions_body
                    found_match = True
                    break  # Stop searching after the first match

            # For subsections without a name, check if the body starts with the instructions title
            else:
                body = subsection.get("body", "")
                if isinstance(body, Tag):
                    body = body.get_text()
                elif isinstance(body, list) and len(body) > 0:
                    if isinstance(body[0], Tag):
                        body = body[0].get_text()
                else:
                    body = body.strip()

                if body.lower().startswith(instructions_title.lower()):
                    # If subsection already has instructions, skip it -- only one set of instructions per subsection
                    # This is unexpected
                    if "instructions" in subsection:
                        logger.info(
                            "Duplicate instructions found",
                            extra={"instructions_title": instructions_title},
                        )
                        continue

                    subsection["instructions"] = instructions_body
                    found_match = True
                    break  # Stop searching after the first match

        if not found_match:
            logger.warning(
                "No matching subsection found for instructions.",
                extra={"instructions_title": instructions_title},
            )


def normalize_whitespace_img_alt_text(soup):
    """
    This function mutates the soup!

    Normalize whitespace in image alt text by replacing all occurrences
    of double newlines (\n\n) with a single newline (\n).

    :param soup: BeautifulSoup object to modify in place.
    """
    for img in soup.find_all("img"):
        if img.has_attr("alt"):
            img["alt"] = img["alt"].replace("\n\n", "\n")


def extract_page_break_context(body, html_class=None):
    results = []

    if html_class and any(c.startswith("page-break") for c in html_class.split()):
        results.append(
            '<strong><mark class="bg-yellow">Page break at top of section found.</mark></strong>'
        )

    cleaned_body = strip_markdown_links(body) if body else ""
    contexts = extract_highlighted_context(cleaned_body, r"page-break")

    if contexts:
        for ctx in contexts:
            results.append(f"<p>{ctx}</p>")
    elif not results:
        results.append(
            "<p><em>Page break found in CSS classes or other locations</em></p>"
        )

    return "".join(results)


def count_page_breaks_nofo(nofo):
    """
    Count the total number of page breaks in all subsections of a NOFO.

    Args:
        nofo: A Nofo instance

    Returns:
        int: Total number of page breaks across all subsections
    """
    return sum(
        count_page_breaks_subsection(subsection)
        for section in nofo.sections.all()
        for subsection in section.subsections.all()
    )


def count_page_breaks_subsection(subsection):
    """
    Count the number of page breaks in a subsection.

    Args:
        subsection: The subsection object to check for page breaks

    Returns:
        int: The total number of page breaks (CSS class + word occurrences)
    """
    # Count CSS class page breaks
    css_breaks = 0
    if subsection.html_class:
        css_breaks = sum(
            1 for c in subsection.html_class.split() if c.startswith("page-break")
        )

    body = subsection.body

    # Add newlines at beginning and end if not present to handle edge cases
    if not body.startswith("\n"):
        body = "\n" + body
    if not body.endswith("\n"):
        body = body + "\n"

    # Count page breaks
    newline_breaks = len(re.findall(r"page-break", body))

    return css_breaks + newline_breaks


def remove_page_breaks_from_subsection(subsection):
    """
    Remove page breaks from a subsection.

    Only removes lowercase 'page-break'.
    Page breaks that appear within sentences (like "what if there is a page-break here?") are also removed.
    Uppercase 'PAGE-BREAK' or mixed case variations are preserved.

    Args:
        subsection: The subsection object to remove page breaks from

    Returns:
        subsection: The updated subsection object
    """
    # 1. Remove CSS class page breaks
    if subsection.html_class:
        # Get all non-pagebreak classes
        classes = [
            c for c in subsection.html_class.split() if not c.startswith("page-break")
        ]
        # Update html_class with only non-pagebreak classes
        subsection.html_class = " ".join(classes) if classes else ""

    # 2. Remove all `page-breaks`
    subsection.body = re.sub(r"page-break", "", subsection.body)

    return subsection


###########################################################
#################### ADD TO HTML FUNCS ####################
###########################################################

PUBLIC_INFORMATION_SUBSECTION = {
    "name": "Important: public information",
    "order": None,  # This will be dynamically set
    "tag": "h5",
    "html_id": "",
    "is_callout_box": True,
    "body": """
When filling out your SF-424 form, pay attention to Box 15: Descriptive Title of Applicant's Project.

We share what you put there with [USAspending](https://www.usaspending.gov). This is where the public goes to learn how the federal government spends their money.

Instead of just a title, insert a short description of your project and what it will do.

[See instructions and examples](https://www.hhs.gov/sites/default/files/hhs-writing-award-descriptions.pdf).
""",
}


def add_final_subsection_to_step_3(sections):
    """
    This function accepts a list of section dicts, _not_ Section objects.

    This function looks for a section named either "Step 3: Prepare Your Application"
    or "Step 3: Write Your Application" (case-insensitive).

    If found, then looks for a subsection called "Other required forms", "Standard forms", or "Application components".
    It looks in reverse order for a matching subsection name, so it matches the one closest to the end of the section.

        If either of those are found, then a new subsection is added immediately afterwards.
        If none are found, then the new subsection is added as the final subsection.

    but only if a subsection with the same name doesn't already exist.

    Args:
        sections (list of dict): A list of section dictionaries, where each section may
            contain a "name" (str) and a "subsections" (list of dict) key.

    Side Effects:
        - Modifies the `sections` list in-place by adding a new subsection to the
          matching "Step 3" section if it doesn't already exist.

    Note:
        This function stops searching after finding and modifying the first matching
        "Step 3" section.
    """

    def _insert_new_subsection_at_order_number(subsections, order_number):
        """
        Inserts an empty space in the list at the specified order_number.
        Increments the order of all elements with order >= order_number.

        :param subsections: List of subsection dictionaries with "order" values.
        :param order_number: The order number where the space should be inserted.
        """
        new_public_information_subsection = PUBLIC_INFORMATION_SUBSECTION.copy()
        new_public_information_subsection["order"] = order_number

        if order_number <= len(subsections):
            for subsection in subsections:
                if subsection.get("order", 0) >= order_number:
                    # increment order numbers
                    subsection["order"] += subsection["order"] + 1

            # insert at specific position in array
            subsections.insert(order_number - 1, new_public_information_subsection)

        else:
            # insert at the end of the array
            subsections.append(new_public_information_subsection)

    # The target section names to search for
    step_3_names = [
        "Step 3: Prepare Your Application",
        "Step 3: Write Your Application",
    ]

    subsection_names = [
        "Other required forms",
        "Standard forms",
        "Application components",
    ]

    for section in sections:
        # case insensitive match
        if section.get("name", "").lower() in [name.lower() for name in step_3_names]:
            # Get the subsections array
            subsections = section.get("subsections", [])

            # Check if subsection already exists
            public_info_name = PUBLIC_INFORMATION_SUBSECTION["name"]
            if any(sub.get("name") == public_info_name for sub in subsections):
                break

            order_number = None

            # find the new subsection to insert after (starting from the last match)
            for subsection in reversed(subsections):
                if subsection.get("name", "").lower() in [
                    name.lower() for name in subsection_names
                ]:
                    order_number = subsection.get("order") + 1
                    break  # Stop loop once the LAST matching subsection name is found

            if not order_number:
                # set as last order if not yet set
                order_number = (
                    max((sub.get("order", 0) for sub in subsections), default=0) + 1
                )

            _insert_new_subsection_at_order_number(subsections, order_number)

            # Exit after adding new subsection
            break


def modifications_update_announcement_text(nofo):
    """
    Update announcement text in all subsection bodies of a given NOFO.
    Usually this is just in 1 subsection ("Key facts"), but I guess it could be in others.

    - Looks for "Announcement version: New" or "Announcement type: New" (case insensitive).
    - Replaces them with "Announcement version: Modified" or "Announcement type: Modified".
    - Mutates the NOFO object in place.

    :param nofo: The NOFO object containing sections and subsections.
    """
    patterns = [
        (
            re.compile(r"Announcement version:\s*(?:New|Initial)", re.IGNORECASE),
            "Announcement version: Modified",
        ),
        (
            re.compile(r"Announcement type:\s*(?:New|Initial)", re.IGNORECASE),
            "Announcement type: Modified",
        ),
    ]

    for section in nofo.sections.all():
        for subsection in section.subsections.all():
            updated_body = subsection.body
            for pattern, replacement in patterns:
                updated_body = pattern.sub(replacement, updated_body)

            if updated_body != subsection.body:
                subsection.body = updated_body
                subsection.save()


def find_matches_with_context(nofo, find_text, include_name=False):
    """
    Find all occurrences of text in NOFO subsections with context.

    Args:
        nofo: The NOFO object to search in
        find_text: The text to find (case-insensitive)

    Returns:
        list: A list of dictionaries containing:
            - section: The Section object
            - subsection: The Subsection object
            - subsection_body_highlight: The subsection body with matches highlighted
    """

    def _is_basic_info_first_subsection(subsection):
        """
        Returns True if the subsection is the 'Basic Information' subsection
        (with order 1 in section order 1), which we want to skip.
        """
        return (
            subsection.name
            and subsection.name.lower() == "basic information"
            and subsection.order == 1
            and subsection.section.order == 1
        )

    matches = []
    pattern = re.compile(re.escape(find_text), re.IGNORECASE)

    for section in nofo.sections.prefetch_related("subsections").all():
        for subsection in section.subsections.all():
            if _is_basic_info_first_subsection(subsection):
                continue

            body_highlight = None
            name_highlight = None

            # --- Match body ---
            # Strip links unless search term starts with "http" or "#"
            if find_text.lower().startswith(("http", "#")):
                cleaned_body = subsection.body or ""
            else:
                cleaned_body = strip_markdown_links(subsection.body or "")

            if cleaned_body and pattern.search(cleaned_body):
                body_snippets = extract_highlighted_context(cleaned_body, pattern)
                body_highlight = "".join(f"<div>{s}</div>" for s in body_snippets)

            # --- Match name ---
            if include_name and subsection.name and pattern.search(subsection.name):
                name_snippets = extract_highlighted_context(subsection.name, pattern)
                name_highlight = "".join(f"<span>{s}</span>" for s in name_snippets)

            if body_highlight or name_highlight:
                matches.append(
                    {
                        "section": section,
                        "subsection": subsection,
                        "subsection_body_highlight": body_highlight,
                        "subsection_name_highlight": name_highlight,
                    }
                )

    return matches


def find_subsections_with_nofo_field_value(nofo, field_name):
    """
    Find all subsections containing the value of a specific NOFO field.

    Args:
        nofo: The NOFO object to search in
        field_name: The field name whose value will be searched for

    Returns:
        list: A list of dictionaries containing:
            - section: The Section object
            - subsection: The Subsection object
            - subsection_body_highlight: The subsection body with matches highlighted
    """
    value = getattr(nofo, field_name, None)
    if not value:
        return []

    return find_matches_with_context(nofo, find_text=value)


@transaction.atomic
def replace_value_in_subsections(
    subsection_ids, old_value, new_value, include_name=False
):
    """
    Replaces `old_value` with `new_value` in the bodies (and optionally names) of given subsection_ids.
    Uses case-insensitive replacement (e.g., "JUNE 1" will match "June 1").

    Returns the list of updated Subsection objects.

    If new_value or old_value is empty, returns an empty list.
    """
    if not subsection_ids or not old_value or not new_value:
        return []

    updated_subsections = []

    for subsection_id in subsection_ids:
        try:
            subsection = Subsection.objects.select_related("section").get(
                id=subsection_id
            )
        except Subsection.DoesNotExist:
            continue

        updated = False
        pattern = re.compile(re.escape(old_value), flags=re.IGNORECASE)

        # Update body
        if subsection.body:
            # Strip links unless "old value" starts with "http" or "#"
            if old_value.lower().startswith(("http", "#")):
                new_body = replace_text_include_markdown_links(
                    subsection.body, old_value, new_value
                )
            else:
                new_body = replace_text_exclude_markdown_links(
                    subsection.body, old_value, new_value
                )

            if new_body != subsection.body:
                subsection.body = new_body
                updated = True

        # Update name (optional)
        if include_name and subsection.name:
            new_name = pattern.sub(new_value, subsection.name)
            if new_name != subsection.name:
                subsection.name = new_name
                updated = True

        if updated:
            subsection.save()
            updated_subsections.append(subsection)

    return updated_subsections
