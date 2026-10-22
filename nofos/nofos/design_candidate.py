"""Pure operation rules for synthetic design candidates, not a security sandbox.

The trusted host owns the current snapshot, identity, choices and persistence.
Never expose a Python interpreter or let document/agent input construct these
objects. No authentication, database write, HTML/PDF render or acceptance occurs
here. A host must atomically compare and replace its authoritative revision.
"""

import hashlib
import json
from dataclasses import dataclass, replace


class DesignRequestError(ValueError):
    """A request is outside the candidate's declared capabilities."""


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class DesignCandidate:
    candidate_id: str
    source_sha256: str
    content_json: str
    presentation_json: str
    changes_json: str = "[]"
    sequence: int = 0

    @classmethod
    def create(cls, candidate_id, source_sha256, content, presentation):
        """Trusted-host constructor; imported content is opaque immutable data."""
        if not isinstance(candidate_id, str) or not candidate_id:
            raise DesignRequestError("Host candidate identity is required")
        if (
            not isinstance(source_sha256, str)
            or len(source_sha256) != 64
            or any(char not in "0123456789abcdef" for char in source_sha256)
        ):
            raise DesignRequestError("Host source SHA-256 is required")
        if not isinstance(presentation, dict) or set(presentation) != {
            "theme",
            "cover",
            "section_table_width",
        }:
            raise DesignRequestError("Unsupported presentation structure")
        widths = presentation["section_table_width"]
        if not isinstance(widths, dict) or any(
            not isinstance(key, str) or not key or type(value) is not bool
            for key, value in widths.items()
        ):
            raise DesignRequestError("Section widths must be host-bound booleans")
        return cls(candidate_id, source_sha256, _json(content), _json(presentation))

    @property
    def revision(self):
        return hashlib.sha256(
            _json(
                {
                    "candidate": self.candidate_id,
                    "source": self.source_sha256,
                    "content": self.content_json,
                    "presentation": self.presentation_json,
                    "changes": self.changes_json,
                    "sequence": self.sequence,
                }
            ).encode()
        ).hexdigest()

    def read(self):
        """Return detached JSON data, never a mutable reference to host state."""
        return {
            "candidate_id": self.candidate_id,
            "source_sha256": self.source_sha256,
            "revision": self.revision,
            "content": json.loads(self.content_json),
            "presentation": json.loads(self.presentation_json),
            "changes": json.loads(self.changes_json),
        }


def apply_design_request(candidate, request, *, choices):
    """Validate one bounded mutation and return a new immutable snapshot.

    Choices come from the trusted application, not the request. Read/HTML review
    transport, authorization and authoritative compare-and-swap are host work.
    """
    if not isinstance(request, dict):
        raise DesignRequestError("Request must be an object")
    try:
        if len(_json(request).encode()) > 4096:
            raise DesignRequestError("Request exceeds operation limit")
    except (TypeError, ValueError, RecursionError):
        raise DesignRequestError("Request must contain bounded JSON data") from None
    operation = request.get("operation")
    fields = {"operation", "candidate_id", "expected_revision", "value", "reason"}
    if operation == "set_table_width":
        fields.add("section_id")
    elif operation not in ("set_theme", "set_cover"):
        raise DesignRequestError("Unsupported operation")
    if set(request) != fields:
        raise DesignRequestError("Unexpected or missing operation fields")
    if request["candidate_id"] != candidate.candidate_id:
        raise DesignRequestError("Candidate is outside this binding")
    if request["expected_revision"] != candidate.revision:
        raise DesignRequestError("Candidate revision is stale")
    reason = request["reason"]
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
        raise DesignRequestError("A bounded change rationale is required")
    presentation = json.loads(candidate.presentation_json)
    value = request["value"]
    if operation == "set_table_width":
        target = request["section_id"]
        widths = presentation["section_table_width"]
        if (
            not isinstance(target, str)
            or target not in widths
            or type(value) is not bool
        ):
            raise DesignRequestError("Invalid section or table width")
        before = widths[target]
        widths[target] = value
    else:
        target = operation.removeprefix("set_")
        if not isinstance(value, str) or value not in choices[target]:
            raise DesignRequestError("Value is not an application choice")
        before = presentation[target]
        presentation[target] = value
    if before == value:
        return candidate
    if candidate.sequence >= 100:
        raise DesignRequestError("Candidate operation budget exhausted")
    changes = json.loads(candidate.changes_json)
    changes.append(
        {
            "operation": operation,
            "target": target,
            "before": before,
            "after": value,
            "reason": reason,
            "before_revision": candidate.revision,
        }
    )
    return replace(
        candidate,
        presentation_json=_json(presentation),
        changes_json=_json(changes),
        sequence=candidate.sequence + 1,
    )
