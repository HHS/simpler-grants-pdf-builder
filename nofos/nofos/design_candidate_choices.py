"""Trusted host metadata, reusing current Builder model choices."""

from .models import Nofo


def design_capabilities():
    return {
        "operations": ["set_theme", "set_cover", "set_table_width"],
        "choices": {
            name: [value for value, _label in Nofo._meta.get_field(name).flatchoices]
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
