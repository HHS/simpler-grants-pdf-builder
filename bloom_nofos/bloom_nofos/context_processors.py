from constance import config
from django.conf import settings


def add_docraptor_test_mode(request):
    return {"DOCRAPTOR_TEST_MODE": getattr(config, "DOCRAPTOR_TEST_MODE")}


def add_github_sha(request):
    return {"GITHUB_SHA": settings.GITHUB_SHA}
