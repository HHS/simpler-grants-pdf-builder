"""Internal content processing, separate from upload and persistence workflows.

This reuses Builder's NOFO-specific rules and parser objects, not a portable
interchange schema. See documentation/DOCUMENT_PROCESSING.md for dependencies.
"""

from copy import deepcopy
from dataclasses import dataclass

from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError

from .nofo import (
    builder_import_content,
    consume_tagline_paragraph,
    decompose_before_you_begin_section,
    extract_basic_information_tagline,
    get_sections_from_soup,
    get_subsections_from_sections,
    process_nofo_html,
    replace_chars,
    replace_links,
    resolve_section_heading_level,
    unwrap_heading_containers,
)


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
        raise ValidationError("That file does not contain a NOFO.", code="no_sections")
    return get_subsections_from_sections(
        sections, top_heading_level, consume_scoped_tagline=consume_scoped_tagline
    )


def process_document_content(
    html, *, section_parser=None, builder_import=False, extract_scoped_tagline=False
):
    """Normalize HTML and parse sections without a request, upload or ORM record.

    ``section_parser`` preserves the application's existing overridable section
    parser. Instruction attachment and consumer postprocessing stay with callers.
    Exceptions propagate unchanged for the caller to present or handle.
    """
    cleaned_content = replace_links(replace_chars(html))
    soup = BeautifulSoup(cleaned_content, "html.parser")
    if builder_import:
        from .introductory_page import capture_introductory_page

        soup = capture_introductory_page(soup)
    # Preserve the pre-pass before selecting the main section heading level.
    decompose_before_you_begin_section(soup)
    top_heading_level = resolve_section_heading_level(
        builder_import_content(soup) if builder_import else soup
    )
    imported_tagline = None
    if extract_scoped_tagline:
        unwrap_heading_containers(soup)
        imported_tagline = extract_basic_information_tagline(soup, top_heading_level)
    soup, instructions_tables = process_nofo_html(soup, top_heading_level)
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
