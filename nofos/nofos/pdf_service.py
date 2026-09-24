"""Generate a NOFO PDF without coupling callers to the download response."""

from dataclasses import dataclass

import docraptor
from bloom_nofos.context_processors import template_context
from django.conf import settings
from django.template.loader import render_to_string

from .nofo_document_context import get_nofo_document_context


@dataclass(frozen=True)
class GeneratedPDF:
    content: bytes
    is_test_pdf: bool


class PDFGenerationError(Exception):
    """DocRaptor rejected PDF generation; no vendor details are exposed."""

    def __init__(self, *, status_code=None):
        super().__init__("DocRaptor PDF generation failed")
        # HTTP status codes are safe operational metadata. Do not retain the
        # vendor reason, response body, or headers because they may echo the
        # submitted NOFO or credentials.
        self.status_code = status_code if type(status_code) is int else None
        self.is_retryable = (
            self.status_code is None
            or self.status_code in (0, 408, 429)
            or self.status_code >= 500
        )


def generate_nofo_pdf(nofo, *, base_url: str, is_test_pdf: bool) -> GeneratedPDF:
    """Render and generate a PDF for an already-authorized NOFO.

    Callers must authorize access and provide a trusted absolute base URL for
    relative assets and links. This function neither records an audit event nor
    makes an artifact available; those are caller-specific operations.
    """
    # Reuse the detail page's document context without attaching a request or
    # running request context processors. In particular, user controls, CSRF
    # tokens, and credentials must never be sent to DocRaptor.
    document_context = {"object": nofo, "nofo": nofo}
    document_context.update(get_nofo_document_context(nofo))
    document_context.update(template_context(None))
    document_content = render_to_string("nofos/nofo_pdf.html", document_context)

    doc_api = docraptor.DocApi()
    doc_api.api_client.configuration.username = settings.DOCRAPTOR_API_KEY
    # The request contains the complete NOFO; the SDK must not log its payload.
    doc_api.api_client.configuration.debug = False
    try:
        content = doc_api.create_doc(
            {
                "test": is_test_pdf,
                "document_content": document_content,
                "document_type": "pdf",
                "javascript": False,
                "pipeline": 11,
                "prince_options": {
                    "baseurl": base_url,
                    "media": "print",
                    "profile": "PDF/UA-1",
                },
            }
        )
    except docraptor.rest.ApiException as error:
        raise PDFGenerationError(status_code=error.status) from None
    return GeneratedPDF(content=content, is_test_pdf=is_test_pdf)
