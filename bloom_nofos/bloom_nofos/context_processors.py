from constance import config
from django.conf import settings

from .utils import is_docraptor_live_mode_active


def template_context(request):
    """
    Provides specific settings variables to all templates.
    Only passes the exact settings needed rather than the entire settings object.
    """
    # Get DocRaptor live mode status
    last_updated = getattr(config, "DOCRAPTOR_LIVE_MODE")
    docraptor_live_mode = is_docraptor_live_mode_active(last_updated)

    # Get Login.gov enabled status
    login_gov_enabled = getattr(settings, "LOGIN_GOV", {}).get("ENABLED", False)

    return {
        "DOCRAPTOR_LIVE_MODE": docraptor_live_mode,
        "GITHUB_SHA": settings.GITHUB_SHA,
        "LOGIN_GOV_ENABLED": login_gov_enabled,
    }
