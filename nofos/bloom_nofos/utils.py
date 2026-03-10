import os
import re
import sys
from socket import gaierror, gethostbyname, gethostname
from urllib.parse import urlparse

from django.conf import settings
from django.http import HttpResponse, HttpResponseServerError
from google.cloud import secretmanager
from GrabzIt import GrabzItClient, GrabzItDOCXOptions


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


_secret_manager_client = None


def get_secret_manager_client():
    global _secret_manager_client
    if _secret_manager_client is None:
        _secret_manager_client = secretmanager.SecretManagerServiceClient()
    return _secret_manager_client


def get_secret(secret_id: str) -> str:
    """Fetches a secret from Google Cloud Secret Manager."""
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        if settings.DEBUG:
            print(
                "[bloom_nofos.utils.get_secret] No GOOGLE_CLOUD_PROJECT, cannot fetch '{}'".format(
                    secret_id
                )
            )
        return ""

    try:
        client = get_secret_manager_client()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        if settings.DEBUG:
            print(
                "[bloom_nofos.utils.get_secret] Error accessing secret '{}': {}".format(
                    secret_id, str(e)
                )
            )
        return ""


def get_login_gov_keys(environment: str = "dev", testing: bool = "test" in sys.argv):
    """Get Login.gov keys.
    Private key from Secret Manager, public key from filesystem."""
    if testing:
        return "test_key", "test_key"

    # Get private key from Secret Manager
    private_key = get_secret("login-gov-private-key-{}".format(environment))

    # Read public key from filesystem
    cert_path = "bloom_nofos/certs/login-gov-public-key-{}.crt".format(environment)
    try:
        with open(cert_path) as f:
            public_key = f.read()
    except:
        public_key = ""

    return private_key, public_key


def generate_docx_download_response(
    *,
    request,
    export_url: str,
    target_element: str,
    filename_base: str,
    tmp_name: str,
):
    """
    Convert a URL to DOCX using GrabzIt and return it as an attachment response.
    """
    session_value = request.COOKIES.get("sessionid")
    csrf_value = request.COOKIES.get("csrftoken")

    if not session_value or not csrf_value:
        return HttpResponseServerError(
            "Missing session/csrf cookies for DOCX conversion."
        )

    parsed = urlparse(export_url)
    export_host = parsed.hostname
    export_scheme = parsed.scheme

    if not export_host or export_scheme != "https":
        return HttpResponseServerError("Invalid export URL for DOCX conversion.")

    request_host = request.get_host().split(":")[0]

    # Defensive check: the cookies we are copying came from this incoming request,
    # so the request host should match the host GrabzIt will fetch.
    if request_host != export_host:
        return HttpResponseServerError(
            f"Host mismatch for DOCX conversion. request_host={request_host}, export_host={export_host}"
        )

    grabzit = GrabzItClient.GrabzItClient(
        settings.GRABZIT_APPLICATION_KEY,
        settings.GRABZIT_APPLICATION_SECRET,
    )

    # Set cookies only for the exact host GrabzIt will request.
    if not grabzit.SetCookie("sessionid", export_host, session_value):
        return HttpResponseServerError(
            "Failed to set session cookie for GrabzIt conversion."
        )

    if not grabzit.SetCookie("csrftoken", export_host, csrf_value):
        return HttpResponseServerError(
            "Failed to set csrf cookie for GrabzIt conversion."
        )

    options = GrabzItDOCXOptions.GrabzItDOCXOptions()
    options.targetElement = target_element

    grabzit.URLToDOCX(export_url, options)

    file_path = f"/tmp/{tmp_name}.docx"
    grabzit.SaveTo(file_path)

    with open(file_path, "rb") as f:
        content = f.read()

    # Optional cleanup (safe even if it fails)
    try:
        os.remove(file_path)
    except OSError:
        pass

    response = HttpResponse(
        content,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename_base}.docx"'
    return response
