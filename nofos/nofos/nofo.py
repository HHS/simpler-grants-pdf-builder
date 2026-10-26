"""
NOFO import pipeline: DOCX/HTML parsing, cleanup, sectioning, and metadata
suggestion.

Content normalization and parsing now live in content_processing.py and are
reexported here for existing callers. This module retains Word conversion,
application validation, metadata defaults, persistence and workflow helpers.
Update documentation/IMPORT_RULES.md when changing an import rule.
"""

import datetime
import json
import logging
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import mammoth
import markdown
import requests
from bloom_nofos.error_helpers import (
    AmbiguousHeadingHierarchyError,
    MistaggedHeadingError,
    StrictFormattingError,
)
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

from . import content_processing as _content_processing
from .content_processing import (
    BEFORE_YOU_BEGIN_HEADING_TEXT,
    DEFAULT_NOFO_OPPORTUNITY_NUMBER,
    END_NOTES_SECTION_NAME,
    INVALID_OPDIV_ACRONYMS,
    METADATA_BLOCK_LABELS,
    METADATA_LABEL_PATTERN,
    _change_existing_anchor_links_to_new_id,
    _get_classnames_for_font_weight_bold,
    _get_font_size_from_cssText,
    _heading_search_text,
    _is_before_you_begin_heading,
    _is_invalid_opdiv_placeholder,
    _looks_like_metadata_label,
    _looks_like_metadata_line,
    _metadata_block,
    _metadata_label_key,
    _suggest_by_startswith_string,
    add_body_if_no_body,
    add_em_to_de_minimis,
    add_endnotes_header_if_exists,
    add_missing_alt_text_to_imgs,
    add_strongs_to_soup,
    builder_import_content,
    clean_heading_tags,
    clean_table_cells,
    combine_consecutive_links,
    consume_tagline_paragraph,
    convert_table_first_row_to_header_row,
    convert_table_with_all_ths_to_a_regular_table,
    decompose_before_you_begin_section,
    decompose_empty_tags,
    decompose_instructions_tables,
    extract_basic_information_tagline,
    get_sections_from_soup,
    get_subsections_from_sections,
    is_acf_nofo_metadata,
    is_callout_box_table,
    is_h7,
    join_nested_lists,
    merge_funding_details_label_value_paragraphs,
    metadata_block_fields,
    normalize_whitespace_img_alt_text,
    preserve_bookmark_links,
    preserve_bookmark_targets,
    preserve_heading_links,
    preserve_table_heading_links,
    recognized_metadata_block,
    remove_google_tracking_info_from_links,
    rename_footnotes_heading_to_endnotes,
    repair_acf_required_alignment_lists,
    replace_chars,
    replace_links,
    sanitize_imported_text,
    suggest_nofo_opdiv,
    suggest_nofo_opportunity_number,
    unwrap_empty_elements,
    unwrap_heading_containers,
    unwrap_nested_lists,
)
from .document_processing import _application_call, capture_debug_soup
from .endnotes import (
    analyze_endnotes,
    convert_bracketed_endnotes,
    is_endnotes_heading,
    remove_duplicate_native_note_custom_marks,
)
from .import_transforms import (
    APPLICATION_CHECKLIST_CHILD_STYLE_MAP,
    normalize_strong1_runs,
    omit_leading_word_title,
    transform_word_document,
)
from .models import Nofo, Section, Subsection
from .nofo_markdown import MISSING_ALT_TEXT_ATTR, PRESERVE_BOOKMARK_TARGET_ATTR, md
from .pdf_metadata import normalize_pdf_metadata_value
from .policy_language import detect_policy_language_status, get_candidate_slots
from .templatetags.add_footnote_ids import add_footnote_ids
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
from .word_endnotes import preserve_word_note_cross_references
from .word_instruction_boxes import clean_instruction_boxes


def resolve_section_heading_level(soup):
    return _application_call(_content_processing.resolve_section_heading_level, soup)


def process_nofo_html(soup, top_heading_level):
    return _application_call(
        _content_processing.process_nofo_html,
        soup,
        top_heading_level,
        debug_capture=capture_debug_soup if settings.DEBUG else None,
    )


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


def parse_uploaded_file_as_html_string(
    uploaded_file,
    *,
    omit_leading_title=False,
    remove_instruction_boxes=True,
    review_warnings=None,
    list_review_warnings=None,
    preserve_empty_paragraphs=False,
):
    """
    Given an uploaded file, return a tuple of (raw HTML string, mammoth warning
    count). warning_count is always 0 for HTML-file uploads, since those never
    go through mammoth.
    Raise a ValidationError if invalid or missing.
    """
    if not uploaded_file:
        raise ValidationError("Oops! No fos uploaded.", code="no_file")

    content_type = uploaded_file.content_type

    if content_type == "text/html":
        # Decode the HTML file
        return uploaded_file.read().decode("utf-8"), 0

    elif (
        content_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        # Convert DOCX to HTML
        try:
            conversion_file = (
                omit_leading_word_title(uploaded_file)
                if omit_leading_title
                else uploaded_file
            )
            if remove_instruction_boxes:
                conversion_file, box_warnings = clean_instruction_boxes(conversion_file)
                if review_warnings is not None:
                    review_warnings.extend(box_warnings)
            # IMPORT-066: capture source numbering before Mammoth discards
            # marker formats, numbering identity and start/restart information.
            from .word_lists import prepare_word_lists

            conversion_file, list_plan = prepare_word_lists(conversion_file)
            conversion_file = normalize_strong1_runs(conversion_file)
            conversion_file = preserve_word_note_cross_references(conversion_file)
            if list_review_warnings is not None:
                list_review_warnings.extend(list_plan.warnings)
            doc_to_html_result = mammoth.convert_to_html(
                conversion_file,
                style_map="\n".join(
                    [
                        style_map_manager.get_style_map(),
                        APPLICATION_CHECKLIST_CHILD_STYLE_MAP,
                        list_plan.style_map,
                    ]
                ),
                transform_document=transform_word_document,
                ignore_empty_paragraphs=not preserve_empty_paragraphs,
            )
        except Exception as e:
            raise ValidationError(
                "NOFO Builder could not read this Word document.",
                code="docx_conversion",
            ) from e

        # Always compute warnings (not just in strict mode) so non-blocking
        # imports still record how many formatting issues mammoth flagged.
        # Strict mode only changes what happens next, not whether we look.
        warnings = [
            m.message
            for m in doc_to_html_result.messages
            if m.type == "warning"
            and all(
                style_ignore not in m.message
                for style_ignore in style_map_manager.get_styles_to_ignore()
            )
        ]

        # If strict mode, raise on any warnings - same condition as before
        if config.WORD_IMPORT_STRICT_MODE and warnings:
            raise StrictFormattingError(warnings)

        return list_plan.restore_html(doc_to_html_result.value), len(warnings)

    else:
        raise ValidationError(
            "Please import a .docx or HTML file.", code="unsupported_file_type"
        )


###########################################################
#################### UTILITY FUNCS ####################
###########################################################


###########################################################
##################### BUILD THE NOFO ######################
###########################################################


@transaction.atomic
def add_headings_to_document(
    document, SectionModel=Section, SubsectionModel=Subsection, *, extra_link_text=None
):
    new_ids = []
    # collect sections and subsections in arrays to facilitate bulk updating
    sections_to_update = []
    subsections_to_update = []
    # add counter because subheading titles can repeat, resulting in duplicate IDs
    counter = 1

    # add ids to all section headings
    for section in document.sections.all():
        section_id = (
            "section--before-you-begin"
            if getattr(section, "is_introduction", False)
            else "{}".format(slugify(section.name))
        )

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
    if extra_link_text is not None:
        for patterns in compiled_patterns:
            extra_link_text = patterns["href_pattern"].sub(
                'href="#{}"'.format(patterns["new_id"]), extra_link_text
            )
            extra_link_text = patterns["hash_pattern"].sub(
                "(#{})".format(patterns["new_id"]), extra_link_text
            )
        return extra_link_text


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
    # Check all names before creating any section, for every import consumer.
    long_headings = []
    for section in sections:
        for kind, items, model in (
            ("section", [section], SectionModel),
            ("subsection", section.get("subsections", []), SubsectionModel),
        ):
            limit = model._meta.get_field("name").max_length
            for item in items:
                name = item.get("name", "Section X" if kind == "section" else "")
                if len(name) > limit:
                    long_headings.append(
                        {
                            "heading_kind": kind,
                            "heading_order": item.get("order", ""),
                            "heading_text": name,
                            "max_length": limit,
                            "source_tag": item.get("source_tag", ""),
                            "search_text": item.get("search_text", name),
                            "section_name": section.get("name", "Section X"),
                            "section_order": section.get("order", ""),
                        }
                    )
    if long_headings:
        raise MistaggedHeadingError(headings=long_headings)

    def _get_document_field_name(SectionModel, document):
        """
        Return the field name that should be used to attach `document` to SectionModel.
        """
        # ContentGuideSection has this method
        if hasattr(SectionModel, "get_document_field_name_for"):
            return SectionModel.get_document_field_name_for(document)

        # NOFO Section has "nofo", Compare docs have "document"
        return "nofo" if hasattr(SectionModel, "nofo") else "document"

    def _raise_document_validation_error(validation_error, obj, heading_kind):
        name_errors = validation_error.error_dict.get("name", [])
        if any(error.code == "max_length" for error in name_errors):
            raise MistaggedHeadingError(
                heading_kind=heading_kind,
                heading_order=obj.order,
                heading_text=obj.name,
                max_length=obj._meta.get_field("name").max_length,
            ) from validation_error

        # Surface the field and rule that failed as plain sentences. str() on a
        # ValidationError with an error_dict renders the dict repr, which is not
        # something we can put in front of a NOFO writer.
        readable = []
        for field, errors in getattr(validation_error, "error_dict", {}).items():
            label = "Document" if field == "__all__" else field
            for error in errors:
                readable.extend(f"{label}: {message}" for message in error.messages)

        raise ValidationError(readable or [str(validation_error)]) from validation_error

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
            **({"role": section.get("role", "")} if SectionModel is Section else {}),
        )
        try:
            section_obj.full_clean()
        except ValidationError as e:
            _raise_document_validation_error(e, section_obj, "section")

        sections_to_create.append(section_obj)

    # Bulk create sections and retrieve them
    created_sections = SectionModel.objects.bulk_create(sections_to_create)
    # Map created sections to their names for subsection linking
    section_mapping = {section.name: section for section in created_sections}

    # Fetched once per document, not once per subsection. Only the live Nofo's
    # Subsection model carries this field - ContentGuideSubsection and
    # CompareSubsection don't, so this never runs for Composer or Compare.
    # Also gated on the feature flag itself: with it off, this prototype
    # should add zero extra work/behavior to a normal import, not just hide
    # the export UI.
    policy_language_slots = (
        get_candidate_slots()
        if hasattr(SubsectionModel, "policy_language_status")
        and config.HHS_NOFO_POLICY_EXPORT_ENABLED
        else None
    )

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

            if policy_language_slots is not None:
                status, matched_slot = detect_policy_language_status(
                    subsection_fields["name"],
                    subsection_fields["body"],
                    candidate_slots=policy_language_slots,
                )
                subsection_fields["policy_language_status"] = status
                subsection_fields["policy_language_slot"] = matched_slot

            subsection_obj = SubsectionModel(**subsection_fields)

            # If the SubsectionModel has an extract_variables method, then it is a
            # ContentGuideSubsection and the edit_mode should be determined
            if hasattr(SubsectionModel, "extract_variables"):
                variables = subsection_obj.extract_variables()
                body_contains_insert = "insert" in subsection_obj.body.lower()
                instructions_contains_insert = (
                    "insert" in subsection_obj.instructions.lower()
                )
                # If variables are detected, edit_mode = "variables"
                if variables:
                    subsection_obj.edit_mode = "variables"
                    serializable_variables = {
                        key: var.to_dict() for key, var in variables.items()
                    }
                    subsection_obj.variables = json.dumps(serializable_variables)
                # Subsection edit_mode = "full" if no variables, and:
                #   - subsection is optional OR
                #   - the word "insert" is present in the subsection body OR
                #   - the word "insert" is present in the instructions
                elif (
                    subsection_obj.optional
                    or body_contains_insert
                    or instructions_contains_insert
                ):
                    subsection_obj.edit_mode = "full"

                # Otherwise, default edit_mode = "locked" remains

            add_html_id_to_subsection(subsection_obj)
            try:
                subsection_obj.full_clean()
            except ValidationError as e:
                _raise_document_validation_error(e, subsection_obj, "subsection")

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


@transaction.atomic
def create_nofo(title, sections, opdiv, group="bloom"):
    nofo = Nofo(title=title, group=group)
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

    # _build_document creates sections and subsections with bulk_create, which
    # skips save() and so never reaches touch_updated(). nofo.save() above only
    # advances `updated` when a field on the NOFO itself changed, so re-import
    # can replace the entire body while leaving `updated` untouched. Anything
    # keyed on that timestamp (readability snapshots) would then replay a
    # measurement of content that no longer exists.
    nofo.touch_updated()
    nofo.refresh_from_db()
    return nofo


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


# Href values that name no destination at all. "" covers both an empty href
# and a whitespace-only one (the check strips first); "about:blank" is what
# Word and Google Docs write when a hyperlink in the source document was never
# given a target. Neither is a broken link *into* the NOFO, so both are
# reported with the external links -- the other category of link that points
# outside the NOFO -- and neither is ever requested over HTTP.
INVALID_LINK_DESTINATIONS = ("", "about:blank")
INVALID_LINK_ERROR = "No link destination in the source document"


def _is_invalid_link_destination(url):
    """True for an href value that names no destination. None means no href attribute at all, which is_dangling_link_anchor() decides on instead, since it needs the rest of the tag to tell a link from a bookmark target."""
    if url is None:
        return False

    return url.strip().lower() in INVALID_LINK_DESTINATIONS


def is_dangling_link_anchor(tag):
    """
    True when an `<a>` is a link a reader can see but that goes nowhere.

    Two shapes count:
      - an `href` that names no destination ("", whitespace, "about:blank")
      - no `href` attribute at all, which is what martor's sanitizer leaves
        behind when it strips a disallowed scheme such as "bookmark://"

    Two shapes deliberately do not:
      - no visible text: an artifact a designer can neither see nor click, so
        there is nothing to report and nothing to fix
      - no `href` but carrying an `id`/`name`: that is a bookmark *target*,
        not a link, and some targets keep their original visible label (see
        `preserve_bookmark_links` below, and the "category 2b" tests in
        tests_nofos/test_templatetags.py). Text alone isn't enough to call
        an href-less anchor broken.

    Shared with `templatetags/add_classes_to_links.py` so the inline tooltip
    in the editor body and the external-links page agree on what counts.
    """
    if getattr(tag, "name", None) != "a":
        return False

    if not tag.get_text(strip=True):
        return False

    href = tag.get("href")
    if href is None:
        return not (tag.get("id") or tag.get("name"))

    return _is_invalid_link_destination(href)


def _update_link_statuses(all_links):
    logging.basicConfig(
        level=logging.WARNING
    )  # You can adjust the level to DEBUG, ERROR, etc.
    logger = logging.getLogger(__name__)

    def check_link_status(link):
        if link.get("invalid_destination"):
            # Nothing to request: there is no destination to resolve.
            return link

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


END_NOTES_SECTION_HTML_ID = "endnotes"

# Matches the "docx-style" endnote id/href convention this app already
# recognizes elsewhere (see get_footnote_type in templatetags/utils), so the
# link-numbering/backlink logic that already runs on subsection bodies keeps
# working on this content unmodified.
END_NOTES_PLACEHOLDER_BODY = """<ol>
 <li id="endnote-1" tabindex="-1">
  <p>
   Placeholder paragraph text goes here. Replace this with your citation or note.
   <a href="#endnote-ref-1">
    ↑
   </a>
  </p>
 </li>
 <li id="endnote-2" tabindex="-1">
  <p>
   Placeholder paragraph text goes here.
   <a href="https://example.com">
    Placeholder link text goes here
   </a>
   .
   <a href="#endnote-ref-2">
    ↑
   </a>
  </p>
 </li>
</ol>"""


def nofo_has_end_notes_section(nofo):
    return nofo.sections.filter(html_id=END_NOTES_SECTION_HTML_ID).exists()


def nofo_has_appendix_section(nofo):
    return nofo.sections.filter(html_id="appendix").exists()


def get_subsection_action_availability(nofo):
    """Present existing status restrictions; action views still enforce access."""
    return {
        "can_edit_subsections": not nofo.archived
        and nofo.status != "cancelled"
        and (nofo.status != "published" or bool(nofo.modifications)),
        "can_delete_subsections": not nofo.archived and nofo.status == "draft",
    }


def get_nofo_action_links(nofo):
    # Canonical action builders
    def _link_compare(nofo):
        return {
            "key": "compare",
            "label": "Compare NOFO",
            "href": reverse_lazy("compare:compare_duplicate", args=[nofo.pk]),
            "external": True,
        }

    def _link_duplicate(nofo):
        return {
            "key": "duplicate",
            "label": "Duplicate NOFO",
            "href": reverse_lazy("nofos:nofo_duplicate", args=[nofo.pk]),
        }

    def _link_export(nofo):
        return {
            "key": "export",
            "label": "Export Word doc",
            "href": reverse_lazy("nofos:nofo_export", args=[nofo.pk]),
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

    def _link_add_end_notes(nofo):
        return {
            "key": "add_end_notes",
            "label": "Add Endnotes",
            "href": reverse_lazy("nofos:section_add_end_notes", args=[nofo.pk]),
        }

    def _link_add_appendix(nofo):
        return {
            "key": "add_appendix",
            "label": "Add Appendix",
            "href": reverse_lazy("nofos:section_add_appendix", args=[nofo.pk]),
            "method": "post",
        }

    # Status → allowed actions
    _STATUS_ACTIONS = {
        "draft": (
            "find_replace",
            "compare",
            "duplicate",
            "add_end_notes",
            "add_appendix",
            "reimport",
            "export",
            "delete",
        ),
        "active": (
            "find_replace",
            "compare",
            "duplicate",
            "add_end_notes",
            "add_appendix",
            "reimport",
            "export",
        ),
        "ready-for-qa": (
            "find_replace",
            "compare",
            "duplicate",
            "add_end_notes",
            "add_appendix",
            "reimport",
            "export",
        ),
        "review": (
            "find_replace",
            "compare",
            "duplicate",
            "add_end_notes",
            "add_appendix",
            "export",
        ),
        "doge": (
            "find_replace",
            "compare",
            "duplicate",
            "add_end_notes",
            "add_appendix",
            "export",
        ),  # Deputy Secretary review
        "published": ("export",),
        "paused": (
            "find_replace",
            "compare",
            "duplicate",
            "add_end_notes",
            "add_appendix",
            "export",
        ),
        "cancelled": ("export",),
    }

    status = (nofo.status or "").lower()
    actions = _STATUS_ACTIONS.get(status, ())

    # Assemble in order
    link_builders = {
        "find_replace": lambda: _link_find_replace(nofo),
        "compare": lambda: _link_compare(nofo),
        "duplicate": lambda: _link_duplicate(nofo),
        "add_end_notes": lambda: _link_add_end_notes(nofo),
        "add_appendix": lambda: _link_add_appendix(nofo),
        "reimport": lambda: _link_reimport(nofo),
        "export": lambda: _link_export(nofo),
        "delete": lambda: _link_delete(nofo),
    }

    links = []
    for key in actions:
        # A NOFO can only ever have one Endnotes section.
        if key == "add_end_notes" and nofo_has_end_notes_section(nofo):
            continue
        if key == "add_appendix" and (nofo.archived or nofo_has_appendix_section(nofo)):
            continue

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

    Links that name no destination at all are included here too, flagged with 'invalid_destination': an empty or whitespace-only href, "about:blank", or no href attribute (see is_dangling_link_anchor). None of them is an anchor into the NOFO, so they belong in this list rather than in find_broken_links(), and none is ever requested over HTTP because there is no destination to request. Anchors with no visible text, and href-less bookmark *targets* carrying an id/name, are skipped.

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
            - 'invalid_destination' (bool): True if the link has no destination at all (empty/whitespace href, "about:blank", or no href attribute), in which case 'url' is the literal href (""  when absent), 'error' is pre-filled, and no HTTP request is made.
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
                href = link.get("href")
                # "" when the anchor has no href attribute at all, so the row
                # reports the literal (missing) destination rather than a "#"
                # placeholder that was never in the document.
                url = href if href is not None else ""

                if is_dangling_link_anchor(link):
                    all_links.append(
                        {
                            "url": url,
                            "link_text": link.get_text(),
                            "domain": "",
                            "section": section,
                            "subsection": subsection,
                            "status": "",
                            "error": INVALID_LINK_ERROR,
                            "redirect_url": "",
                            "invalid_destination": True,
                        }
                    )
                elif url.startswith("http"):
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
                                "invalid_destination": False,
                            }
                        )

    if with_status:
        _update_link_statuses(all_links)

    return all_links


def find_broken_links(nofo):
    """
    Identifies and returns a list of broken links within a given Nofo.

    A broken link is defined as an anchor (`<a>`) element whose `href` attribute value starts with "#" (eg. "#h.", "#id.", "#_heading"),
    "/", "bookmark", or "file://", and which does not resolve to an id that exists in the NOFO.
    This means that someone created an internal link to a header, and then later the header was deleted or otherwise
    modified so the original link doesn't point anywhere.

    Links to destinations *outside* the NOFO are deliberately not counted here, even when they are a problem:
    Google Docs URLs (`https://docs.google.com/...`) are ordinary external links and are reported by
    find_external_links(), and links that name no destination at all (an empty or whitespace-only href,
    "about:blank", or no href attribute) are reported there too as invalid destinations. None of them is
    an internal anchor, so calling them broken internal links was both misleading and, for Google Docs,
    a duplicate of the external-link report.

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
                if (
                    nofo.before_you_begin == "none"
                    and not nofo.has_imported_introduction
                    and nofo.number != "hrsa-application-guide"
                    and link.get("href") == "#section--before-you-begin"
                ):
                    # The public renderer intentionally flattens this disabled
                    # generated destination; it is not a broken authored link.
                    continue
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


FOOTNOTE_HEADING_TAGS = ("h2", "h3", "h4", "h5", "h6", "h7")


def find_endnote_issues(nofo):
    """Recheck saved content without modifying records or their link destinations.

    Reconstruct the document's heading order on a disposable HTML tree. Location
    metadata belongs only to this tree, so warnings follow subsequent edits without
    a migration, persisted import diagnostics, or rewriting legacy content.

    Runs at view time (see views.py), not at import - not itself one of the
    IMPORT-NNN rules in documentation/IMPORT_RULES.md, but reuses IMPORT-050's
    detection logic (endnotes.py::analyze_endnotes) and is documented in that
    file's "Related, But Out of Scope" section since the two are tightly coupled.
    """
    soup = BeautifulSoup("", "html.parser")
    locations = {}

    def append_fragment(fragment, section, subsection=None):
        key = str(len(locations))
        locations[key] = (section, subsection)
        for node in list(fragment.contents):
            if isinstance(node, Tag):
                node["data-endnote-location"] = key
            soup.append(node.extract())

    for section in nofo.sections.all().order_by("order"):
        heading = soup.new_tag("h1")
        heading.string = section.name
        if section.html_id:
            heading["id"] = section.html_id
        fragment = BeautifulSoup("", "html.parser")
        fragment.append(heading)
        append_fragment(fragment, section)
        for subsection in section.subsections.all().order_by("order"):
            fragment = BeautifulSoup("", "html.parser")
            if subsection.tag in FOOTNOTE_HEADING_TAGS and subsection.name:
                heading = soup.new_tag(subsection.tag)
                heading.string = subsection.name
                if subsection.html_id:
                    heading["id"] = subsection.html_id
                fragment.append(heading)
            body = BeautifulSoup(
                add_footnote_ids(
                    markdown.markdown(subsection.body or "", extensions=["extra"])
                ),
                "html.parser",
            )
            for node in list(body.contents):
                fragment.append(node.extract())
            append_fragment(fragment, section, subsection)

    results = []
    content_locations = set()
    for issue in analyze_endnotes(soup, check_content=True):
        tag = issue["tag"]
        location = (
            tag
            if tag.has_attr("data-endnote-location")
            else tag.find_parent(attrs={"data-endnote-location": True})
        )
        if location is None:
            continue
        section, subsection = locations[location["data-endnote-location"]]
        if issue["code"] == "content-format":
            key = location["data-endnote-location"]
            if key in content_locations:
                continue
            content_locations.add(key)
        # Basic information is represented by the metadata table rather than its
        # imported subsection, and unnamed subsections have no editor anchor.
        # In either case, link to the containing section, which is always rendered.
        subsection_is_linkable = (
            subsection and subsection.name != "Basic information" and subsection.html_id
        )
        results.append(
            {
                "section": section,
                "subsection": subsection,
                "location_html_id": (
                    subsection.html_id if subsection_is_linkable else section.html_id
                ),
                "message": issue["message"],
                "code": issue["code"],
                "excerpt": issue.get("excerpt", ""),
            }
        )
    return results


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
            {'id': 'nofo-edit--basic-information', 'name': 'Basic information'},
            {'id': 'section-1-html-id', 'name': 'Section 1 Name'},
            ...
        ]
    """
    if nofo.sections.count() == 0:
        return []

    side_nav_links = [
        {"id": "nofo-edit--basic-information", "name": "Basic information"}
    ]

    for section in nofo.sections.all().order_by("order"):
        side_nav_links.append({"id": section.html_id, "name": section.name})

    return side_nav_links


###########################################################
#################### SUGGEST VAR FUNCS ####################
###########################################################


# These are the fields owned by a structured Metadata block. Tagline and
# assistance-listing labels deliberately retain their independent legacy path.


# Label variants seen in real NOFOs today. A future HHS Word template may add a
# dedicated, single label for this - once confirmed, prefer matching that first.
ASSISTANCE_LISTING_NUMBER_LABELS = (
    "Assistance Listing Number:",
    "Assistance Listing:",
    "Federal Assistance Listing Number:",
    "Federal Assistance Listing:",
)

# CFDA numbers are 2 digits, a period, then up to 3 more characters (eg, 93.884,
# 12.ABC per SGG's own example). Matches just the code, not any trailing title
# text (eg, "93.318: Protecting and Improving Health Globally...") - the
# trailing (?!...) boundary rejects a 4th alphanumeric character rather than
# silently truncating a malformed, overlong code (eg, "93.8840", "12.ABCD").
ASSISTANCE_LISTING_NUMBER_PATTERN = re.compile(
    r"^\s*(\d{2}\.[A-Za-z0-9]{1,3})(?![A-Za-z0-9])"
)


def suggest_nofo_assistance_listing_number(soup):
    if not config.HHS_NOFO_ASSISTANCE_LISTING_ENABLED:
        return ""

    for label in ASSISTANCE_LISTING_NUMBER_LABELS:
        suggestion = _suggest_by_startswith_string(soup, label)
        if suggestion:
            match = ASSISTANCE_LISTING_NUMBER_PATTERN.match(suggestion)
            if match:
                return match.group(1)

    return ""


def suggest_nofo_application_deadline(soup):
    nofo_application_deadline_default = "[WEEKDAY, MONTH DAY, YEAR]"

    suggestion = _suggest_by_startswith_string(soup, "Application Deadline:")
    return suggestion or nofo_application_deadline_default


def suggest_nofo_cover(nofo_theme):
    if any(
        prefix in nofo_theme.lower()
        for prefix in ["acf-", "acl-", "cdc-", "hrsa-", "nih-"]
    ):
        return "nofo--cover-page--text"

    return "nofo--cover-page--medium"


def suggest_nofo_before_you_begin(
    nofo_group, nofo_theme="", introductory_page_family="legacy"
):
    if "hrsa-" in nofo_theme.lower():
        return "full" if introductory_page_family == "get_started" else "hrsa"

    if nofo_group == "nih":
        return "era"

    return "full"


def suggest_nofo_theme(nofo_number, opdiv=""):
    opdiv_lower = (opdiv or "").lower()
    if "national institutes of health" in opdiv_lower or re.search(
        r"\bnih\b", opdiv_lower
    ):
        return "portrait-nih-white"

    if "health resources and services administration" in opdiv_lower or re.search(
        r"\bhrsa\b", opdiv_lower
    ):
        return "portrait-hrsa-white"

    if (
        "substance abuse and mental health services administration" in opdiv_lower
        or re.search(r"\bsamhsa\b", opdiv_lower)
    ):
        return "portrait-samhsa-white"

    if "administration for community living" in opdiv_lower or re.search(
        r"\bacl\b", opdiv_lower
    ):
        return "portrait-acl-white"

    if "cdc-" in nofo_number.lower():
        return "portrait-cdc-blue"

    if is_acf_nofo_metadata(nofo_number, opdiv):
        return "portrait-acf-white"

    if "acl-" in nofo_number.lower():
        return "portrait-acl-white"

    if "cms-" in nofo_number.lower():
        return "portrait-cms-white"

    if "ihs-" in nofo_number.lower():
        return "portrait-ihs-white"

    if re.search(r"(?:^|-)hrsa-", nofo_number.lower()):
        return "portrait-hrsa-white"

    # NOFO numbers with "RFA" are also CDC, but do this check last
    if "rfa-" in nofo_number.lower():
        return "portrait-cdc-blue"

    return "portrait-nih-white"


def suggest_nofo_title(soup):
    nofo_title_default = "NOFO: {}".format(
        datetime.datetime.now().replace(microsecond=0).isoformat().replace("T", " ")
    )

    suggestion = _suggest_by_startswith_string(soup, "Opportunity Name:")
    return suggestion or nofo_title_default


def suggest_nofo_agency(soup):
    suggestion = _suggest_by_startswith_string(soup, "Agency:")
    return suggestion or ""


def suggest_nofo_subagency(soup):
    suggestion = _suggest_by_startswith_string(soup, "Subagency:")
    return suggestion or ""


def suggest_nofo_subagency2(soup):
    suggestion = _suggest_by_startswith_string(soup, "Subagency2:")
    return suggestion or ""


# Word templates leave a ruled blank for the tagline, which converts to a run of
# underscores. Sanitizing keeps them (they are ordinary printable characters), so
# the placeholder would otherwise be saved and rendered as the tagline itself.
TAGLINE_UNDERSCORE_PLACEHOLDER_PATTERN = re.compile(r"[\s_]*_[\s_]*")


def _is_underscore_placeholder(value):
    """True for a value made up only of underscores (and whitespace)."""
    return bool(value) and bool(TAGLINE_UNDERSCORE_PLACEHOLDER_PATTERN.fullmatch(value))


def suggest_nofo_tagline(soup):
    suggestion = _suggest_by_startswith_string(soup, "Tagline:")

    # Scoped to the tagline on purpose: other metadata fields have no reason to
    # treat underscores as a blank, and IMPORT-041 otherwise keeps them as-is.
    if _is_underscore_placeholder(suggestion):
        return ""

    return suggestion or ""


def suggest_nofo_author(soup):
    suggestion = _suggest_by_startswith_string(soup, "Metadata Author:")
    return normalize_pdf_metadata_value(suggestion)


def suggest_nofo_subject(soup):
    suggestion = _suggest_by_startswith_string(soup, "Metadata Subject:")
    return normalize_pdf_metadata_value(suggestion)


def suggest_nofo_keywords(soup):
    suggestion = _suggest_by_startswith_string(soup, "Metadata Keywords:")
    return normalize_pdf_metadata_value(suggestion)


def suggest_nofo_cover_image(nofo):
    cover_img = "img/cover-img/{}.jpg".format(nofo.number.lower())
    if os.path.exists(os.path.join(settings.STATIC_ROOT, cover_img)):
        return cover_img

    if "pepfar" in nofo.title.lower():
        return "img/cover-img/cdc-pepfar.jpg"

    return ""


def suggest_all_nofo_fields(
    nofo, soup, *, first_time_import=None, imported_tagline=None
):
    from .introductory_page import introductory_family_from_soup

    # Import views know whether this is a new record, even when a legacy record
    # still has a blank/default opportunity number.
    if first_time_import is None:
        first_time_import = (
            not nofo.number or nofo.number == DEFAULT_NOFO_OPPORTUNITY_NUMBER
        )
    if first_time_import:
        nofo.introductory_page_family = introductory_family_from_soup(soup)
        from .introductory_page import imported_introduction

        if imported_introduction(soup):
            nofo.introductory_content_mode = "imported"

    nofo_number = suggest_nofo_opportunity_number(soup)  # guess the NOFO number
    nofo.number = nofo_number
    # Only overwrite on a real suggestion: a disabled flag or an unrecognized
    # label both return "", and re-import must not erase an existing value.
    suggested_assistance_listing_number = suggest_nofo_assistance_listing_number(soup)
    if suggested_assistance_listing_number:
        nofo.assistance_listing_number = suggested_assistance_listing_number
    nofo.application_deadline = suggest_nofo_application_deadline(
        soup
    )  # guess the NOFO application deadline
    nofo.opdiv = suggest_nofo_opdiv(soup)  # guess the NOFO OpDiv
    nofo.agency = suggest_nofo_agency(soup)  # guess the NOFO Agency
    nofo.subagency = suggest_nofo_subagency(soup)  # guess the NOFO Subagency
    nofo.subagency2 = suggest_nofo_subagency2(soup)  # guess NOFO Subagency 2
    nofo.tagline = (
        suggest_nofo_tagline(soup) if imported_tagline is None else imported_tagline
    )
    nofo.author = suggest_nofo_author(soup)  # guess the NOFO author
    nofo.subject = suggest_nofo_subject(soup)  # guess the NOFO subject
    nofo.keywords = suggest_nofo_keywords(soup)  # guess the NOFO keywords

    preserve_hrsa_image = not first_time_import and "hrsa-" in nofo.theme.lower()
    if not nofo.cover_image and not preserve_hrsa_image:
        nofo.cover_image = suggest_nofo_cover_image(nofo)  # guess NOFO cover image

    nofo_title = suggest_nofo_title(soup)  # guess the NOFO title
    # reset title only if there is a title and it's not the default title, or current nofo.title is empty
    if nofo_title:
        if not nofo.title or not nofo_title.startswith("NOFO: "):
            nofo.title = nofo_title

    # do not reset these during import
    if first_time_import:
        nofo.theme = suggest_nofo_theme(
            nofo.number, opdiv=nofo.opdiv
        )  # guess the NOFO theme
    if first_time_import:
        nofo.cover = suggest_nofo_cover(nofo.theme)  # guess the NOFO cover
    if first_time_import:
        nofo.before_you_begin = suggest_nofo_before_you_begin(
            nofo.group, nofo.theme, nofo.introductory_page_family
        )  # guess the NOFO "Before you begin" page


###########################################################
#################### MUTATE HTML FUNCS ####################
###########################################################


def _get_all_id_attrs_for_nofo(nofo):
    """
    Extracts all unique HTML 'id' attributes from a given Nofo.
    This includes 'id' attributes defined in the 'html_id' field of sections and subsections,
    as well as any 'id' attributes found within the HTML content of the subsection.body.
    """
    # Initialize a set to collect all unique ids
    all_ids = set()
    if (
        nofo.has_imported_introduction
        or nofo.before_you_begin != "none"
        or nofo.number == "hrsa-application-guide"
    ):
        from .introductory_page import INTRO_ANCHOR

        all_ids.add(INTRO_ANCHOR)

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
                    r"^(instructions for nofo writers|instructions for new nofo team|instructions for template managers)",
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


# Matches a short "field name" label, eg "Award date" or "Anticipated start date" -
# not a full sentence like "Note" in "Note: applications received after this date
# won't be reviewed" would still match (that's fine, it's field-name-shaped too), but
# a long sentence with a stray colon in it won't.
KEY_DATES_FIELD_NAME_WORD_RE = re.compile(r"^[A-Za-z][A-Za-z'-]*$")


def add_line_breaks_to_key_dates_values(sections):
    """
    This function accepts a list of section dicts, _not_ Section objects, and mutates
    the paragraph tags inside them in place.

    The "Key dates" callout box is a narrow, right-aligned component, and its "field
    name: value" paragraphs (eg, "Award date: 00/00/0000") can wrap in the middle of
    the value there, breaking a date format like "00/00/0000" across two lines.

    Within the "Key dates" callout box only, this inserts a line break right after the
    colon in any such "field name:" paragraph, so the value always starts on its own
    line. A paragraph with no field-name colon (eg, a plain descriptive sentence ending
    in a period) is left untouched, as is every other section/subsection in the NOFO.

    Args:
        sections (list of dict): A list of section dictionaries, where each section may
            contain a "subsections" (list of dict) key. Each subsection's "body" is
            either a single BeautifulSoup Tag (a callout box's extracted cell) or a
            list of BeautifulSoup Tag objects (an ordinary subsection) - see
            `get_subsections_from_sections`.

    Side Effects:
        - Modifies the "Key dates" subsection's paragraph tags in place, splitting a
          "field name:" text node into a "field name:" node, a new <br> tag, and the
          remaining text.
    """

    def _looks_like_field_name(text):
        # Real field names are short labels (eg, "Award date", "Anticipated start
        # date"), not a full clause. 4 words comfortably covers realistic field
        # names while still excluding longer sentence fragments.
        words = text.strip().split()
        return 1 <= len(words) <= 4 and all(
            KEY_DATES_FIELD_NAME_WORD_RE.match(word) for word in words
        )

    def _get_paragraphs(body):
        if hasattr(body, "find_all"):
            # a callout box's body is a single extracted <div> cell
            return body.find_all("p")
        # an ordinary subsection's body is a list of top-level tags
        return [tag for tag in body if getattr(tag, "name", None) == "p"]

    for section in sections:
        for subsection in section.get("subsections", []):
            if (subsection.get("name") or "").strip().casefold() != "key dates":
                continue

            for paragraph in _get_paragraphs(subsection["body"]):
                if paragraph.find("br"):
                    continue

                first_text_with_colon = next(
                    (
                        node
                        for node in paragraph.contents
                        if isinstance(node, NavigableString) and ":" in node
                    ),
                    None,
                )
                if first_text_with_colon is None:
                    continue

                before, _, after = str(first_text_with_colon).partition(":")
                if not _looks_like_field_name(before):
                    continue

                label_node = NavigableString(before.strip() + ":")
                first_text_with_colon.replace_with(label_node)

                br_tag = paragraph.new_tag("br")
                label_node.insert_after(br_tag)
                if after.strip():
                    br_tag.insert_after(after.strip())


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
