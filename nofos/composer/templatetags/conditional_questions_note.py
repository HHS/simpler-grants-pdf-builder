from composer.models import ContentGuideSubsection
from composer.utils import get_conditional_question_note
from django import template

register = template.Library()


@register.filter
def conditional_questions_note(subsection: ContentGuideSubsection):
    """
    Return the conditional question related to this subsection.
    Usage: {{ subsection|conditional_question_note }}
    """
    return get_conditional_question_note(subsection)
