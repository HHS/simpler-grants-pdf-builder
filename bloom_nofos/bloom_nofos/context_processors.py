from constance import config


def add_docraptor_test_mode(request):
    return {"DOCRAPTOR_TEST_MODE": getattr(config, "DOCRAPTOR_TEST_MODE")}
