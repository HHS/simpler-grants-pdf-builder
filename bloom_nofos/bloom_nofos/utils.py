import os
import re
import sys

from django.conf import settings
from django.utils.timezone import now, timedelta
from google.cloud import secretmanager


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


def is_docraptor_live_mode_active(last_updated):
    # Check if the timestamp is more than 5 minutes old
    if last_updated and now() - last_updated < get_timedelta_for_docraptor_live_mode():
        return True

    return False


def get_timedelta_for_docraptor_live_mode():
    return timedelta(minutes=5)


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
