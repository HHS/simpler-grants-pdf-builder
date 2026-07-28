import re

PDF_METADATA_FIELDS = (
    ("author", "Author"),
    ("subject", "Subject"),
    ("keywords", "Keywords"),
)

_WHOLE_FIELD_PLACEHOLDER = re.compile(r"^\{[^{}]+\}$")


def normalize_pdf_metadata_value(value):
    """Convert a whole-field curly-brace placeholder to an empty value."""
    if not value:
        return ""

    stripped_value = value.strip()
    if not stripped_value or _WHOLE_FIELD_PLACEHOLDER.fullmatch(stripped_value):
        return ""

    return value


def is_missing_pdf_metadata_value(value):
    """Return whether a metadata value is empty or only a placeholder."""
    return not normalize_pdf_metadata_value(value).strip()
