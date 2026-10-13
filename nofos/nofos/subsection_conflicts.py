"""Signed, content-based edit tokens; no persisted version counter is needed."""

import hashlib
import json

from django.core import signing

EDIT_FIELDS = ("name", "tag", "callout_box", "html_class", "body")
TOKEN_SALT = "nofos.subsection-edit.version"
RECOVERY_SALT = "nofos.subsection-edit.recovery"


def saved_values(subsection):
    return {field: getattr(subsection, field) for field in EDIT_FIELDS}


def version_token(subsection):
    serialized = json.dumps(saved_values(subsection), sort_keys=True)
    digest = hashlib.sha256(serialized.encode()).hexdigest()
    return signing.dumps({"pk": str(subsection.pk), "digest": digest}, salt=TOKEN_SALT)


def read_version(token, subsection):
    try:
        payload = signing.loads(token, salt=TOKEN_SALT)
        if payload["pk"] == str(subsection.pk):
            return payload
    except (signing.BadSignature, TypeError, ValueError, KeyError):
        pass
    return None


def matches_version(token, subsection):
    return read_version(token, subsection) == signing.loads(
        version_token(subsection), salt=TOKEN_SALT
    )


def recovery_token(subsection, values):
    return signing.dumps(
        {"pk": str(subsection.pk), "values": values}, salt=RECOVERY_SALT, compress=True
    )


def recovery_values(token, subsection):
    try:
        payload = signing.loads(token, salt=RECOVERY_SALT)
        if payload["pk"] == str(subsection.pk):
            return payload["values"]
    except (signing.BadSignature, TypeError, ValueError, KeyError):
        pass
    return None
