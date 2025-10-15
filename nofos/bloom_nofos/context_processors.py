from constance import config
from django.conf import settings

from .version import get_version


def template_context(request):
    """
    Provides specific settings variables to all templates.
    Only passes the exact settings needed rather than the entire settings object.
    """
    # Get Login.gov enabled status
    login_gov_enabled = getattr(settings, "LOGIN_GOV", {}).get("ENABLED", False)

    return {
        "GITHUB_SHA": settings.GITHUB_SHA,
        "LOGIN_GOV_ENABLED": login_gov_enabled,
        "VERSION": get_version(),
    }
