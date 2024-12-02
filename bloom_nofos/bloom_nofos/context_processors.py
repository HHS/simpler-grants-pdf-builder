from constance import config
from django.conf import settings

from .utils import is_docraptor_test_mode_active


def add_docraptor_test_mode(request):
    last_updated = getattr(config, "DOCRAPTOR_TEST_MODE")
    docraptor_test_mode = is_docraptor_test_mode_active(last_updated)

    return {"DOCRAPTOR_TEST_MODE": docraptor_test_mode}


def add_github_sha(request):
    return {"GITHUB_SHA": settings.GITHUB_SHA}
