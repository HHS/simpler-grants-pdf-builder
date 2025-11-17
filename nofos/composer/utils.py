from html import escape

from django.forms import ValidationError

from nofos.nofo import _build_document

from .models import ContentGuide, ContentGuideSection, ContentGuideSubsection


def create_content_guide_document(title, sections, opdiv):
    document = ContentGuide(title=title)
    document.opdiv = opdiv
    document.save()
    try:
        return _build_document(
            document, sections, ContentGuideSection, ContentGuideSubsection
        )
    except ValidationError as e:
        document.delete()
        e.document = document
        raise e


EDIT_MODE_LABELS = {
    "variables": "Certain text",
    "yes_no": "Yes/No",
    "locked": "Locked",
}

EDIT_MODE_LABEL_CLASSES = {
    "variables": "bg-yellow",
    "yes_no": "bg-primary-lighter",
    "locked": "bg-secondary-light",
}


def get_edit_mode_label(value: str) -> str:
    """Return a human-readable label for an ContentGuideSubsection edit_mode value."""
    if not value:
        return ""
    return EDIT_MODE_LABELS.get(value) or ""


def get_edit_mode_label_class(value: str) -> str:
    """Return a class string to apply to the label tag <span> for a ContentGuideSubsection."""
    if not value:
        return ""
    return EDIT_MODE_LABEL_CLASSES.get(value) or ""


def get_conditional_questions_label(subsection: ContentGuideSubsection) -> str:
    """Return a label for an ContentGuideSubsection that is a conditional question."""
    if subsection and subsection.is_conditional:
        if subsection.conditional_answer:
            return "Conditional: Yes"
        else:
            return "Conditional: No"

    return ""


def render_curly_variable_list_html_string(extracted_variables) -> str:
    """
    Render the HTML string for the inline variable list shown after the
    "Only variables in curly braces can be changed" label.

    Example:
        >>> render_curly_variable_list_html_string([
        ...   {"label": "first"}, {"label": "second"}
        ... ])
        ': <span class="curly-var font-mono-xs">{first}</span>, '
        '<span class="curly-var font-mono-xs">{second}</span>'
    """
    variables = [
        escape(v.get("label", "").strip())
        for v in extracted_variables or []
        if v.get("label")
    ]

    if not variables:
        return ""

    labels = ", ".join(
        f'<span class="curly-var font-mono-xs">{{{v}}}</span>' for v in variables
    )
    return f": {labels}"


def get_audit_event_object_display_name(value: str) -> str:
    OBJECT_DISPLAY_NAMES = {
        "Contentguide": "Content guide",
        "Contentguidesection": "Step",
        "Contentguidesubsection": "Section",
    }

    if not value:
        return ""

    return OBJECT_DISPLAY_NAMES.get(value) or value
