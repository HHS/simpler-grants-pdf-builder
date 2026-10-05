from constance import config
from django.conf import settings
from django.utils.functional import SimpleLazyObject

from .changelog_banner import CHANGELOG_URL, get_active_release
from .utils import is_grabzit_word_export_enabled
from .version import get_version


def template_context(request):
    """
    Provides specific settings variables to all templates.
    Only passes the exact settings needed rather than the entire settings object.
    """
    grabzit_word_export_enabled = bool(
        request and is_grabzit_word_export_enabled(request.get_host())
    )

    return {
        "GITHUB_SHA": settings.GITHUB_SHA,
        "GRABZIT_WORD_EXPORT_ENABLED": grabzit_word_export_enabled,
        "VERSION": get_version(),
        # Lazy, so only templates that render the banner (base.html) read the
        # Constance settings.
        "CHANGELOG_BANNER": SimpleLazyObject(get_changelog_banner),
    }


def get_changelog_banner():
    """
    Returns banner details while the newest CHANGELOG.md release is inside its
    business-day window and the banner is enabled, otherwise None.
    """
    if not config.CHANGELOG_BANNER_ENABLED:
        return None

    release = get_active_release(business_days=config.CHANGELOG_BANNER_BUSINESS_DAYS)
    if release is None:
        return None

    return {
        "version": release.version,
        "release_date": release.release_date,
        "url": CHANGELOG_URL,
    }
