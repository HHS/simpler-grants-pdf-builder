from html import escape
from typing import Dict, List

from bs4 import BeautifulSoup
from composer.conditional.conditional_questions import find_question_for_subsection
from composer.models import (
    ContentGuide,
    ContentGuideSection,
    ContentGuideSubsection,
    VariableInfo,
)
from django.conf import settings
from django.forms import ValidationError
from django.utils.safestring import mark_safe

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
        "Contentguideinstance": "Draft NOFO",
        "Contentguidesection": "Step",
        "Contentguidesubsection": "Section",
    }

    if not value:
        return ""

    return OBJECT_DISPLAY_NAMES.get(value) or value


def do_replace_variable_keys_with_values(html_string, variables_dict):
    """
    Replace variable keys in curly braces within the HTML string
    with their corresponding values from the variables_dict.

    Example:
        >>> replace_variable_keys_with_values(
        ...   "Hello, {name}! Your balance is {balance}.",
        ...   {"name": "Alice", "balance": "$100"}
        ... )
        "Hello, Alice! Your balance is $100."
    """
    soup = BeautifulSoup(html_string, "html.parser")

    # Find all span elements with class 'md-curly-variable'
    var_spans = soup.find_all("span", class_="md-curly-variable")
    for span in var_spans:
        # Look for a variable that matches the label
        label = span.text.strip().strip("{}").strip()
        try:
            var_key, var_info = _find_variable_by_label(variables_dict, label)
        except Exception as e:
            print("ERROR FINDING VAR BY LABEL", e)
            continue

        # If a matching variable exists, replace the content
        if var_key:
            var_value = var_info.value
            if var_value:
                # Update the span with the variable value
                span.string = var_value
                # Add the "md-curly-variable--value" class to the list of classes
                span["class"] = span.get("class", []) + ["md-curly-variable--value"]

    return mark_safe(str(soup))


def _find_variable_by_label(variables_dict: Dict[str, VariableInfo], label: str):
    for var_key, var_info in variables_dict.items():
        if var_info.label == label:
            return var_key, var_info
    return None, None
