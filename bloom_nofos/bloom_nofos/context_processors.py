from constance import config
from django.conf import settings

from .utils import is_docraptor_live_mode_active


def add_docraptor_live_mode(request):
    last_updated = getattr(config, "DOCRAPTOR_LIVE_MODE")
    docraptor_live_mode = is_docraptor_live_mode_active(last_updated)

    return {"DOCRAPTOR_LIVE_MODE": docraptor_live_mode}


def add_github_sha(request):
    return {"GITHUB_SHA": settings.GITHUB_SHA}
