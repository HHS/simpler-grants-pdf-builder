import re
from difflib import SequenceMatcher

from django.utils.html import escape

from .models import Nofo


def html_diff(original, new):
    def _tokenize(text):
        """Splits text into words while keeping punctuation and spaces intact."""
        return re.findall(r"\s+|\w+|\W", text)

    def _is_whitespace_only(text):
        return re.fullmatch(r"\s*", text) is not None  # Matches only whitespace

    original_tokens = _tokenize(original)
    new_tokens = _tokenize(new)

    matcher = SequenceMatcher(None, original_tokens, new_tokens)
    result = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        # Rebuild text from tokens
        old_text = "".join(original_tokens[i1:i2])
        new_text = "".join(new_tokens[j1:j2])

        if tag == "replace":
            if not _is_whitespace_only(old_text):
                result.append(f"<del>{old_text}</del>")
            if not _is_whitespace_only(new_text):
                result.append(f"<ins>{new_text}</ins>")
            if _is_whitespace_only(old_text) and _is_whitespace_only(new_text):
                result.append(new_text)
        elif tag == "delete":
            if not _is_whitespace_only(old_text):
                result.append(f"<del>{old_text}</del>")
        elif tag == "insert":
            if not _is_whitespace_only(new_text):
                result.append(f"<ins>{new_text}</ins>")
        else:  # "equal" case
            result.append(old_text)

    diff_result = "".join(result)

    return diff_result if "<del>" in diff_result or "<ins>" in diff_result else None


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


def add_content_guide_comparison_metadata(result, subsection):
    """
    Adds comparison_type and diff_strings to the result dict if present on the subsection.
    Returns a new dict with those keys added if applicable.
    """
    if hasattr(subsection, "comparison_type"):
        result["comparison_type"] = subsection.comparison_type
        result["diff_strings"] = subsection.diff_strings or []
    return result


def result_match(original_subsection):
    result = {
        "name": get_subsection_name_or_order(original_subsection),
        "status": "MATCH",
        "old_value": original_subsection.body,
        "new_value": original_subsection.body,
        "diff": "",  # no changes,
    }

    return add_content_guide_comparison_metadata(result, original_subsection)


def result_update(original_subsection, new_subsection):
    result = {
        "name": get_subsection_name_or_order(original_subsection),
        "status": "UPDATE",
        "old_value": original_subsection.body,
        "new_value": new_subsection.body,
        "diff": html_diff(original_subsection.body, new_subsection.body) or "",
    }

    return add_content_guide_comparison_metadata(result, original_subsection)


def result_merged_update(name, old_value, new_value, old_sub_dict=None):
    result = {
        "name": name,
        "status": "UPDATE",
        "old_value": old_value,
        "new_value": new_value,
        "diff": html_diff(old_value, new_value),
    }

    if old_sub_dict.get("comparison_type", None):
        result["comparison_type"] = old_sub_dict.get("comparison_type")
        result["diff_strings"] = old_sub_dict.get("diff_strings", [])

    return result


def result_add(new_subsection):
    return {
        "name": get_subsection_name_or_order(new_subsection),
        "status": "ADD",
        "old_value": "",
        "new_value": new_subsection.body,
        "diff": html_diff("", new_subsection.body) or "",
    }


def result_delete(original_subsection):
    result = {
        "name": html_diff(get_subsection_name_or_order(original_subsection), ""),
        "status": "DELETE",
        "old_value": original_subsection.body,
        "new_value": "",
        "diff": html_diff(original_subsection.body, "") or "",
    }

    return add_content_guide_comparison_metadata(result, original_subsection)


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
    max_length = max(len(new_subsections), len(old_subsections))
    matched_subsections = set()

    subsections = []

    for index in range(max_length):
        new_sub = new_subsections[index] if index < len(new_subsections) else None
        old_sub = old_subsections[index] if index < len(old_subsections) else None
        # First, check the new subsection for a match
        if new_sub:
            matched_old_sub = find_matching_subsection(
                new_sub, old_subsections, matched_subsections
            )
            if matched_old_sub:
                # add ids from both subsections to the "matched_subsections" set
                matched_subsections.update([new_sub.id, matched_old_sub.id])

                # Check if body does not match and diff is not None
                if new_sub.body != matched_old_sub.body and html_diff(
                    matched_old_sub.body.strip(), new_sub.body.strip()
                ):
                    # UPDATE
                    subsections.append(result_update(matched_old_sub, new_sub))
                else:
                    # MATCH
                    subsections.append(result_match(matched_old_sub))

            else:
                # ADD
                subsections.append(result_add(new_sub))
                matched_subsections.add(new_sub.id)

        if old_sub and old_sub.id not in matched_subsections:
            # Look for it in new NOFO subsections (maybe it was moved)
            has_moved = any(n.is_matching_subsection(old_sub) for n in new_subsections)
            if not has_moved:
                # DELETE
                subsections.append(result_delete(old_sub))
                matched_subsections.add(old_sub.id)

    return {
        "name": new_section.name,
        "subsections": subsections,
    }


def merge_renamed_subsections(subsections):
    """
    Detects DELETE + ADD pairs in a section that are likely renames and merges them into an UPDATE.
    This improves diff quality when only a subsection title has changed (and body remains the same or similar).
    """
    merged = []
    i = 0

    while i < len(subsections):
        current = subsections[i]
        next_item = subsections[i + 1] if i + 1 < len(subsections) else None

        if current["status"] == "ADD" and next_item and next_item["status"] == "DELETE":
            new_body = current["new_value"].strip()
            old_body = next_item["old_value"].strip()
            new_name = current["name"]
            old_name = next_item["name"].replace("<del>", "").replace("</del>", "")

            heading_diff = html_diff(old_name, new_name)

            is_rename_only = old_body == new_body
            # look for if there is shared text in the header (remove del and ins and keep remainder)
            has_shared_heading = bool(
                re.sub(r"<(del|ins)>.*?</\1>", "", heading_diff).strip()
            )

            if is_rename_only or has_shared_heading:
                merged.append(
                    result_merged_update(
                        name=heading_diff or new_name,
                        old_value=old_body,
                        new_value=new_body,
                        old_sub_dict=next_item,
                    )
                )
                i += 2
                continue

        # Normal case: keep the current item
        merged.append(current)
        i += 1

    return merged


def apply_comparison_types(subsections):
    def normalize(text):
        return re.sub(r"\s+", " ", text.strip()).lower()

    results = []
    for item in subsections:
        comparison_type = item.get("comparison_type")

        if comparison_type == "none":
            continue

        if not comparison_type or item["status"] in ["ADD", "DELETE", "MATCH"]:
            results.append(item)
            continue

        if item["status"] == "UPDATE":
            if comparison_type == "name":
                if "<del>" not in item["name"] and "<ins>" not in item["name"]:
                    item["status"] = "MATCH"

                item["diff"] = "—"

            elif comparison_type == "diff_strings":
                diff_strings_not_matched = []
                normalized_body = normalize(item["new_value"])
                for s in item.get("diff_strings", []):
                    if normalize(s) not in normalized_body:
                        diff_strings_not_matched.append(s)

                if diff_strings_not_matched:
                    item["diff"] = "<ul>{}</ul>".format(
                        "".join(
                            f"<li><del>{escape(s)}</del></li>"
                            for s in diff_strings_not_matched
                        )
                    )
                else:
                    item["status"] = "MATCH"
                    item["diff"] = "—"

            # default case, do nothing
            # elif comparison_type == "body":

            results.append(item)

    return results


def compare_nofos(old_nofo, new_nofo):
    """
    Compares sections and subsections between an existing NOFO and a newly uploaded one.

    - Identifies matched, added, and deleted subsections.
    - Preserves order based on the new NOFO’s structure.
    - If a matched subsection has different content, marks it as updated.

    Returns:
        list[dict]: A structured list of subsection diff objects, in this format:

        {
            "name": str,   # The name of the subsection
            "status": str,  # One of "MATCH", "UPDATE", "ADD", or "DELETE"
            "old_value": str,  # The body content of the old subsection (if applicable)
            "new_value": str,  # The body content of the new subsection (if applicable)
            "diff": str (optional)  # An HTML-based diff string showing changes (only included if the content changed)
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

    return nofo_comparison


def compare_nofos_metadata(old_nofo, new_nofo):
    """
    Compares metadata fields between an existing NOFO and a newly uploaded one.

    - Identifies added, deleted, and updated metadata fields.
    - Returns a structured diff showing changes.

    Returns:
        list[dict]: A structured list of subsection diff objects, in this format:

        {
            "name": str,   # The name of the attribute
            "status": str,  # One of "MATCH", "UPDATE", "ADD", or "DELETE"
            "value": str,  # The value of the new attribute (if applicable)
            "diff": str (optional)  # An HTML-based diff string showing changes (only included if the content changed)
        }
    """
    nofo_metadata_comparison = []

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
            # the comparison NOFO has this appended automatically, this is not a true change
            new_value = new_value.replace("(COMPARE) ", "")

        field_name = Nofo._meta.get_field(key).verbose_name

        if old_value != new_value:
            if not old_value:  # Value was missing before, now added
                status = "ADD"
                diff = html_diff("", new_value)
            elif not new_value:  # Value was present before, now deleted
                status = "DELETE"
                diff = html_diff(old_value, "")
            else:  # Value changed
                status = "UPDATE"
                diff = html_diff(old_value, new_value)

            nofo_metadata_comparison.append(
                {
                    "name": field_name,
                    "status": status,
                    "value": new_value,
                    "diff": diff,
                }
            )
        else:
            nofo_metadata_comparison.append(
                {
                    "name": field_name,
                    "status": "MATCH",
                    "value": new_value,
                }
            )

    return nofo_metadata_comparison
