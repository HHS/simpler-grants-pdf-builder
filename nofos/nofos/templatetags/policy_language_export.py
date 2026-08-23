from django import template

from nofos.policy_language import get_policy_language_export_note

register = template.Library()


@register.filter()
def policy_language_export_note(subsection):
    """The reviewer-facing note for a flagged subsection, or None if it
    isn't one (see get_policy_language_export_note for the status rules)."""
    return get_policy_language_export_note(subsection)


@register.filter()
def policy_language_flag_is_prominent(subsection):
    slot = subsection.policy_language_slot
    return bool(slot and slot.flag_prominently)
