from constance import config
from django.conf import settings

from .utils import is_grabzit_word_export_enabled
from .version import get_version


def template_context(request):
    """
    Provides specific settings variables to all templates.
    Only passes the exact settings needed rather than the entire settings object.
    """
    # Get Login.gov enabled status
    login_gov_enabled = getattr(settings, "LOGIN_GOV", {}).get("ENABLED", False)
    grabzit_word_export_enabled = bool(
        request and is_grabzit_word_export_enabled(request.get_host())
    )

    return {
        "GITHUB_SHA": settings.GITHUB_SHA,
        "GRABZIT_WORD_EXPORT_ENABLED": grabzit_word_export_enabled,
        "LOGIN_GOV_ENABLED": login_gov_enabled,
        "VERSION": get_version(),
    }
