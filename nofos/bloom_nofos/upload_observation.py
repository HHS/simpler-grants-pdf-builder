"""Opt-in infra-dev body-read observations; never inspect or retain body data."""

import logging
import os
import time
import uuid

from constance import config
from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest

logger = logging.getLogger("django.request.readability_observation")
ROUTES = {
    "/readability": "public",
    "/readability/": "public",
    "/readability-checker": "public",
    "/readability-checker/": "public",
    "/nofos/readability": "authenticated",
    "/nofos/readability/": "authenticated",
    "/nofos/readability-checker": "authenticated",
    "/nofos/readability-checker/": "authenticated",
}
MAX_OBSERVED_READS = 8


class ObservedStream:
    def __init__(self, stream, source):
        self.stream = stream
        self.source = source
        self.observation_id = uuid.uuid4().hex
        self.worker_pid = os.getpid()
        self.calls = 0
        self.bytes_read = 0

    def emit(self, phase, **fields):
        try:
            logger.info(
                "Readability upload observation",
                extra={
                    "observation_phase": phase,
                    "observation_id": self.observation_id,
                    "worker_pid": self.worker_pid,
                    "upload_source": self.source,
                    **fields,
                },
            )
        except Exception:
            # A failed diagnostic sink must not break document handling.
            pass

    def _read(self, operation, *args, **kwargs):
        self.calls += 1
        sequence = self.calls
        observed = sequence <= MAX_OBSERVED_READS
        if observed:
            self.emit("read_begin", read_sequence=sequence, read_operation=operation)
        started = time.monotonic()
        try:
            data = getattr(self.stream, operation)(*args, **kwargs)
        except BaseException:
            if observed:
                self.emit("read_aborted", read_sequence=sequence)
            raise
        self.bytes_read += len(data)
        if observed:
            self.emit(
                "read_end",
                read_sequence=sequence,
                read_bytes=len(data),
                read_elapsed_ms=round((time.monotonic() - started) * 1000, 3),
            )
        return data

    def read(self, *args, **kwargs):
        return self._read("read", *args, **kwargs)

    def readline(self, *args, **kwargs):
        return self._read("readline", *args, **kwargs)

    def __iter__(self):
        return self

    def __next__(self):
        line = self.readline()
        if not line:
            raise StopIteration
        return line

    def __getattr__(self, name):
        return getattr(self.stream, name)


class ReadabilityUploadObservationMiddleware:
    """Wrap only matching WSGI POST streams before middleware can parse them."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        source = ROUTES.get(request.path_info)
        if (
            settings.READABILITY_OBSERVATION_ENVIRONMENT != "infra-dev"
            or request.method != "POST"
            or source is None
            or not isinstance(request, WSGIRequest)
            or getattr(request, "_read_started", False)
            or not hasattr(request, "_stream")
            or not config.HHS_NOFO_UPLOAD_READ_OBSERVATION_ENABLED
        ):
            return self.get_response(request)
        stream = ObservedStream(request._stream, source)
        request._stream = stream
        stream.emit("request_entered")
        phase = "response_raised"
        try:
            response = self.get_response(request)
            phase = "response_returned"
            return response
        finally:
            stream.emit(
                phase,
                body_read_calls=stream.calls,
                body_bytes_read=stream.bytes_read,
                read_events_truncated=stream.calls > MAX_OBSERVED_READS,
            )
            if request._stream is stream:
                request._stream = stream.stream
