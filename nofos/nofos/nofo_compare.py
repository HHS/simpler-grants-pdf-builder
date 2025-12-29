import re
from dataclasses import dataclass, field
from typing import List, Literal, Optional

from bloom_nofos.html_diff import has_diff, html_diff
from bs4 import BeautifulSoup
from django.utils.html import escape
from martor.utils import markdownify

from .models import Nofo, Section
from .nofo import decompose_empty_tags


@dataclass
class SubsectionDiff:
    name: str
    status: str  # "MATCH", "UPDATE", "ADD", "DELETE"
    comparison_type: Literal["body", "name", "none", "diff_strings"] = "body"
    section: Optional[Section] = None
    old_name: Optional[str] = ""
    new_name: Optional[str] = ""
    old_value: Optional[str] = ""
    new_value: Optional[str] = ""
    diff: Optional[str] = None
    old_diff: Optional[str] = None  # just the diff for the "old" document
    new_diff: Optional[str] = None  # just the diff for the "new" document
    diff_strings: List[str] = field(default_factory=list)
    tag: Optional[str] = ""  # metadata diffs don't have a tag (eg, nofo.number)
    html_id: Optional[str] = ""  # metadata diffs don't have an id
    index_number: Optional[int] = 0  # used for numbering the changes in the final diff


def find_matching_subsection(new_subsection, old_subsections, matched_ids):
    """
    Attempts to find an unmatched old subsection that matches the given new subsection.
    Returns the matched subsection or None.
    """
    for old_subsection in old_subsections:
        if old_subsection.id in matched_ids:
            continue
        if new_subsection.is_matching_subsection(old_subsection):
            return old_subsection
    return None


def get_subsection_name_or_order(subsection):
    return subsection.name or "(#{})".format(subsection.order)


def add_content_guide_comparison_metadata(
    result: SubsectionDiff, subsection
) -> SubsectionDiff:
    """
    Adds comparison_type and diff_strings to the result dict if present on the subsection.
    Returns a new dict with those keys added if applicable.
    """
    if hasattr(subsection, "comparison_type"):
        result.comparison_type = subsection.comparison_type or "body"
        result.diff_strings = subsection.diff_strings or []
    return result


def result_match(original_subsection):
    name = get_subsection_name_or_order(original_subsection)
    result = SubsectionDiff(
        name=name,
        section=original_subsection.section,
        old_name=name,
        new_name=name,
        status="MATCH",
        old_value=original_subsection.body,
        new_value=original_subsection.body,
        diff="",  # explicitly setting for template compatibility
        tag=original_subsection.tag,
        html_id=original_subsection.html_id,
    )
    return add_content_guide_comparison_metadata(result, original_subsection)


def result_update(original_subsection, new_subsection):
    result = SubsectionDiff(
        name=get_subsection_name_or_order(original_subsection),
        section=original_subsection.section,
        old_name=get_subsection_name_or_order(original_subsection),
        new_name=get_subsection_name_or_order(new_subsection),
        status="UPDATE",
        old_value=original_subsection.body,
        new_value=new_subsection.body,
        diff=html_diff(
            markdownify(original_subsection.body), markdownify(new_subsection.body)
        )
        or "",
        tag=new_subsection.tag,
        html_id=new_subsection.html_id,
    )
    return add_content_guide_comparison_metadata(result, original_subsection)


def result_merged_update(
    name, old_value, new_value, old_subsection, new_subsection, html_id
):
    return SubsectionDiff(
        name=name,
        comparison_type=old_subsection.comparison_type,
        section=old_subsection.section,
        old_name=re.sub(r"<.*?>", "", old_subsection.name),
        new_name=re.sub(r"<.*?>", "", new_subsection.name),
        status="UPDATE",
        old_value=old_value,
        new_value=new_value,
        diff=html_diff(markdownify(old_value), markdownify(new_value)),
        diff_strings=old_subsection.diff_strings or [],
        html_id=html_id,
    )


def result_add(new_subsection):
    return SubsectionDiff(
        name=get_subsection_name_or_order(new_subsection),
        section=new_subsection.section,
        old_name="",
        new_name=get_subsection_name_or_order(new_subsection),
        status="ADD",
        old_value="",
        new_value=new_subsection.body,
        diff=html_diff("", markdownify(new_subsection.body)) or "",
        tag=new_subsection.tag,
        html_id=new_subsection.html_id,
    )


def result_delete(old_subsection):
    result = SubsectionDiff(
        name=html_diff(get_subsection_name_or_order(old_subsection), ""),
        section=old_subsection.section,
        old_name=get_subsection_name_or_order(old_subsection),
        new_name="",
        status="DELETE",
        old_value=old_subsection.body,
        new_value="",
        diff=html_diff(markdownify(old_subsection.body), "") or "",
        tag=old_subsection.tag,
        html_id=old_subsection.html_id,
    )
    return add_content_guide_comparison_metadata(result, old_subsection)


def contains_required_strings(diff_strings, body):
    """
    Returns True if all required strings (normalized) are found in the normalized body.
    """

    def normalize_whitespace(text):
        return re.sub(r"\s+", " ", text.strip())

    normalized_body = normalize_whitespace(body).lower()
    for string in diff_strings:
        if normalize_whitespace(string).lower() not in normalized_body:
            return False
    return True


def compare_sections(old_section, new_section):
    """
    Compares all subsections in a pair of NOFO sections.
    Returns a dict with:
        - section name
        - comparison result for each subsection
    """
    # Get all subsections for comparison
    new_subsections = list(new_section.subsections.all())
    old_subsections = list(old_section.subsections.all()) if old_section else []

    matched_subsections = set()
    subsections = []

    old_index = 0
    new_index = 0

    while new_index < len(new_subsections):
        new_sub = new_subsections[new_index]

        # Try to find a matching old subsection
        matched_old = find_matching_subsection(
            new_sub, old_subsections, matched_subsections
        )

        if matched_old:
            # Flush any unmatched old subsections that come BEFORE this match
            while (
                old_index < len(old_subsections)
                and old_subsections[old_index].id != matched_old.id
            ):
                old_sub = old_subsections[old_index]
                if old_sub.id not in matched_subsections:
                    subsections.append(result_delete(old_sub))
                    matched_subsections.add(old_sub.id)
                old_index += 1

            # Now handle the matched pair
            matched_subsections.update([new_sub.id, matched_old.id])
            if has_diff(
                html_diff(
                    markdownify(matched_old.body.strip()),
                    markdownify(new_sub.body.strip()),
                )
            ):
                subsections.append(result_update(matched_old, new_sub))
            else:
                subsections.append(result_match(matched_old))

            old_index += 1
        else:
            # ADD (no matching old subsection)
            subsections.append(result_add(new_sub))
            matched_subsections.add(new_sub.id)

        new_index += 1

    # Flush any remaining unmatched old subsections as DELETE
    while old_index < len(old_subsections):
        old_sub = old_subsections[old_index]
        if old_sub.id not in matched_subsections:
            subsections.append(result_delete(old_sub))
            matched_subsections.add(old_sub.id)
        old_index += 1

    return {
        "name": new_section.name,
        "html_id": new_section.html_id,
        "subsections": subsections,
    }


def merge_renamed_subsections(
    subsections: list[SubsectionDiff],
) -> list[SubsectionDiff]:
    """
    Detects ADD + DELETE pairs in a section that are likely renames and merges them into an UPDATE.
    This improves diff quality when only a subsection title has changed (and body remains the same or similar).
    """
    merged = []
    i = 0

    while i < len(subsections):
        current = subsections[i]
        next_item = subsections[i + 1] if i + 1 < len(subsections) else None

        if current.status == "ADD" and next_item and next_item.status == "DELETE":
            new_body = (current.new_value or "").strip()
            old_body = (next_item.old_value or "").strip()
            new_name = current.name
            old_name = re.sub(r"<.*?>", "", next_item.name)  # strip tags
            html_id = current.html_id  # use the old html_id

            heading_diff = html_diff(old_name, new_name)

            is_rename_only = old_body == new_body

            # look for if there is shared text in the header (remove del and ins and keep remainder)
            # "Shared heading" means at least 3 contiguous characters of overlap, case-sensitive
            remaining_text = re.sub(r"<(del|ins)>.*?</\1>", " ", heading_diff or "")
            has_shared_heading = bool(re.search(r"[A-Za-z0-9]{3,}", remaining_text))

            if is_rename_only or has_shared_heading:
                merged.append(
                    result_merged_update(
                        name=heading_diff or new_name,
                        old_value=old_body,
                        new_value=new_body,
                        old_subsection=next_item,
                        new_subsection=current,
                        html_id=html_id,
                    )
                )
                i += 2
                continue

        # Normal case: keep the current item
        merged.append(current)
        i += 1

    return merged


def apply_comparison_types(subsections: list[SubsectionDiff]) -> list[SubsectionDiff]:
    def normalize(text):
        return re.sub(r"\s+", " ", text.strip()).lower()

    def name_modified(item: SubsectionDiff):
        return "<del>" in item.name or "<ins>" in item.name

    results = []
    for item in subsections:
        comparison_type = item.comparison_type

        if comparison_type == "none":
            continue

        if not comparison_type or item.status in ["ADD", "MATCH"]:
            results.append(item)
            continue

        if item.status == "DELETE":
            if comparison_type == "name":
                item.diff = "—"

            elif comparison_type == "diff_strings":
                item.diff = "<ul>"
                for s in item.diff_strings:
                    item.diff += f"<li><del>{escape(s)}</del></li>"
                item.diff += "</ul>"

            results.append(item)
            continue

        if item.status == "UPDATE":
            if comparison_type == "name":
                if not name_modified(item):
                    item.status = "MATCH"
                item.diff = "—"

            elif comparison_type == "diff_strings":
                diff_strings_not_matched = []
                normalized_body = normalize(item.new_value or "")
                for s in item.diff_strings:
                    if normalize(s) not in normalized_body:
                        diff_strings_not_matched.append(s)

                if diff_strings_not_matched:
                    item.diff = "<ul>{}</ul>".format(
                        "".join(
                            f"<li><del>{escape(s)}</del></li>"
                            for s in diff_strings_not_matched
                        )
                    )
                else:
                    if not name_modified(item):
                        item.status = "MATCH"

                    item.diff = "—"

            # default case, do nothing
            # elif comparison_type == "body":

            results.append(item)

    return results


def filter_comparison_by_status(comparison, statuses_to_ignore=[]):
    """
    Removes any comparison items (subsections or metadata rows) with statuses in `statuses_to_ignore`.

    - If the comparison is section-based (i.e., each item is a dict with a 'subsections' list),
      it will filter the subsections and discard sections that become empty.

    - If the comparison is flat (i.e., a list of SubsectionDiffs), it will directly filter the list.
    """
    if not statuses_to_ignore:
        return comparison

    if (
        comparison
        and isinstance(comparison[0], dict)
        and "subsections" in comparison[0]
    ):
        filtered = []
        for section in comparison:
            subsections = [
                s for s in section["subsections"] if s.status not in statuses_to_ignore
            ]
            if subsections:
                filtered.append({**section, "subsections": subsections})
        return filtered

    # Flat list metadata comparison (compare_nofos_metadata)
    return [item for item in comparison if item.status not in statuses_to_ignore]


def extract_old_diff(diff_html: str) -> str:
    soup = BeautifulSoup(diff_html, "html.parser")
    for ins in soup.find_all("ins"):
        ins.decompose()
    decompose_empty_tags(soup)
    return str(soup) or ""


def extract_new_diff(diff_html: str) -> str:
    soup = BeautifulSoup(diff_html, "html.parser")
    for delete in soup.find_all("del"):
        delete.decompose()
    decompose_empty_tags(soup)
    return str(soup) or ""


def annotate_side_by_side_diffs(comparison):
    for item in comparison:
        # Section-based comparison (has subsections)
        if isinstance(item, dict) and "subsections" in item:
            for s in item["subsections"]:
                if s.diff:
                    s.old_diff = extract_old_diff(s.diff)
                    s.new_diff = extract_new_diff(s.diff)
        # Metadata or flat comparison
        elif isinstance(item, SubsectionDiff):
            if item.diff:
                item.old_diff = extract_old_diff(item.diff)
                item.new_diff = extract_new_diff(item.diff)
    return comparison


def compare_nofos(old_nofo, new_nofo, statuses_to_ignore=[]):
    """
    Compares sections and subsections between an existing NOFO and a newly uploaded one.

    - Compares subsections within each section by name and position.
    - Marks each subsection as "MATCH", "UPDATE", "ADD", or "DELETE".
    - Applies additional rules to detect renamed subsections and diff string requirements.
    - Respects comparison_type and diff_strings if present on ContentGuideSubsections.

    Args:
        old_nofo: The existing NOFO instance.
        new_nofo: The new NOFO instance being compared.
        statuses_to_ignore (list[str], optional): Subsection statuses to exclude from the result (e.g. ["MATCH"]).

    Returns:
        list[dict]: A list of sections with structural diffs, each in the format:
            {
                "name": str,  # Section name
                "subsections": list[SubsectionDiff]  # Comparison results per subsection
            }
    """

    nofo_comparison = []

    for new_section in new_nofo.sections.all():
        old_section = old_nofo.sections.filter(name=new_section.name).first()
        comparison = compare_sections(old_section, new_section)

        if comparison["subsections"]:
            # Only add section comparison if there are changes
            nofo_comparison.append(comparison)

    for section in nofo_comparison:
        section["subsections"] = merge_renamed_subsections(section["subsections"])

    for section in nofo_comparison:
        section["subsections"] = apply_comparison_types(section["subsections"])

    return filter_comparison_by_status(nofo_comparison, statuses_to_ignore)


def compare_nofos_metadata(old_nofo, new_nofo, statuses_to_ignore=[]):
    """
    Compares metadata fields between two NOFO objects (an existing one and a new one).

    The result is a list of SubsectionDiff objects, which represent structured diffs
    for each metadata field. Optional comparison-related fields (like comparison_type
    and diff_strings) are available for downstream use but not populated here.

    Args:
        old_nofo: The original NOFO instance.
        new_nofo: The updated NOFO instance being compared.
        statuses_to_ignore (list[str], optional): A list of statuses to exclude from
            the final result (e.g., ["MATCH"] to omit unchanged fields).

    Returns:
        list[SubsectionDiff]: A filtered list of metadata diffs.
    """
    comparison_results = []

    metadata_keys = [
        "title",
        "number",
        "opdiv",
        "agency",
        "subagency",
        "subagency2",
        "application_deadline",
        "tagline",
    ]

    for key in metadata_keys:
        old_value = getattr(old_nofo, key, "") or ""
        new_value = getattr(new_nofo, key, "") or ""

        if key == "title":
            new_value = new_value.replace("(COMPARE) ", "")

        field_name = Nofo._meta.get_field(key).verbose_name

        if old_value != new_value:
            if not old_value:
                status = "ADD"
                diff = html_diff("", new_value)
            elif not new_value:
                status = "DELETE"
                diff = html_diff(old_value, "")
            else:
                status = "UPDATE"
                diff = html_diff(old_value, new_value)

            comparison_results.append(
                SubsectionDiff(
                    name=field_name,
                    status=status,
                    old_value=old_value,
                    new_value=new_value,
                    diff=diff,
                )
            )
        else:
            comparison_results.append(
                SubsectionDiff(
                    name=field_name,
                    status="MATCH",
                    old_value=old_value,
                    new_value=new_value,
                )
            )

    return filter_comparison_by_status(comparison_results, statuses_to_ignore)
