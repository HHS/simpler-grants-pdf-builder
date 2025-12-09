from html import escape
from typing import List

from composer.conditional.conditional_questions import find_question_for_subsection
from composer.models import (
    ContentGuide,
    ContentGuideSection,
    ContentGuideSubsection,
    VariableInfo,
)
from django.conf import settings
from django.forms import ValidationError

from nofos.nofo import _build_document

GROUP_MAP = dict(settings.GROUP_CHOICES)


def get_opdiv_label(opdiv_code: str) -> str:
    """
    Returns the human-readable label for a group code.
    If unknown, returns the code unchanged.
    """
    return GROUP_MAP.get(opdiv_code, opdiv_code)


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
    "locked": "Locked",
}

EDIT_MODE_LABEL_CLASSES = {
    "variables": "bg-yellow",
    "locked": "bg-secondary-light",
}


def get_edit_mode_label(value: str) -> str:
    """Return a human-readable label for an ContentGuideSubsection edit_mode value."""
    if not value:
        return ""
    return EDIT_MODE_LABELS.get(value) or ""


def get_edit_mode_label_class(value: str) -> str:
    """Return a class string to apply to the label tag <span> for a ContentGuideSubsection edit_mode label."""
    if not value:
        return ""
    return EDIT_MODE_LABEL_CLASSES.get(value) or ""


SUBSECTION_STATUS_LABELS = {
    "default": "Not started",
    "done": "Done",
}

SUBSECTION_STATUS_LABEL_CLASSES = {
    "default": "bg-yellow",
    "done": "bg-green text-white",
}


def get_subsection_status_label(value: str) -> str:
    """Return a human-readable label for an ContentGuideSubsection status value."""
    if not value:
        return ""
    return SUBSECTION_STATUS_LABELS.get(value) or ""


def get_subsection_status_label_class(value: str) -> str:
    """Return a class string to apply to the label tag <span> for a ContentGuideSubsection.status label."""
    if not value:
        return ""
    return SUBSECTION_STATUS_LABEL_CLASSES.get(value) or ""


def get_conditional_questions_label(conditional_answer=None) -> str:
    """Return a label for an ContentGuideSubsection that is a conditional question."""
    if conditional_answer is True:
        return "Conditional: Yes"
    if conditional_answer is False:
        return "Conditional: No"

    return ""


def get_conditional_question_note(subsection):
    if not subsection or not subsection.is_conditional:
        return ""

    question = find_question_for_subsection(subsection)
    if not question:
        return ""

    answer_label = "Yes" if subsection.conditional_answer else "No"

    return (
        "Note: Writers will be asked “<em>{}</em>”, "
        "and will see this section if they answer: <strong>{}</strong>. "
    ).format(
        question.label,
        answer_label,
    )


def get_yes_no_label(value):
    if value is True:
        return "Yes"
    if value is False:
        return "No"
    return "Not answered"


def render_curly_variable_list_html_string(
    extracted_variables: List[VariableInfo],
) -> str:
    """
    Render the HTML string for the inline variable list shown after the
    "Only variables in curly braces can be changed" label.

    Example:
        >>> render_curly_variable_list_html_string([
        ...   VariableInfo(key="k1", type="string", label="first"),
        ...   VariableInfo(key="k2", type="string", label="second")
        ... ])
        ': <span class="curly-var font-mono-xs">{first}</span>, '
        '<span class="curly-var font-mono-xs">{second}</span>'
    """
    variables = [escape(v.label.strip()) for v in extracted_variables or [] if v.label]

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
