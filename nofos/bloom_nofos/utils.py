import io
import logging
import re
import zipfile
import zlib
from socket import gaierror, gethostbyname, gethostname
from urllib.parse import urlparse
from xml.etree import ElementTree

from django.conf import settings
from django.http import HttpResponse, HttpResponseServerError
from GrabzIt import GrabzItClient, GrabzItDOCXOptions

logger = logging.getLogger(__name__)
DOCX_DOCUMENT_PATH = "word/document.xml"
DOCX_REQUIRED_PATHS = {"[Content_Types].xml", DOCX_DOCUMENT_PATH}
WORDPROCESSINGML_TEXT_TAG = (
    "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
)


def with_word_download_outcome(response, outcome):
    """Tag a Word download response with why it ended, for usage metrics.

    The attribute stays on the server-side response object; it is never sent
    to the browser. See nofos.word_download_metrics.
    """
    response.word_download_outcome = outcome
    return response


def cast_to_boolean(value_str):
    """
    Cast a string value to a boolean.

    Args:
    value_str (str): The string to be cast to a boolean.

    Returns:
    bool: The boolean value of the string.

    Raises:
    ValueError: If the string cannot be cast to a boolean.
    """
    # Define truthy and falsy values
    truthy_values = [True, "true", "True", "TRUE", "1", "t"]
    falsy_values = [False, "false", "False", "FALSE", "0", "f", ""]

    if value_str in truthy_values:
        return True
    elif value_str in falsy_values:
        return False
    else:
        raise ValueError(f"Value '{value_str}' is not a valid boolean string")


def get_internal_ip():
    try:
        return gethostbyname(gethostname())
    except gaierror:
        return ""


def parse_docraptor_ip_addresses(ip_string: str):
    # Split on commas, spaces, and newlines while ignoring extra whitespace
    return [ip.strip() for ip in re.split(r"[\s,]+", ip_string) if ip.strip()]


def _normalize_hostname(host):
    return (host or "").split(":", 1)[0].lower().rstrip(".")


def is_grabzit_word_export_enabled(host):
    """Return whether this host may use the configured GrabzIt credentials."""
    allowed_hosts = set(settings.GRABZIT_WORD_EXPORT_ALLOWED_HOSTS)
    return bool(
        settings.GRABZIT_APPLICATION_KEY
        and settings.GRABZIT_APPLICATION_SECRET
        and _normalize_hostname(host) in allowed_hosts
    )


def is_valid_docx(content):
    """Reject blank or malformed provider output before offering a download."""
    if not content:
        return False

    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            if not DOCX_REQUIRED_PATHS.issubset(archive.namelist()):
                return False
            document = ElementTree.fromstring(archive.read(DOCX_DOCUMENT_PATH))
    except (
        ElementTree.ParseError,
        KeyError,
        zipfile.BadZipFile,
        zipfile.LargeZipFile,
        # A corrupt or unsupported compressed entry, or an encrypted package.
        zlib.error,
        EOFError,
        NotImplementedError,
        RuntimeError,
        ValueError,
    ):
        return False

    return any(
        node.text and node.text.strip()
        for node in document.iter(WORDPROCESSINGML_TEXT_TAG)
    )


def generate_docx_download_response(
    *,
    request,
    export_url: str,
    target_element: str,
    filename_base: str,
):
    """
    Convert a URL to DOCX using GrabzIt and return it as an attachment response.
    """
    request_host = _normalize_hostname(request.get_host())
    if not is_grabzit_word_export_enabled(request_host):
        logger.warning(
            "GrabzIt Word export blocked for unconfigured host",
            extra={
                "export_host": request_host,
                "allowed_export_hosts": settings.GRABZIT_WORD_EXPORT_ALLOWED_HOSTS,
            },
        )
        return with_word_download_outcome(
            HttpResponse(
                "Word export is not available in this environment.", status=503
            ),
            "export_disabled",
        )

    session_value = request.COOKIES.get("sessionid")
    csrf_value = request.COOKIES.get("csrftoken")

    if not session_value or not csrf_value:
        return with_word_download_outcome(
            HttpResponseServerError(
                "Missing session/csrf cookies for DOCX conversion."
            ),
            "missing_cookies",
        )

    parsed = urlparse(export_url)
    export_host = _normalize_hostname(parsed.hostname)
    export_scheme = parsed.scheme

    if not export_host or export_scheme != "https":
        return with_word_download_outcome(
            HttpResponseServerError("Invalid export URL for DOCX conversion."),
            "invalid_export_url",
        )

    # Defensive check: the cookies we are copying came from this incoming request,
    # so the request host should match the host GrabzIt will fetch.
    if request_host != export_host:
        return with_word_download_outcome(
            HttpResponseServerError(
                f"Host mismatch for DOCX conversion. request_host={request_host}, export_host={export_host}"
            ),
            "host_mismatch",
        )

    grabzit = _grabzit_docx_client()

    # Set cookies only for the exact host GrabzIt will request.
    for name, value, label in (
        ("sessionid", session_value, "session"),
        ("csrftoken", csrf_value, "csrf"),
    ):
        try:
            registered = grabzit.SetCookie(name, export_host, value)
        except Exception as exc:
            # A network error or timeout reaching GrabzIt. Log neither the
            # cookie value nor the provider's error text.
            logger.error(
                "GrabzIt cookie registration failed",
                extra={"export_host": export_host, "error_type": type(exc).__name__},
            )
            registered = False
        if not registered:
            return with_word_download_outcome(
                HttpResponseServerError(
                    f"Failed to set {label} cookie for GrabzIt conversion."
                ),
                "cookie_rejected",
            )

    options = GrabzItDOCXOptions.GrabzItDOCXOptions()
    options.targetElement = target_element

    return _docx_attachment(
        grabzit,
        lambda: grabzit.URLToDOCX(export_url, options),
        filename_base,
        export_host,
    )


def generate_html_docx_download_response(*, request, html, filename_base):
    """Convert dedicated HTML without forwarding browser cookies or a source URL."""
    host = _normalize_hostname(request.get_host())
    if not is_grabzit_word_export_enabled(host):
        return with_word_download_outcome(
            HttpResponse(
                "Word export is not available in this environment.", status=503
            ),
            "export_disabled",
        )
    grabzit = _grabzit_docx_client()
    return _docx_attachment(
        grabzit, lambda: grabzit.HTMLToDOCX(html), filename_base, host
    )


def _grabzit_docx_client():
    grabzit = GrabzItClient.GrabzItClient(
        settings.GRABZIT_APPLICATION_KEY,
        settings.GRABZIT_APPLICATION_SECRET,
    )
    grabzit.UseSSL(True)
    return grabzit


def _docx_attachment(grabzit, prepare_conversion, filename_base, export_host):
    try:
        prepare_conversion()
        # With no path, SaveTo returns the DOCX bytes instead of writing a file,
        # so concurrent exports of the same document can't share a temp file.
        content = grabzit.SaveTo()
        if not isinstance(content, (bytes, bytearray)):
            raise RuntimeError("GrabzIt did not return the DOCX result")
    except Exception as exc:
        # Provider error text can contain sensitive request data.
        logger.error(
            "GrabzIt Word export request failed",
            extra={"export_host": export_host, "error_type": type(exc).__name__},
        )
        return with_word_download_outcome(
            HttpResponse(
                "Word export could not be completed. Please try again later.",
                status=502,
            ),
            "conversion_failed",
        )

    if not is_valid_docx(content):
        logger.error(
            "GrabzIt returned an invalid or empty DOCX",
            extra={"export_host": export_host, "response_size": len(content)},
        )
        return with_word_download_outcome(
            HttpResponse(
                "Word export could not be completed. Please try again later.",
                status=502,
            ),
            "invalid_docx",
        )

    response = HttpResponse(
        content,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename_base}.docx"'
    return with_word_download_outcome(response, "success")
