"""Internal content processing, separate from upload and persistence workflows.

This reuses Builder's NOFO-specific rules and parser objects, not a portable
interchange schema. See documentation/DOCUMENT_PROCESSING.md for dependencies.
"""

from dataclasses import dataclass

from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError

from .nofo import (
    decompose_before_you_begin_section,
    get_sections_from_soup,
    get_subsections_from_sections,
    process_nofo_html,
    replace_chars,
    replace_links,
    resolve_section_heading_level,
)


@dataclass
class ProcessedDocumentContent:
    """Existing mutable parser results; no copies or persistence are performed."""

    soup: BeautifulSoup
    sections: list
    instructions_tables: list


def get_sections_and_subsections_from_soup(soup, top_heading_level):
    """Extract content dictionaries, retaining the existing validation code."""
    sections = get_sections_from_soup(soup, top_heading_level)
    if not len(sections):
        raise ValidationError("That file does not contain a NOFO.", code="no_sections")
    return get_subsections_from_sections(sections, top_heading_level)


def process_document_content(html, *, section_parser=None):
    """Normalize HTML and parse sections without a request, upload or ORM record.

    ``section_parser`` preserves the application's existing overridable section
    parser. Instruction attachment and consumer postprocessing stay with callers.
    Exceptions propagate unchanged for the caller to present or handle.
    """
    cleaned_content = replace_links(replace_chars(html))
    soup = BeautifulSoup(cleaned_content, "html.parser")
    # Preserve the pre-pass before selecting the main section heading level.
    decompose_before_you_begin_section(soup)
    top_heading_level = resolve_section_heading_level(soup)
    soup, instructions_tables = process_nofo_html(soup, top_heading_level)
    if section_parser is None:
        section_parser = get_sections_and_subsections_from_soup
    sections = section_parser(soup, top_heading_level)
    return ProcessedDocumentContent(soup, sections, instructions_tables)
