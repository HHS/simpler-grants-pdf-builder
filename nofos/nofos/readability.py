"""NOFO Builder integration boundary for HHS readability metrics."""

from importlib import import_module

from django.template.loader import render_to_string

METRICS_MODULE = "hhs_nofo_metrics"
PROFILE_REFERENCE = "hhs-nofo-fy27-html@0.1.0"
EXPORT_ROOT_ID = "download_target"
PRODUCTION_PATH = "nofo_builder_export_html"


class ReadabilityMetricsUnavailable(RuntimeError):
    """The optional metrics package is not installed in this environment."""


class ReadabilityMetricsAnalysisError(RuntimeError):
    """The metrics package rejected or could not analyze the rendered source."""

    def __init__(self, payload):
        super().__init__(payload["message"])
        self.payload = payload


def render_nofo_export_document(nofo):
    """Render the same document fragment used by Builder's Word export."""

    return render_to_string(
        "nofos/includes/nofo_export_document.html",
        {"nofo": nofo},
    ).encode("utf-8")


def analyze_nofo_readability(nofo):
    """Return the package's complete, status-aware result for a NOFO revision."""

    try:
        metrics = import_module(METRICS_MODULE)
    except ModuleNotFoundError as error:
        if error.name == METRICS_MODULE:
            raise ReadabilityMetricsUnavailable(
                "The hhs-nofo-metrics package is not installed."
            ) from error
        raise

    source = metrics.SourceBundle.from_html(render_nofo_export_document(nofo))

    try:
        result = metrics.analyze(
            source,
            profile=PROFILE_REFERENCE,
            adapter_config={"root_id": EXPORT_ROOT_ID},
            production_path=PRODUCTION_PATH,
            document_id=str(nofo.pk),
            revision=nofo.updated.isoformat(),
        )
    except metrics.NofoMetricsError as error:
        raise ReadabilityMetricsAnalysisError(error.to_dict()) from error

    return result.to_dict()
