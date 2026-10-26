"""Builder adapter for the framework-independent content-processing core."""

import os

from bloom_nofos.error_helpers import AmbiguousHeadingHierarchyError
from django.conf import settings
from django.core.exceptions import ValidationError

from . import content_processing
from .content_processing import ProcessedDocumentContent  # compatibility re-export


def capture_debug_soup(soup):
    """Retain the application's existing DEBUG snapshot path and capture point."""
    debug_dir = os.path.join(settings.BASE_DIR, "nofos", "fixtures", "_temp")
    os.makedirs(debug_dir, exist_ok=True)
    output_file_path = os.path.join(debug_dir, "debug_output.html")
    with open(output_file_path, "w", encoding="utf-8") as file:
        file.write(str(soup))


def _application_call(function, *args, **kwargs):
    """Translate only core failures; application hook exceptions stay unchanged."""
    try:
        return function(*args, **kwargs)
    except content_processing.AmbiguousHeadingHierarchyError as error:
        raise AmbiguousHeadingHierarchyError(
            h2_text=error.h2_text,
            h1_text=error.h1_text,
            preceding_h2_count=error.preceding_h2_count,
        ) from error
    except content_processing.ContentProcessingError as error:
        raise ValidationError(str(error), code=error.code) from error


def get_sections_and_subsections_from_soup(
    soup, top_heading_level, *, consume_scoped_tagline=False, consume_metadata=False
):
    return _application_call(
        content_processing.get_sections_and_subsections_from_soup,
        soup,
        top_heading_level,
        consume_scoped_tagline=consume_scoped_tagline,
        consume_metadata=consume_metadata,
    )


def process_document_content(
    html,
    *,
    section_parser=None,
    builder_import=False,
    extract_scoped_tagline=False,
    editable_intro="generated"
):
    return _application_call(
        content_processing.process_document_content,
        html,
        section_parser=section_parser,
        builder_import=builder_import,
        extract_scoped_tagline=extract_scoped_tagline,
        editable_intro=editable_intro,
        debug_capture=capture_debug_soup if settings.DEBUG else None,
    )
