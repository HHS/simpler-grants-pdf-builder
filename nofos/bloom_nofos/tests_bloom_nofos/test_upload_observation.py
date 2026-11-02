"""Content-free, default-off dev upload observations preserve request behavior."""

import io
from types import SimpleNamespace
from unittest.mock import Mock, patch

from bloom_nofos.upload_observation import (
    MAX_OBSERVED_READS,
    ROUTES,
    ObservedStream,
    ReadabilityUploadObservationMiddleware,
)
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import path
from django.views.decorators.csrf import csrf_protect

MODULE = "bloom_nofos.upload_observation"


@csrf_protect
def multipart_view(request):
    upload = request.FILES["pdf"]
    return JsonResponse({"bytes": len(upload.read())})


urlpatterns = [path("readability-checker/", multipart_view)]


@override_settings(READABILITY_OBSERVATION_ENVIRONMENT="infra-dev")
class UploadObservationTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.flag = SimpleNamespace(HHS_NOFO_UPLOAD_READ_OBSERVATION_ENABLED=True)
        self.flag_patch = patch(MODULE + ".config", self.flag)
        self.flag_patch.start()
        self.addCleanup(self.flag_patch.stop)

    def request(self, path="/readability-checker/"):
        return self.factory.post(
            path, b"PRIVATE DOCUMENT", content_type="application/pdf"
        )

    def test_actual_setting_defaults_off(self):
        from django.conf import settings

        self.assertIs(
            settings.CONSTANCE_CONFIG["HHS_NOFO_UPLOAD_READ_OBSERVATION_ENABLED"][0],
            False,
        )

    def test_all_supported_route_forms_have_fixed_source_labels(self):
        for route, source in ROUTES.items():
            with self.subTest(route=route), patch(MODULE + ".logger") as logger:
                response = ReadabilityUploadObservationMiddleware(
                    lambda r: HttpResponse(r.body)
                )(self.request(route))
                self.assertEqual(response.content, b"PRIVATE DOCUMENT")
                self.assertEqual(
                    logger.info.call_args.kwargs["extra"]["upload_source"], source
                )

    def test_preconsumed_and_non_wsgi_streams_are_not_observed(self):
        request = self.request()
        self.assertEqual(request.body, b"PRIVATE DOCUMENT")
        non_wsgi = SimpleNamespace(
            method="POST",
            path_info="/readability-checker/",
            _stream=io.BytesIO(b"PRIVATE"),
        )
        for candidate in (request, non_wsgi):
            with patch(MODULE + ".logger") as logger:
                original = candidate._stream
                ReadabilityUploadObservationMiddleware(lambda r: HttpResponse())(
                    candidate
                )
                self.assertIs(candidate._stream, original)
                logger.info.assert_not_called()

    def test_disabled_flag_preserves_original_stream_and_emits_nothing(self):
        self.flag.HHS_NOFO_UPLOAD_READ_OBSERVATION_ENABLED = False
        request = self.request()
        original = request._stream

        def handle(request):
            self.assertIs(request._stream, original)
            return HttpResponse(request.body)

        with patch(MODULE + ".logger") as logger:
            response = ReadabilityUploadObservationMiddleware(handle)(request)
        self.assertEqual(response.content, b"PRIVATE DOCUMENT")
        logger.info.assert_not_called()

    def test_environment_gate_precedes_config_access(self):
        for environment in ("", "prod", "dev", "infra-training"):
            with self.subTest(environment=environment), override_settings(
                READABILITY_OBSERVATION_ENVIRONMENT=environment
            ), patch(MODULE + ".config") as config, patch(MODULE + ".logger") as logger:
                ReadabilityUploadObservationMiddleware(
                    lambda request: HttpResponse(request.body)
                )(self.request())
                self.assertEqual(config.mock_calls, [])
                logger.info.assert_not_called()

    def test_dynamic_toggle_requires_no_restart(self):
        middleware = ReadabilityUploadObservationMiddleware(
            lambda request: HttpResponse(request.body)
        )
        with patch(MODULE + ".logger") as logger:
            self.flag.HHS_NOFO_UPLOAD_READ_OBSERVATION_ENABLED = False
            middleware(self.request())
            logger.info.assert_not_called()
            self.flag.HHS_NOFO_UPLOAD_READ_OBSERVATION_ENABLED = True
            middleware(self.request())
            self.assertTrue(logger.info.called)
            logger.reset_mock()
            self.flag.HHS_NOFO_UPLOAD_READ_OBSERVATION_ENABLED = False
            middleware(self.request())
            logger.info.assert_not_called()

    def test_body_read_emits_begin_before_blocking_then_end(self):
        stream = Mock()

        def read(size):
            self.assertEqual(
                logger.info.call_args.kwargs["extra"]["observation_phase"], "read_begin"
            )
            return b"PRIVATE"

        stream.read.side_effect = read
        with patch(MODULE + ".logger") as logger:
            observed = ObservedStream(stream, "public")
            self.assertEqual(observed.read(7), b"PRIVATE")
            stream.read.assert_called_once_with(7)
            fields = logger.info.call_args.kwargs["extra"]
            self.assertEqual(fields["observation_phase"], "read_end")
            self.assertEqual(fields["read_bytes"], 7)
            self.assertEqual(fields["read_sequence"], 1)
            self.assertNotIn("PRIVATE", repr(logger.info.call_args_list))

    def test_only_fixed_metadata_is_logged_even_with_private_request_data(self):
        request = self.request("/readability-checker/?filename=PRIVATE")
        request.META.update(
            HTTP_COOKIE="PRIVATE", HTTP_USER_AGENT="PRIVATE", HTTP_REFERER="PRIVATE"
        )
        request.user = SimpleNamespace(id="PRIVATE")
        with patch(MODULE + ".logger") as logger:
            response = ReadabilityUploadObservationMiddleware(
                lambda r: HttpResponse(r.body)
            )(request)
        self.assertEqual(response.content, b"PRIVATE DOCUMENT")
        self.assertNotIn("PRIVATE", repr(logger.info.call_args_list))
        records = [call.kwargs["extra"] for call in logger.info.call_args_list]
        self.assertEqual(
            [row["observation_phase"] for row in records],
            ["request_entered", "read_begin", "read_end", "response_returned"],
        )
        self.assertEqual(len({row["observation_id"] for row in records}), 1)
        self.assertTrue(all(type(row["worker_pid"]) is int for row in records))
        self.assertEqual(records[-1]["body_bytes_read"], len(b"PRIVATE DOCUMENT"))

    def test_errors_propagate_without_logging_exception_content(self):
        stream = Mock()
        error = OSError("PRIVATE CONTENT")
        stream.read.side_effect = error
        with patch(MODULE + ".logger") as logger:
            observed = ObservedStream(stream, "authenticated")
            with self.assertRaises(OSError) as caught:
                observed.read()
            self.assertIs(caught.exception, error)
            self.assertEqual(
                logger.info.call_args.kwargs["extra"]["observation_phase"],
                "read_aborted",
            )
            self.assertNotIn("PRIVATE", repr(logger.info.call_args_list))

    def test_record_count_is_capped_and_truncation_is_disclosed(self):
        request = self.request()

        def handle(request):
            for _ in range(MAX_OBSERVED_READS + 4):
                request.read(1)
            return HttpResponse()

        with patch(MODULE + ".logger") as logger:
            ReadabilityUploadObservationMiddleware(handle)(request)
        self.assertEqual(logger.info.call_count, MAX_OBSERVED_READS * 2 + 2)
        self.assertTrue(logger.info.call_args.kwargs["extra"]["read_events_truncated"])

    def test_logging_failure_does_not_change_read_result(self):
        with patch(
            MODULE + ".logger.info", side_effect=RuntimeError("sink unavailable")
        ):
            response = ReadabilityUploadObservationMiddleware(
                lambda r: HttpResponse(r.body)
            )(self.request())
        self.assertEqual(response.content, b"PRIVATE DOCUMENT")

    def test_unrelated_paths_get_and_comparison_save_are_untouched(self):
        for request in (
            self.factory.get("/readability-checker/"),
            self.factory.post("/nofos/"),
            self.factory.post("/nofos/readability-checker/comparisons/save/"),
        ):
            with self.subTest(path=request.path), patch(MODULE + ".logger") as logger:
                original = request._stream
                ReadabilityUploadObservationMiddleware(lambda r: HttpResponse())(
                    request
                )
                self.assertIs(request._stream, original)
                logger.info.assert_not_called()

    def test_iteration_and_original_stream_are_preserved(self):
        raw = io.BytesIO(b"line one\nline two\n")
        with patch(MODULE + ".logger"):
            stream = ObservedStream(raw, "public")
            self.assertEqual(list(stream), [b"line one\n", b"line two\n"])
            stream.close()
            self.assertTrue(raw.closed)
        request = self.request()
        original = request._stream

        def fail(request):
            request.read(1)
            raise ValueError("PRIVATE")

        with patch(MODULE + ".logger") as logger, self.assertRaises(ValueError):
            ReadabilityUploadObservationMiddleware(fail)(request)
        self.assertIs(request._stream, original)
        self.assertEqual(
            logger.info.call_args.kwargs["extra"]["observation_phase"],
            "response_raised",
        )

    @override_settings(
        ROOT_URLCONF=__name__,
        MIDDLEWARE=[
            "bloom_nofos.upload_observation.ReadabilityUploadObservationMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
        ],
    )
    def test_real_django_multipart_parsing_remains_unchanged(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.middleware.csrf import _get_new_csrf_string
        from django.test import Client

        client = Client(enforce_csrf_checks=True)
        token = _get_new_csrf_string()
        client.cookies["csrftoken"] = token
        with patch(MODULE + ".logger") as logger:
            response = client.post(
                "/readability-checker/",
                {
                    "csrfmiddlewaretoken": token,
                    "pdf": SimpleUploadedFile("PRIVATE.pdf", b"PRIVATE DOCUMENT"),
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"bytes": len(b"PRIVATE DOCUMENT")})
        self.assertTrue(
            any(
                call.kwargs["extra"]["observation_phase"] == "read_begin"
                for call in logger.info.call_args_list
            )
        )
        self.assertNotIn("PRIVATE", repr(logger.info.call_args_list))
