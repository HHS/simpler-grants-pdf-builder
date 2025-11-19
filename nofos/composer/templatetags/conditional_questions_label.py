from composer.utils import get_conditional_questions_label
from django import template

register = template.Library()


@register.filter
def conditional_questions_label(conditional_answer):
    """
    Return "Conditional: Yes" or "Conditional: No" if subsection is a conditional question.
    Usage: {{ subsection|conditional_questions_label }}
    """
    return get_conditional_questions_label(conditional_answer)
