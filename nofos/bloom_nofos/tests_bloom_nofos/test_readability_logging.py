"""Keep anonymous PDF request content out of application request logs."""

import json
import logging

from bloom_nofos.logs import CustomJsonFormatter, ReadabilityRequestFilter
from bloom_nofos.middleware import JSONRequestLoggingMiddleware
from django.core.exceptions import (
    PermissionDenied,
    SuspiciousOperation,
    ValidationError,
)
from django.http import HttpResponse
from django.middleware.csrf import CsrfViewMiddleware
from django.test import Client, RequestFactory, SimpleTestCase, override_settings
from django.urls import path


def failing_view(request):
    if request.GET.get("failure") == "suspicious":
        raise SuspiciousOperation("secret suspicious request")
    raise RuntimeError("secret framework error")


def handler500(request):
    return HttpResponse("Server error", status=500)


def handler400(request, exception):
    return HttpResponse("Bad request", status=400)


urlpatterns = [path("readability/", failing_view), path("other/", failing_view)]


class ReadabilityLoggingTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = JSONRequestLoggingMiddleware(lambda request: HttpResponse())

    def request(self, path):
        return self.factory.get(
            path + "?name=secret.pdf",
            HTTP_REFERER="https://example.test/secret-referrer",
            HTTP_USER_AGENT="secret-agent",
        )

    def assert_safe(self, record):
        self.assertNotIn("secret", repr(record.__dict__))
        for key in ("exception_message", "traceback", "referrer", "user_agent"):
            self.assertNotIn(key, record.__dict__)
        payload = json.loads(CustomJsonFormatter().format(record))
        self.assertNotIn("secret", json.dumps(payload))

    def test_readability_response_logs_are_safe_in_all_environments(self):
        for prod in (False, True):
            for path in ("/readability/", "/readability"):
                for status in (200, 400, 503):
                    with self.subTest(prod=prod, path=path, status=status):
                        with override_settings(is_prod=prod):
                            with self.assertLogs(
                                "django.request", level="INFO"
                            ) as logs:
                                self.middleware.process_response(
                                    self.request(path), HttpResponse(status=status)
                                )
                        self.assertEqual(logs.records[0].url, path)
                        self.assert_safe(logs.records[0])

    @override_settings(is_prod=True)
    def test_readability_exception_logs_omit_message_and_traceback(self):
        for error, status in (
            (RuntimeError, 500),
            (ValidationError, 400),
            (PermissionDenied, 403),
        ):
            with self.subTest(error=error):
                request = self.request("/readability/")
                with self.assertLogs("django.request", level="WARNING") as logs:
                    try:
                        raise error("secret exception text")
                    except error as exc:
                        self.middleware.process_exception(request, exc)
                record = logs.records[0]
                self.assertEqual(record.exception_type, error.__name__)
                self.assertEqual(record.status, status)
                self.assertIn("response_time", record.__dict__)
                self.assert_safe(record)

    @override_settings(is_prod=True)
    def test_other_routes_keep_existing_logging(self):
        for path in ("/nofos/", "/readability-other/", "/readability/child/"):
            with self.subTest(path=path):
                request = self.request(path)
                with self.assertLogs("django.request", level="INFO") as logs:
                    self.middleware.process_response(request, HttpResponse())
                    try:
                        raise RuntimeError("secret exception text")
                    except RuntimeError as exc:
                        self.middleware.process_exception(request, exc)
                self.assertIn("?name=secret.pdf", logs.records[0].url)
                self.assertEqual(logs.records[0].user_agent, "secret-agent")
                self.assertIn("secret-referrer", logs.records[0].referrer)
                self.assertEqual(
                    logs.records[1].exception_message, "secret exception text"
                )
                self.assertIn("secret exception text", logs.records[1].traceback)

    def test_django_error_record_is_sanitized_without_affecting_other_routes(self):
        for path in ("/readability/", "/nofos/"):
            with self.subTest(path=path):
                error = RuntimeError("secret framework error")
                record = logging.LogRecord(
                    "django.request",
                    logging.ERROR,
                    __file__,
                    1,
                    "Internal Server Error: %s",
                    (path,),
                    (RuntimeError, error, None),
                )
                record.request = self.request(path)
                record.status_code = 500
                # Exercise cached traceback text as well as exc_info.
                record.exc_text = "secret cached traceback"
                ReadabilityRequestFilter().filter(record)
                if path == "/readability/":
                    self.assert_safe(record)
                    self.assertIsNone(record.exc_info)
                    self.assertNotIn("request", record.__dict__)
                    self.assertEqual(record.exception_type, "RuntimeError")
                    self.assertEqual(record.status_code, 500)
                else:
                    self.assertIs(record.exc_info[1], error)
                    self.assertIn("request", record.__dict__)

    @override_settings(
        ROOT_URLCONF=__name__,
        MIDDLEWARE=["bloom_nofos.middleware.JSONRequestLoggingMiddleware"],
        DEBUG=False,
        is_prod=True,
    )
    def test_full_exception_chain_sanitizes_both_request_records(self):
        logger = logging.getLogger("django.request")
        privacy_filter = ReadabilityRequestFilter()
        logger.addFilter(privacy_filter)
        self.addCleanup(logger.removeFilter, privacy_filter)
        client = Client(raise_request_exception=False)
        with self.assertLogs("django.request", level="ERROR") as logs:
            response = client.get(
                "/readability/?name=secret.pdf",
                HTTP_REFERER="https://example.test/secret-referrer",
                HTTP_USER_AGENT="secret-agent",
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(len(logs.records), 2)
        for record in logs.records:
            self.assert_safe(record)

    def test_inherited_django_handlers_have_privacy_filter(self):
        handlers = logging.getLogger("django").handlers
        self.assertTrue(handlers)
        for handler in handlers:
            self.assertTrue(
                any(
                    isinstance(item, ReadabilityRequestFilter)
                    for item in handler.filters
                )
            )

    @override_settings(CSRF_TRUSTED_ORIGINS=[])
    def test_real_csrf_rejection_sanitizes_submitted_referrer(self):
        request = self.factory.post(
            "/readability/?name=secret.pdf",
            secure=True,
            HTTP_REFERER="https://evil.test/secret-filename.pdf",
        )
        with self.assertLogs("django.security.csrf", level="WARNING") as logs:
            # assertLogs replaces handlers; use the same filter as the runtime
            # handlers whose installation is checked separately above.
            for handler in logging.getLogger("django.security.csrf").handlers:
                handler.addFilter(ReadabilityRequestFilter())
            response = CsrfViewMiddleware(lambda request: HttpResponse()).process_view(
                request, lambda request: HttpResponse(), (), {}
            )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(logs.records), 1)
        self.assert_safe(logs.records[0])

    @override_settings(ROOT_URLCONF=__name__, MIDDLEWARE=[], DEBUG=False)
    def test_real_suspicious_operation_omits_exception_and_request(self):
        with self.assertLogs(
            "django.security.SuspiciousOperation", level="ERROR"
        ) as logs:
            for handler in logging.getLogger(
                "django.security.SuspiciousOperation"
            ).handlers:
                handler.addFilter(ReadabilityRequestFilter())
            response = Client().get("/readability/?failure=suspicious&name=secret.pdf")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(logs.records), 1)
        self.assert_safe(logs.records[0])
