import re
from difflib import SequenceMatcher

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


def compare_nofos(new_nofo, old_nofo):
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
            "value": str,  # The body content of the new subsection (if applicable)
            "diff": str (optional)  # An HTML-based diff string showing changes (only included if the content changed)
        }
    """

    def get_subsection_name_or_order(subsection):
        return subsection.name or "(#{})".format(subsection.order)

    nofo_comparison = []

    for new_section in new_nofo.sections.all():
        old_section = old_nofo.sections.filter(name=new_section.name).first()

        section_comparison = {"name": new_section.name, "subsections": []}

        # Get all subsections for comparison
        new_subsections = list(new_section.subsections.all()) if new_section else []
        old_subsections = list(old_section.subsections.all()) if old_section else []
        max_length = max(len(new_subsections), len(old_subsections))

        matched_subsections = set()  # Track matched subsection IDs

        # Step 1: Iterate through both new and old subsections using the max index length
        for index in range(max_length):
            new_subsection = (
                new_subsections[index] if index < len(new_subsections) else None
            )
            old_subsection = (
                old_subsections[index] if index < len(old_subsections) else None
            )

            # First, check the new subsection (if it exists)
            if new_subsection:
                matched_old_subsection = None

                # Look for a match in old subsections
                for os in old_subsections:
                    if os.id in matched_subsections:
                        continue  # Skip already matched

                    if new_subsection.is_matching_subsection(os):
                        matched_old_subsection = os
                        # Mark as matched
                        matched_subsections.add(new_subsection.id)
                        matched_subsections.add(os.id)
                        break

                if matched_old_subsection:
                    # grab a diff. if only whitespaces changes, None is returned
                    diff = html_diff(matched_old_subsection.body, new_subsection.body)

                    # Check if body changed and diff is not None
                    if new_subsection.body != matched_old_subsection.body and diff:
                        section_comparison["subsections"].append(
                            {
                                "name": get_subsection_name_or_order(
                                    matched_old_subsection
                                ),
                                "status": "UPDATE",
                                "value": new_subsection.body,
                                "diff": diff,
                            }
                        )

                    else:
                        section_comparison["subsections"].append(
                            {
                                "name": get_subsection_name_or_order(
                                    matched_old_subsection
                                ),
                                "value": new_subsection.body,
                                "status": "MATCH",
                            }
                        )
                else:
                    # If no match was found, it's a new addition
                    section_comparison["subsections"].append(
                        {
                            "name": get_subsection_name_or_order(new_subsection),
                            "value": new_subsection.body,
                            "diff": html_diff("", new_subsection.body),
                            "status": "ADD",
                        }
                    )
                    matched_subsections.add(new_subsection.id)

            # Now, check the old subsection (if it exists)
            if old_subsection and old_subsection.id not in matched_subsections:
                # Look for it in new NOFO subsections (maybe it was moved)
                has_moved = any(
                    new.is_matching_subsection(old_subsection)
                    for new in new_subsections
                )

                if not has_moved:
                    section_comparison["subsections"].append(
                        {
                            "name": get_subsection_name_or_order(old_subsection),
                            "value": old_subsection.body,
                            "diff": html_diff(old_subsection.body, ""),
                            "status": "DELETE",
                        }
                    )
                    matched_subsections.add(old_subsection.id)

        # Only add section comparison if there are changes
        if section_comparison["subsections"]:
            nofo_comparison.append(section_comparison)

    return nofo_comparison


def compare_nofos_metadata(new_nofo, nofo):
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
        old_value = getattr(nofo, key, "") or ""
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
