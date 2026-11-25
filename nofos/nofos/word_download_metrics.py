"""Content-free accounting of Word (.docx) download attempts.

Never pass documents, readability values, filenames or request bodies here.
Each entry point records exactly one row per attempt via record_word_download.
"""

import logging
import time

from django.conf import settings
from django.db import transaction

from .metrics_signals import EXCLUDED_GROUPS
from .models import WordDownloadAttempt

logger = logging.getLogger("django.request.word_download_metrics")

SOURCES = {code for code, _ in WordDownloadAttempt.SOURCE_CHOICES}
OUTCOMES = {code for code, _ in WordDownloadAttempt.OUTCOME_CHOICES}

# Used only when a response was not tagged by bloom_nofos.utils or
# readability_word_export, so an untagged response is still classified.
STATUS_FALLBACK_OUTCOMES = {
    400: "results_invalid",
    410: "results_expired",
    502: "conversion_failed",
    503: "export_disabled",
}


def outcome_for(response):
    outcome = getattr(response, "word_download_outcome", None)
    if outcome in OUTCOMES:
        return outcome
    if 200 <= response.status_code < 300:
        return "success"
    return STATUS_FALLBACK_OUTCOMES.get(response.status_code, "unknown")


def record_word_download(request, *, source, response, started, nofo=None):
    """Record one attempt. Never raises: a metrics failure must not break a download."""
    if not settings.WORD_DOWNLOAD_ATTEMPT_RECORDING_ENABLED:
        return
    if source not in SOURCES:
        logger.warning("Word download outcome has an unknown source.")
        return
    try:
        user = getattr(request, "user", None)
        authenticated = bool(user and user.is_authenticated)
        group = (getattr(user, "group", "") or "") if authenticated else ""
        with transaction.atomic():
            WordDownloadAttempt.objects.create(
                source=source,
                outcome=outcome_for(response),
                http_status=response.status_code,
                duration_ms=max(0, round((time.monotonic() - started) * 1000)),
                authenticated=authenticated,
                metrics_group=group,
                metrics_included=(group not in EXCLUDED_GROUPS) if group else None,
                nofo=nofo,
            )
    except Exception:
        # Deliberately omit exception text, like the readability attempt log.
        logger.warning("Word download outcome could not be recorded.")


def retention_days():
    return getattr(settings, "WORD_DOWNLOAD_ATTEMPT_RETENTION_DAYS", None)
