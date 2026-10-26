"""Opt-in synthetic localhost profile; never use for a shared deployment."""

import os
import secrets
import socket
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

_base = Path(__file__).resolve().parent
if any((_base / name).exists() for name in (".env", ".env.docker", ".env.production")):
    raise ImproperlyConfigured("Use a clean checkout without dotenv files")
if os.environ.get("IS_PROD") or any(
    value
    and (
        name.startswith(("AWS_", "OPENAI_", "ANTHROPIC_", "DOCRAPTOR_", "GRABZIT_"))
        or name in {"DATABASE_URL", "API_TOKEN", "GENERAL_S3_BUCKET_URL"}
    )
    for name, value in os.environ.items()
):
    raise ImproperlyConfigured("Start the synthetic profile with a clean environment")
_raw_root = os.environ.get("DESIGN_PILOT_ROOT", "")
_root = Path(_raw_root)
if not _raw_root or not _root.is_absolute() or _root.is_symlink() or not _root.is_dir():
    raise ImproperlyConfigured(
        "DESIGN_PILOT_ROOT must name an existing private directory"
    )
if _root.stat().st_uid != os.getuid() or _root.stat().st_mode & 0o077:
    raise ImproperlyConfigured("Run directory must be owned by you and mode 0700")
_key = _root / "session-key"
if (_root / "candidate.sqlite3").is_symlink():
    raise ImproperlyConfigured("Linked databases are not supported")
if not _key.exists():
    with os.fdopen(
        os.open(_key, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w"
    ) as stream:
        stream.write(secrets.token_urlsafe(48))
if (
    _key.is_symlink()
    or _key.stat().st_uid != os.getuid()
    or _key.stat().st_mode & 0o077
):
    raise ImproperlyConfigured("Invalid synthetic session-key file")
os.environ["SECRET_KEY"] = _key.read_text()
os.environ["DATABASE_URL"] = "sqlite:///" + str(_root / "candidate.sqlite3")
os.environ["DEBUG"] = "False"
os.environ["AWS_EC2_METADATA_DISABLED"] = "true"

from .settings import *  # noqa: E402,F403 # isort: skip

DESIGN_PILOT_ENABLED = True
DESIGN_PILOT_ROOT = _root
DEBUG = False
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
SESSION_COOKIE_NAME = "synthetic_design_session"
CSRF_COOKIE_NAME = "synthetic_design_csrf"
LOGIN_REDIRECT_URL = "/design-pilot/"
LOGOUT_REDIRECT_URL = "/users/login/"
MIDDLEWARE = ["nofos.design_pilot_views.LocalPilotBoundary"] + MIDDLEWARE
DOCRAPTOR_API_KEY = GRABZIT_APPLICATION_KEY = GRABZIT_APPLICATION_SECRET = ""
GRABZIT_WORD_EXPORT_ALLOWED_HOSTS = ()
API_TOKEN = GENERAL_S3_BUCKET_URL = None
LOGGING_CONFIG = "logging.config.dictConfig"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "null": {"class": "logging.NullHandler"},
        "console": {"class": "logging.StreamHandler"},
    },
    "loggers": {
        "django.security.csrf": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        }
    },
    "root": {"handlers": ["null"]},
}
DATA_UPLOAD_MAX_MEMORY_SIZE = FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
FILE_UPLOAD_TEMP_DIR = str(_root)


def _deny_connection(*args, **kwargs):
    raise PermissionError("Outbound connections are disabled in the synthetic profile")


# Defense in depth for Python integrations, not an OS/agent sandbox.
socket.socket.connect = socket.socket.connect_ex = _deny_connection
socket.socket.sendto = socket.create_connection = _deny_connection
