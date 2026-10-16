"""Framework-independent NOFO HTML normalization and section parsing.

This retains Builder's existing content rules and mutable parser objects.
It performs no persistence or implicit debug capture. See DOCUMENT_PROCESSING.md.
"""

import logging
import re
import unicodedata
from copy import deepcopy
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import cssutils
from bs4 import BeautifulSoup, NavigableString, Tag

from .content_text import clean_string
from .endnotes import (
    convert_bracketed_endnotes,
    is_endnotes_heading,
    linkify_endnote_citations,
    remove_duplicate_native_note_custom_marks,
)
from .nofo_markdown import MISSING_ALT_TEXT_ATTR, PRESERVE_BOOKMARK_TARGET_ATTR, md


class ContentProcessingError(ValueError):
    """A content failure that the application adapter presents to its user."""

    def __init__(self, message, *, code):
        self.code = code
        super().__init__(message)


class AmbiguousHeadingHierarchyError(ContentProcessingError):
    def __init__(self, *, h2_text, h1_text, preceding_h2_count=None):
        self.h2_text = h2_text
        self.h1_text = h1_text
        self.preceding_h2_count = preceding_h2_count
        super().__init__(
            "The document uses Heading 2 before its first Heading 1. "
            f'NOFO Builder would skip content beginning with Heading 2 "{h2_text}" '
            f'and start at Heading 1 "{h1_text}".',
            code="ambiguous_heading_hierarchy",
        )


DEFAULT_NOFO_OPPORTUNITY_NUMBER = "NOFO #999"


def resolve_section_heading_level(soup):
    """Choose the section heading level without silently discarding earlier content."""
    section_heading_candidates = [
        heading
        for heading in soup.find_all(["h1", "h2"])
        if clean_string(heading.get_text(" ", strip=True))
        and heading.find_parent("table") is None
    ]

    first_h1_index = next(
        (
            index
            for index, heading in enumerate(section_heading_candidates)
            if heading.name == "h1"
        ),
        None,
    )
    if first_h1_index is None:
        return "h2"

    h2_before_first_h1 = next(
        (
            heading
            for heading in section_heading_candidates[:first_h1_index]
            if heading.name == "h2"
        ),
        None,
    )
    if h2_before_first_h1 is None:
        return "h1"

    h2_text = clean_string(h2_before_first_h1.get_text(" ", strip=True))
    h1_text = clean_string(
        section_heading_candidates[first_h1_index].get_text(" ", strip=True)
    )
    # A lone final H1 is a likely style outlier, not evidence that preceding
    # H2s are its children. Do not infer intent from counts in mixed hierarchies.
    trailing_h1_outlier = (
        first_h1_index == len(section_heading_candidates) - 1 and first_h1_index >= 2
    )
    raise AmbiguousHeadingHierarchyError(
        h2_text=h2_text,
        h1_text=h1_text,
        preceding_h2_count=first_h1_index if trailing_h1_outlier else None,
    )


def unwrap_heading_containers(soup):
    """Expose headings in ordinary div wrappers without flattening tables or lists.

    Section parsing expects body-level headings. Only an uninterrupted chain of
    ordinary divs up to the body is supported; semantic containers remain intact.
    Referenced wrapper IDs become aliases for the first heading in that wrapper.
    """
    wrappers = {}
    for heading in soup.find_all(
        lambda tag: tag.name in {"h1", "h2", "h3", "h4", "h5", "h6"} or is_h7(tag)
    ):
        ancestors = []
        parent = heading.parent
        while (
            parent is not None
            and parent.name == "div"
            and not parent.get("role")
            and not is_h7(parent)
        ):
            ancestors.append(parent)
            parent = parent.parent
        if parent is None or parent.name not in {"body", "[document]"}:
            continue
        for wrapper in ancestors:
            wrappers.setdefault(id(wrapper), (wrapper, heading))

    for wrapper, heading in wrappers.values():
        wrapper_id = wrapper.get("id")
        if wrapper_id:
            heading_id = heading.get("id") or wrapper_id
            heading["id"] = heading_id
            for link in soup.find_all("a", href=f"#{wrapper_id}"):
                link["href"] = f"#{heading_id}"
        wrapper.unwrap()


def process_nofo_html(soup, top_heading_level, *, debug_capture=None):
    """
    Takes a soup object, cleans it up and mutates it, and returns a modified soup object.
    """
    soup = add_body_if_no_body(soup)
    unwrap_heading_containers(soup)

    if debug_capture is not None:
        debug_capture(soup)

    instructions_tables = decompose_instructions_tables(soup)
    merge_funding_details_label_value_paragraphs(soup)
    normalize_whitespace_img_alt_text(soup)
    add_missing_alt_text_to_imgs(soup)
    join_nested_lists(soup)
    add_strongs_to_soup(soup)
    repair_acf_required_alignment_lists(soup)
    preserve_bookmark_links(soup)
    preserve_heading_links(soup)
    preserve_table_heading_links(soup)
    clean_heading_tags(soup)
    decompose_before_you_begin_section(soup)
    clean_table_cells(soup)
    unwrap_empty_elements(soup)
    decompose_empty_tags(soup)
    combine_consecutive_links(soup)
    remove_google_tracking_info_from_links(soup)
    rename_footnotes_heading_to_endnotes(soup)
    add_endnotes_header_if_exists(soup, top_heading_level)
    unwrap_nested_lists(soup)
    preserve_bookmark_targets(soup)
    remove_duplicate_native_note_custom_marks(soup)  # IMPORT-053
    convert_bracketed_endnotes(soup)  # IMPORT-050 in documentation/IMPORT_RULES.md
    linkify_endnote_citations(soup)  # IMPORT-064

    soup = add_em_to_de_minimis(soup)

    return soup, instructions_tables


def merge_funding_details_label_value_paragraphs(soup):
    """Join split label/value paragraphs within Funding details subsections."""
    funding_details_headings = soup.find_all(
        lambda tag: tag.name in {"h3", "h4"}
        and clean_string(tag.get_text(" ", strip=True)).casefold() == "funding details"
    )

    for heading in funding_details_headings:
        heading_level = int(heading.name[1])
        current = heading.find_next_sibling()

        while current is not None:
            if re.fullmatch(r"h[1-6]", current.name or ""):
                current_level = int(current.name[1])
                if current_level <= heading_level:
                    break

            next_sibling = current.find_next_sibling()
            if (
                current.name == "p"
                and clean_string(current.get_text(" ", strip=True)).endswith(":")
                and next_sibling is not None
                and next_sibling.name == "p"
                and (next_text := clean_string(next_sibling.get_text(" ", strip=True)))
                and not next_text.endswith(":")
            ):
                last_text = current.find_all(string=True)[-1]
                last_text.replace_with(str(last_text).rstrip())

                first_value_text = next(
                    text
                    for text in next_sibling.find_all(string=True)
                    if str(text).strip()
                )
                first_value_text.replace_with(str(first_value_text).lstrip())

                current.append(" ")
                for child in list(next_sibling.contents):
                    current.append(child.extract())

                next_after_value = next_sibling.find_next_sibling()
                next_sibling.decompose()
                current = next_after_value
                continue

            current = next_sibling


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


def _heading_search_text(tag):
    """Preserve spaces at manual breaks without changing stored heading names."""
    if "data-builder-search-text" in tag.attrs:
        return tag.attrs.pop("data-builder-search-text")
    return "".join(
        (
            " "
            if isinstance(node, Tag) and node.name == "br"
            else str(node) if isinstance(node, NavigableString) else ""
        )
        for node in tag.descendants
    )


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
                        "source_tag": tag.name,
                        "search_text": _heading_search_text(tag),
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


def get_subsections_from_sections(
    sections, top_heading_level="h1", *, consume_scoped_tagline=False
):
    if_demote_headings = top_heading_level == "h1"
    heading_tags = ["h3", "h4", "h5", "h6"]
    key_callout_titles = {
        "key facts": "Key facts",
        "key dates": "Key dates",
        "application due date": "Application due date",
    }

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

    def get_key_callout_title(tag):
        if not tag:
            return None

        return key_callout_titles.get(
            clean_string(tag.get_text(" ", strip=True)).casefold()
        )

    def is_key_callout_title_paragraph(tag):
        return tag.name == "p" and get_key_callout_title(tag) is not None

    def is_empty_spacer_paragraph(tag):
        return (
            tag.name == "p"
            and not clean_string(tag.get_text(" ", strip=True))
            and tag.find("img") is None
        )

    def get_subsection_dict(
        heading_tag,
        order,
        is_callout_box,
        body=None,
        key_callout_title=None,
    ):
        if (
            consume_scoped_tagline
            and heading_tag
            and heading_tag.get("data-nofo-tagline-source") == "true"
        ):
            # Keep following body content visible, without a source heading.
            return {
                "name": "",
                "tag": "",
                "html_id": "",
                "order": order,
                "is_callout_box": False,
                "body": body or [],
                "consumed_tagline": True,
            }
        if heading_tag:
            if key_callout_title:
                tag_name = "h4"
            else:
                tag_name = (
                    _demote_tag(heading_tag.name)
                    if if_demote_headings
                    else heading_tag.name
                )
                if tag_name == "div" and is_h7(heading_tag):
                    tag_name = "h7"

            return {
                "name": key_callout_title or clean_string(heading_tag.text),
                "source_tag": "h7" if is_h7(heading_tag) else heading_tag.name,
                "search_text": key_callout_title or _heading_search_text(heading_tag),
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

        for index, tag in enumerate(body_descendents):
            next_tag = next(
                (
                    candidate
                    for candidate in body_descendents[index + 1 :]
                    if not is_empty_spacer_paragraph(candidate)
                ),
                None,
            )
            is_followed_by_callout = (
                next_tag is not None
                and next_tag.name == "table"
                and is_callout_box_table(next_tag)
            )

            # handle callout boxes
            if tag.name == "table" and is_callout_box_table(tag):
                # Grab the first td or th
                cell = tag.find("td")
                if not cell:
                    cell = tag.find("th")

                # make the td a div so that it can live on its own
                cell.name = "div"
                heading_tag = extract_first_header(cell)
                callout_box_subsection = get_subsection_dict(
                    heading_tag=heading_tag,
                    order=len(section["subsections"]) + 1,
                    is_callout_box=True,
                    body=cell,
                    key_callout_title=get_key_callout_title(heading_tag),
                )
                section["subsections"].append(callout_box_subsection)

            elif tag.name in heading_tags or is_h7(tag):
                # create new subsection
                key_callout_title = (
                    get_key_callout_title(tag) if is_followed_by_callout else None
                )
                heading_subsection = get_subsection_dict(
                    heading_tag=tag,
                    order=len(section["subsections"]) + 1,
                    is_callout_box=False,
                    key_callout_title=key_callout_title,
                )

                section["subsections"].append(heading_subsection)

            elif is_key_callout_title_paragraph(tag) and is_followed_by_callout:
                heading_subsection = get_subsection_dict(
                    heading_tag=tag,
                    order=len(section["subsections"]) + 1,
                    is_callout_box=False,
                    key_callout_title=get_key_callout_title(tag),
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

        if any(
            subsection.get("consumed_tagline") for subsection in section["subsections"]
        ):
            section["subsections"] = [
                subsection
                for subsection in section["subsections"]
                if not subsection.get("consumed_tagline") or subsection["body"]
            ]
            for order, subsection in enumerate(section["subsections"], 1):
                subsection.pop("consumed_tagline", None)
                subsection["order"] = order
    return sections


END_NOTES_SECTION_NAME = "Endnotes"


def sanitize_imported_text(value: str) -> str:
    if not value:
        return ""

    value = unicodedata.normalize("NFKC", value)

    # Remove invisible/control/format characters, including zero-width chars.
    value = "".join(ch for ch in value if unicodedata.category(ch)[0] != "C")

    # Collapse whitespace and trim.
    value = re.sub(r"\s+", " ", value).strip()

    return value


METADATA_LABEL_PATTERN = re.compile(r"^\s*[^:\n]{1,80}:\s*\S*", re.IGNORECASE)


INVALID_OPDIV_ACRONYMS = {"N/A", "NA", "NONE", "TBD", "UNKNOWN"}


METADATA_BLOCK_LABELS = {
    "opdiv",
    "agency",
    "subagency",
    "subagency2",
    "opportunityname",
    "opportunitynumber",
    "applicationdeadline",
    "metadataauthor",
    "metadatasubject",
    "metadatakeywords",
}


def _metadata_label_key(label):
    return re.sub(r"\s+", "", sanitize_imported_text(label)).casefold()


def metadata_block_fields(heading):
    """Read a Metadata heading's contiguous field paragraphs without mutation.

    Any heading, non-paragraph element, or non-label prose ends the block,
    regardless of heading level. Blank paragraphs may separate fields. None
    means this is not a recognized block; an empty field still recognizes it.
    """
    return _metadata_block(heading)[0]


def _metadata_block(heading):
    """One recognition grammar for extraction and bounded source consumption."""
    if (
        not (heading.name in ("h1", "h2", "h3", "h4", "h5", "h6") or is_h7(heading))
        or sanitize_imported_text(heading.get_text()).casefold() != "metadata"
    ):
        return None, []
    fields = {}
    elements = [heading]
    for element in heading.find_next_siblings():
        if element.name != "p":
            break
        # Text extraction alone must not mistake a diagram/media paragraph for
        # a blank separator or consume an image embedded beside a field label.
        if element.find(
            [
                "img",
                "svg",
                "picture",
                "video",
                "audio",
                "object",
                "embed",
                "iframe",
                "canvas",
                "input",
            ]
        ):
            break
        text = sanitize_imported_text(element.get_text())
        if not text:
            elements.append(element)
            continue
        label, separator, value = text.partition(":")
        key = _metadata_label_key(label)
        if not separator or key not in METADATA_BLOCK_LABELS:
            break
        # First occurrence wins, including a blank, just like legacy scanning.
        fields.setdefault(key, sanitize_imported_text(value))
        elements.append(element)
    return fields or None, elements if fields else []


def builder_import_content(soup):
    """Keep the extraction source intact; consume Metadata only in Builder content.

    Reusing the intact soup in the existing confirmation session preserves every
    field read, including authoritative blanks and independent legacy fields.
    This copy is used only to choose headings and construct incoming sections.
    """
    content = deepcopy(soup)
    removed_ids = set()
    removed = []
    for heading in content.find_all(
        lambda tag: tag.name in ("h1", "h2", "h3", "h4", "h5", "h6") or is_h7(tag)
    ):
        fields, elements = _metadata_block(heading)
        if fields is None:
            continue
        for element in elements:
            for target in [element] + element.find_all(id=True):
                if target.get("id"):
                    removed_ids.add(target["id"])
            removed.append(element)
    for element in removed:
        element.decompose()
    # Do not guess another section destination or invent hidden duplicate
    # subsections. Preserve link text; leave genuinely surviving targets alone.
    for target_id in removed_ids:
        if content.find(id=target_id) is None:
            for link in content.find_all("a", href=f"#{target_id}"):
                link.unwrap()
    return content


def recognized_metadata_block(soup):
    """Return the last recognized block; never combine separate blocks."""
    result = None
    for heading in soup.find_all(
        lambda tag: tag.name in ("h1", "h2", "h3", "h4", "h5", "h6") or is_h7(tag)
    ):
        fields = metadata_block_fields(heading)
        if fields is not None:
            result = fields
    return result


def _looks_like_metadata_label(value):
    return bool(METADATA_LABEL_PATTERN.match(sanitize_imported_text(value)))


def _is_invalid_opdiv_placeholder(value):
    return sanitize_imported_text(value).upper() in INVALID_OPDIV_ACRONYMS


def _suggest_by_startswith_string(soup, startswith_string, use_next_paragraph=False):
    key = _metadata_label_key(startswith_string.rstrip(":"))
    if key in METADATA_BLOCK_LABELS:
        fields = recognized_metadata_block(soup)
        if fields is not None:
            # A recognized block is authoritative, even when this field is
            # absent or blank. Do not borrow an unrelated front-page value.
            return fields.get(key, "")
    suggestion = ""
    regex = re.compile(r"^\s*{}".format(re.escape(startswith_string)), re.IGNORECASE)
    if key in {"subagency", "subagency2"}:
        suffix = r"\s*2" if key == "subagency2" else ""
        regex = re.compile(r"^\s*Sub\s*Agency" + suffix + r"\s*:", re.IGNORECASE)
    element = soup.find(string=regex)

    # look for the paragraph
    if element and element.name != "p":
        for parent in element.parents:
            if parent.name == "p":
                element = parent
                break

    if element:
        suggestion = regex.sub("", element.text)

    if (
        use_next_paragraph
        and not sanitize_imported_text(suggestion)
        and getattr(element, "name", None) == "p"
    ):
        next_element = element.find_next_sibling()
        if next_element and next_element.name == "p":
            candidate = sanitize_imported_text(next_element.get_text(" "))
            following_element = next_element.find_next_sibling()
            following_text = (
                sanitize_imported_text(following_element.get_text(" "))
                if following_element and following_element.name == "p"
                else ""
            )
            # Metadata surrounding the value establishes its role. A value at a
            # heading or document boundary is ambiguous, so leave it for the
            # actionable recovery flow rather than silently guessing.
            if (
                candidate
                and not _is_invalid_opdiv_placeholder(candidate)
                and not _looks_like_metadata_label(candidate)
                and _looks_like_metadata_label(following_text)
            ):
                suggestion = candidate

    return sanitize_imported_text(suggestion)


def suggest_nofo_opportunity_number(soup):
    opportunity_number_default = DEFAULT_NOFO_OPPORTUNITY_NUMBER
    suggestion = _suggest_by_startswith_string(soup, "Opportunity Number:")
    return suggestion or opportunity_number_default


def suggest_nofo_opdiv(soup):
    suggestion = _suggest_by_startswith_string(soup, "Opdiv:", use_next_paragraph=True)
    return suggestion or ""


def extract_basic_information_tagline(soup, top_heading_level):
    """Mark only the scoped new-format source, before empty-tag cleanup.

    None means no new source (legacy fallback); an empty string is an
    intentionally blank new source. Normal repairs run before paragraph
    consumption; sectioning then consumes the marked heading. Builder only.
    """
    section_level = int(top_heading_level[1])
    # These are internal conversion markers, never instructions from an upload.
    for node in soup.find_all(True):
        node.attrs.pop("data-nofo-tagline-source", None)
        node.attrs.pop("data-nofo-tagline-value", None)
    in_step_one = False
    basic_level = None
    container = soup.body or soup
    for tag in list(container.children):
        if not isinstance(tag, Tag) or tag.name not in (
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
        ):
            continue
        level = int(tag.name[1])
        text = sanitize_imported_text(tag.get_text(" ", strip=True)).casefold()
        if level <= section_level:
            in_step_one = level == section_level and bool(
                re.fullmatch(r"step 1\s*:\s*review the opportunity", text)
            )
            basic_level = None
            continue
        if not in_step_one:
            continue
        if basic_level is not None and level <= basic_level:
            basic_level = None
        if text == "basic information" and level == section_level + 1:
            basic_level = level
            continue
        if text != "tagline" or basic_level is None or level != basic_level + 1:
            continue
        paragraph = tag.find_next_sibling()
        value = ""
        if paragraph is not None and paragraph.name == "p":
            # Keep inline emphasis/links using the field's existing Markdown
            # representation. A paragraph containing an image is not a tagline.
            if not paragraph.find("img"):
                value = sanitize_imported_text(md(str(paragraph), escape_misc=False))
                # Leave links in the soup until normal import repairs run.
                paragraph["data-nofo-tagline-value"] = "true"
        # Sectioning consumes this heading but retains a nameless body boundary.
        tag["data-nofo-tagline-source"] = "true"
        return value
    return None


def consume_tagline_paragraph(soup, imported_tagline):
    if imported_tagline is None:
        return None
    heading = soup.find(attrs={"data-nofo-tagline-source": "true"})
    if heading is not None and heading.get("id"):
        # A consumed source heading must not strand incoming links. Basic
        # information remains a visible target even for an empty tagline.
        basic = heading.find_previous(
            lambda tag: tag.name == f"h{int(heading.name[1]) - 1}"
            and sanitize_imported_text(tag.get_text(" ", strip=True)).casefold()
            == "basic information"
            and tag.parent == heading.parent
        )
        if basic is not None:
            source_id = heading.attrs.pop("id")
            target_id = basic.get("id") or source_id
            basic["id"] = target_id
            for link in soup.find_all("a", href="#" + source_id):
                link["href"] = "#" + target_id
    paragraph = soup.find("p", attrs={"data-nofo-tagline-value": "true"})
    if paragraph is None:
        return ""
    value = sanitize_imported_text(md(str(paragraph), escape_misc=False))
    paragraph.decompose()
    return value


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
        # IMPORT-066: reconstructed native Word trees already encode identity,
        # level, type and restart boundaries. Legacy class repair must not merge
        # separate numbering instances or reinterpret those parent relationships.
        if lst.has_attr("data-nofo-source-list") or previous_lst.has_attr(
            "data-nofo-source-list"
        ):
            return
        if (lst.has_attr("type") or previous_lst.has_attr("type")) and (
            lst.get("type") != previous_lst.get("type")
            or lst.get("start", "1") != previous_lst.get("start", "1")
        ):
            return
        if _get_list_classname(lst) == _get_list_classname(previous_lst):
            # if classes match, join these lists
            previous_lst.extend(lst.find_all("li", recursive=False))
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


def is_acf_nofo_metadata(nofo_number="", opdiv=""):
    """Return whether imported metadata identifies an ACF NOFO."""
    number = sanitize_imported_text(nofo_number).casefold()
    opdiv_text = sanitize_imported_text(opdiv).casefold()

    return bool(
        re.search(r"(?:^|-)acf(?:-|$)", number)
        or "administration for children and families" in opdiv_text
        or re.search(r"\bacf\b", opdiv_text)
    )


def repair_acf_required_alignment_lists(soup):
    """Normalize the canonical ACF required-alignment groups to numbering."""
    nofo_number = suggest_nofo_opportunity_number(soup)
    opdiv = suggest_nofo_opdiv(soup)
    if not is_acf_nofo_metadata(nofo_number, opdiv):
        return soup

    heading_names = {f"h{level}" for level in range(1, 7)}
    required_title = (
        "required alignment with acf vision, mission, values, priorities, "
        "and guiding principles"
    )
    opening_prefix = (
        "the recipient of this award must implement any funds awarded under this "
        "nofo to effectuate program goals or agency priorities"
    )
    expected_label_groups = [
        ["program integrity and fiscal stewardship:"],
        [
            "evidence-based and outcome-focused practices:",
            "partnership and local leadership:",
        ],
        [
            "family stability and child well-being:",
            "work, self-sufficiency, and economic mobility:",
            "high-quality early care and learning:",
        ],
    ]

    def _normalized_text(tag):
        return clean_string(tag.get_text(" ", strip=True)).casefold()

    def _heading_level(tag):
        return int(tag.name[1])

    agency_headings = soup.find_all(
        lambda tag: tag.name in heading_names
        and _normalized_text(tag) == "agency priorities"
    )

    for agency_heading in agency_headings:
        agency_level = _heading_level(agency_heading)
        containing_section_heading = agency_heading.find_previous(
            lambda tag: tag.name in heading_names and _heading_level(tag) < agency_level
        )
        if containing_section_heading is None or not _normalized_text(
            containing_section_heading
        ).startswith("step 1"):
            continue

        content_tags = []
        for sibling in agency_heading.next_siblings:
            if not isinstance(sibling, Tag):
                continue
            if (
                sibling.name in heading_names
                and _heading_level(sibling) <= agency_level
            ):
                break
            if clean_string(sibling.get_text(" ", strip=True)):
                content_tags.append(sibling)

        if len(content_tags) < 2:
            continue

        title_tag = content_tags[0]
        title_strong = title_tag.find("strong")
        title_is_bold_paragraph = (
            title_tag.name == "p"
            and title_strong is not None
            and _normalized_text(title_strong) == required_title
        )
        title_is_nested_heading = (
            title_tag.name in heading_names
            and _heading_level(title_tag) == agency_level + 1
        )
        if _normalized_text(title_tag) != required_title or not (
            title_is_bold_paragraph or title_is_nested_heading
        ):
            continue

        if not _normalized_text(content_tags[1]).startswith(opening_prefix):
            continue

        lists = [tag for tag in content_tags if tag.name in {"ul", "ol"}]
        if len(lists) != len(expected_label_groups):
            continue

        actual_label_groups = []
        for source_list in lists:
            labels = []
            for item in source_list.find_all("li", recursive=False):
                strong = item.find("strong")
                labels.append(_normalized_text(strong) if strong else "")
            actual_label_groups.append(labels)

        if actual_label_groups != expected_label_groups:
            continue

        for start, source_list in zip((1, 2, 4), lists):
            source_list.name = "ol"
            # IMPORT-052 deliberately overrides source markers only for its
            # exact agency/content pattern; generic source preservation runs first.
            source_list.attrs.pop("type", None)
            if start == 1:
                source_list.attrs.pop("start", None)
            else:
                source_list["start"] = str(start)

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

        link_href = link.get("href")
        next_sibling_is_link = next_sibling and next_sibling.name == "a"
        next_link_href = next_sibling.get("href") if next_sibling_is_link else None
        same_nonempty_href = link_href and link_href == next_link_href
        same_id_only_target = (
            not link_href
            and not next_link_href
            and link.get("id")
            and next_sibling_is_link
            and link.get("id") == next_sibling.get("id")
        )

        if (
            next_sibling
            and next_sibling.name == "a"
            and (same_nonempty_href or same_id_only_target)
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


def unwrap_empty_elements(soup):
    """
    This function mutates the soup!

    Unwraps empty or image-only span, strong, sup, a, and em tags from the BeautifulSoup `soup`.
    """
    elements = soup.find_all(["em", "span", "strong", "sup"])

    for el in elements:
        # Case 1: no text content
        has_text = bool(el.get_text(strip=True))

        # Case 2: contains images
        has_img = el.find("img") is not None

        # Case 3: any non-whitespace, non-img children?
        meaningful_children = [
            child
            for child in el.contents
            if getattr(child, "name", None)
            and child.name != "img"
            and child.get_text(strip=True)
        ]

        # Only formatting wrappers with no meaningful text
        if not has_text and (has_img or not meaningful_children):
            el.unwrap()


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
        if not tag.get_text().strip() and tag.name not in ["br", "hr", "img"]:
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


def rename_footnotes_heading_to_endnotes(soup):
    """Normalize structural note headings in imported HTML, never on page access.

    Preserve separate headings when there are several note sections; the matcher
    reports the ambiguity instead of silently merging their citation lists.

    Implements import rule IMPORT-049 in documentation/IMPORT_RULES.md.
    """
    headings = soup.find_all(re.compile(r"^h[1-6]$")) + soup.find_all(is_h7)

    for heading in headings:
        if is_endnotes_heading(heading.get_text()):
            heading.string = END_NOTES_SECTION_NAME


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
        return (
            tag.name in {"h1", "h2", "h3", "h4", "h5", "h6", "h7"} or is_h7(tag)
        ) and is_endnotes_heading(tag.get_text())

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
    # Only local top-level rules are examined. Never fetch @import URLs.
    parser = cssutils.CSSParser(
        fetcher=lambda url: (None, ""), loglevel=logging.CRITICAL
    )
    stylesheet = parser.parseString(styles_as_text)

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
    # Work on text nodes so attributes (including Word Find snippets) stay plain.
    soup = BeautifulSoup(str(soup), "html.parser")
    pattern = re.compile(r"de minimis", re.IGNORECASE)
    for node in soup.find_all(string=pattern):
        if type(node) is not NavigableString or node.find_parent(
            ["em", "script", "style"]
        ):
            continue
        text = str(node)
        offset = 0
        for match in pattern.finditer(text):
            if match.start() > offset:
                node.insert_before(NavigableString(text[offset : match.start()]))
            emphasis = soup.new_tag("em")
            emphasis.string = match.group()
            node.insert_before(emphasis)
            offset = match.end()
        if offset < len(text):
            node.insert_before(NavigableString(text[offset:]))
        node.extract()
    return soup


def clean_heading_tags(soup):
    """
    This function mutates the soup!

    Finds all headings, it will:
    - Unwrap span tags in the heading
    - Collapse multiple spaces into one
    - Trim leading and trailing spaces
    - Decomposes headings that are empty after cleanup
    """
    # Find all headings (h1, h2, ..., h6)
    headings = soup.find_all(re.compile(r"^h[1-6]$"))

    for heading in headings:
        # Retain a searchable version before cleanup removes manual breaks.
        # A temporary attribute survives later soup reparsing. The section
        # parser consumes it; it is not stored as heading content.
        heading["data-builder-search-text"] = _heading_search_text(heading)
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

        # If heading is empty after cleanup, remove it
        if not text:
            heading.decompose()


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

    Preserves referenced empty bookmark targets at their exact source locations and normalizes
    unreferenced non-Word bookmark targets onto their parent elements.

    Referenced empty anchors are marked so the Markdown converter retains them as minimal raw HTML
    anchors. Unreferenced anchors without an underscore prefix continue through the existing
    ``nb_bookmark_`` parent-transfer behavior. Unreferenced Word bookmarks whose IDs begin with an
    underscore are left alone and may be discarded by Markdown conversion.

    Unique referenced list-item IDs are moved to a minimal anchor at the start
    of the item so normal Markdown list conversion does not discard them.
    Native Word footnote/endnote IDs retain their existing raw-list handling.
    """
    referenced_ids = {
        link["href"][1:]
        for link in soup.find_all("a", href=True)
        if link["href"].startswith("#") and link["href"][1:]
    }

    id_counts = {}
    for target in soup.find_all(id=True):
        target_id = target["id"]
        id_counts[target_id] = id_counts.get(target_id, 0) + 1

    for item in soup.find_all("li", id=True):
        target_id = item["id"]
        if (
            target_id not in referenced_ids
            or id_counts.get(target_id) != 1
            or target_id.startswith(("footnote", "endnote"))
        ):
            continue
        anchor = soup.new_tag("a", id=target_id)
        anchor[PRESERVE_BOOKMARK_TARGET_ATTR] = ""
        item.insert(0, anchor)
        del item["id"]

    empty_links = [
        a for a in soup.find_all("a", id=True, href=False) if not a.text.strip()
    ]
    for link in empty_links:
        original_id = link.get("id", "")

        if not original_id:
            continue

        if original_id in referenced_ids:
            # Mark only targets that are actually referenced. The Markdown
            # converter retains these empty anchors as raw HTML and removes
            # this implementation-only attribute.
            link[PRESERVE_BOOKMARK_TARGET_ATTR] = ""
            continue

        if not link.get("id", "").startswith("_"):
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
        if li.find_parent(attrs={"data-nofo-source-list": True}):
            continue
        if _has_only_nested_ul(li):
            li.unwrap()

    for ul in soup.select("ul > ul"):
        if ul.has_attr("data-nofo-source-list") or ul.find_parent(
            attrs={"data-nofo-source-list": True}
        ):
            continue
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


BEFORE_YOU_BEGIN_HEADING_TEXT = "before you begin"


def _is_before_you_begin_heading(tag):
    """
    Returns True if "tag" is a heading (h1-h6) whose text, once normalized for
    casing, punctuation, and whitespace, reads exactly "before you begin".
    """
    if tag.name not in ("h1", "h2", "h3", "h4", "h5", "h6"):
        return False

    from .introductory_page import introductory_heading_name

    heading_text = introductory_heading_name(tag)
    return heading_text == BEFORE_YOU_BEGIN_HEADING_TEXT or (
        tag.find_parent("body")
        and tag.find_parent("body").has_attr("data-nofo-introductory-family")
        and heading_text == "before you get started"
    )


def _looks_like_metadata_line(tag):
    """
    Returns True if "tag" is a paragraph that looks like a metadata label,
    whether the value is on the same line or in the following paragraph.
    """
    if tag.name != "p":
        return False

    label, separator, _ = tag.get_text(" ", strip=True).partition(":")
    return bool(separator) and re.sub(r"\s+", "", label).casefold() in {
        "opportunitynumber",
        "opportunityname",
        "applicationdeadline",
        "opdiv",
        "agency",
        "subagency",
        "subagency2",
        "tagline",
        "metadataauthor",
        "metadatasubject",
        "metadatakeywords",
    }


def decompose_before_you_begin_section(soup):
    """
    This function mutates the soup!

    NOFOs exported from the GrantSolutions Announcement Module (GS AM) include a
    "Before You Begin" heading and section that duplicates the "Before you begin"
    page NOFO Builder already generates for every NOFO from its own
    `before_you_begin` field. Because that content is always redundant, it is
    removed silently on import; documents that don't include this heading are
    unaffected.

    Finds any heading (h1-h6) whose text reads "before you begin" and removes it,
    along with all of the content that follows it, up until whichever comes
    first:
    - the next heading of the same or a higher level (ie, the section it
      introduces), or
    - a metadata label, since GS AM exports place NOFO front matter
      (opportunity number, agency, tagline, etc.) directly after this heading,
      sometimes with the value in the following paragraph. That content must
      be preserved.
    - a recognized Metadata heading and field block, even at a lower level.

    Returns the list of extracted tags (the heading plus its section content).
    """
    from .introductory_page import imported_introduction

    if imported_introduction(soup):
        return []
    removed = []

    headings = [
        tag
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
        if tag.parent and tag.parent.name in ["body", "[document]"]
    ]

    for heading in headings:
        if not heading.parent:
            # Already removed as part of a previously matched heading's section.
            continue

        if not _is_before_you_begin_heading(heading):
            continue

        level = int(heading.name[1])
        tags_to_remove = [heading]

        for sibling in heading.find_next_siblings():
            if sibling.name in {"h1", "h2", "h3", "h4", "h5", "h6"} and clean_string(
                sibling.get_text(" ", strip=True)
            ).casefold().strip(":") in {"footnote", "footnotes", "endnote", "endnotes"}:
                break
            if sibling.name == "ol" and sibling.find(
                id=lambda value: value and value.startswith(("footnote", "endnote"))
            ):
                break
            if (
                sibling.name in ("h1", "h2", "h3", "h4", "h5", "h6")
                and int(sibling.name[1]) <= level
            ):
                break
            if _looks_like_metadata_line(sibling):
                break
            if metadata_block_fields(sibling) is not None:
                break
            tags_to_remove.append(sibling)

        for tag in tags_to_remove:
            removed.append(tag.extract())

    return removed


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


def add_missing_alt_text_to_imgs(soup):
    """
    This function mutates the soup!

    Adds an empty alt="" attribute to any img tag that has no alt
    attribute at all, so that missing alt text is visible and greppable
    in the markdown/HTML source, rather than silently absent.

    Also tags the img with MISSING_ALT_TEXT_ATTR, a marker that tells
    NofoMarkdownConverter.convert_img (in nofo_markdown.py) to keep this
    image as raw HTML instead of converting it to markdown's ![]() syntax,
    which can't distinguish a backfilled alt="" from one that was always
    missing.

    Images that already have an alt attribute (including alt="") are
    left untouched.

    :param soup: BeautifulSoup object to modify in place.
    """
    for img in soup.find_all("img"):
        if not img.has_attr("alt"):
            img["alt"] = ""
            img[MISSING_ALT_TEXT_ATTR] = ""


@dataclass
class ProcessedDocumentContent:
    """Existing parser results, with source retained for application inference."""

    soup: BeautifulSoup
    sections: list
    instructions_tables: list
    imported_tagline: str | None = None


def get_sections_and_subsections_from_soup(
    soup, top_heading_level, *, consume_scoped_tagline=False, consume_metadata=False
):
    """Extract content dictionaries, retaining the existing validation code."""
    content = builder_import_content(soup) if consume_metadata else soup
    sections = get_sections_from_soup(content, top_heading_level)
    if not len(sections):
        raise ContentProcessingError(
            "That file does not contain a NOFO.", code="no_sections"
        )
    parsed = get_subsections_from_sections(
        sections, top_heading_level, consume_scoped_tagline=consume_scoped_tagline
    )
    from .introductory_page import INTRO_ANCHOR, imported_introduction

    if imported_introduction(soup):
        for index, section in enumerate(parsed):
            section["order"] = index
            if section.get("html_id") == INTRO_ANCHOR:
                section.update(
                    name="Before you get started",
                    role="introduction",
                    html_id=INTRO_ANCHOR,
                    has_section_page=False,
                )
    return parsed


def process_document_content(
    html,
    *,
    section_parser=None,
    builder_import=False,
    extract_scoped_tagline=False,
    editable_intro="generated",
    debug_capture=None,
):
    """Normalize HTML and parse sections without a request, upload or ORM record.

    ``section_parser`` preserves the application's existing overridable section
    parser. Instruction attachment and consumer postprocessing stay with callers.
    Exceptions propagate unchanged for the caller to present or handle.
    """
    cleaned_content = replace_links(replace_chars(html))
    soup = BeautifulSoup(cleaned_content, "html.parser")
    # Private processing state is server-derived, never an input format signal.
    if soup.body:
        soup.body.attrs.pop("data-nofo-introductory-content-mode", None)
    if builder_import:
        from .introductory_page import (
            capture_introductory_page,
            prepare_editable_introduction,
        )

        soup = capture_introductory_page(soup)
        soup = prepare_editable_introduction(soup, editable_intro)
    # Preserve the pre-pass before selecting the main section heading level.
    decompose_before_you_begin_section(soup)
    top_heading_level = resolve_section_heading_level(
        builder_import_content(soup) if builder_import else soup
    )
    imported_tagline = None
    if extract_scoped_tagline:
        unwrap_heading_containers(soup)
        imported_tagline = extract_basic_information_tagline(soup, top_heading_level)
    soup, instructions_tables = process_nofo_html(
        soup, top_heading_level, debug_capture=debug_capture
    )
    if extract_scoped_tagline:
        imported_tagline = consume_tagline_paragraph(soup, imported_tagline)
    if section_parser is None:
        section_parser = get_sections_and_subsections_from_soup
    if builder_import or extract_scoped_tagline:
        sections = section_parser(
            deepcopy(soup) if extract_scoped_tagline else soup,
            top_heading_level,
            consume_scoped_tagline=extract_scoped_tagline,
            consume_metadata=builder_import,
        )
    else:
        sections = section_parser(soup, top_heading_level)
    return ProcessedDocumentContent(
        soup, sections, instructions_tables, imported_tagline
    )
