"""Trusted host metadata, reusing current Builder model choices."""

import json

from .models import RETIRED_THEME_CHOICES, Nofo


def design_capabilities(*, candidate=None):
    """Return catalog values, retaining only this candidate's legacy theme.

    This catalog does not enforce user/group permissions. The integration host
    must further restrict choices using trusted initiating-user and document
    context, and rebuild them against the current candidate for each request.
    """
    current_theme = (
        json.loads(candidate.presentation_json)["theme"]
        if candidate is not None
        else None
    )
    return {
        "operations": ["set_theme", "set_cover", "set_table_width"],
        "choices": {
            name: [
                value
                for value, _label in Nofo._meta.get_field(name).flatchoices
                if name != "theme"
                or value not in RETIRED_THEME_CHOICES
                or value == current_theme
            ]
            for name in ("theme", "cover")
        },
        "pdf": {
            "supported": False,
            "reason": "DocRaptor is disabled in lower environments",
        },
        "html_review": {
            "supported": False,
            "reason": "Host review integration is not implemented in this slice",
        },
        "acceptance": {
            "supported": False,
            "reason": "Separate trusted human operation",
        },
    }
