from django import template
from django.utils.html import format_html

from nofos.policy_language import get_policy_language_export_note

register = template.Library()


@register.filter(is_safe=True)
def policy_language_export_note(subsection):
    """The reviewer-facing note for a flagged subsection, as safe HTML with
    only its leading label ("Review:"/"Priority review:") bolded - the rest
    renders at normal weight, so the callout doesn't read as one solid
    block of bold text. Empty string (falsy, same as None in a template
    {% if %}) if the subsection isn't flagged - see
    get_policy_language_export_note for the status rules."""
    note = get_policy_language_export_note(subsection)
    if not note:
        return ""
    label, _, rest = note.partition(":")
    return format_html("<strong>{}:</strong>{}", label, rest)


@register.filter()
def policy_language_flag_is_prominent(subsection):
    slot = subsection.policy_language_slot
    return bool(slot and slot.flag_prominently)
