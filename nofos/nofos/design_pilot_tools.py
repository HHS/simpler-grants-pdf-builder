"""Candidate-scoped local transport. Not a model runner or an OS sandbox."""

import hashlib
import json
import re
import secrets
from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.db import OperationalError, transaction
from django.db.models import F
from django.http import Http404, HttpResponse, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from . import design_pilot_host as host
from .design_candidate import DesignRequestError
from .design_candidate_choices import design_capabilities
from .models import DesignPilotCandidate

LIFETIME = timedelta(minutes=20)
MAX_REQUESTS = 100
# A token-bearing request never reaches ordinary human pages or Builder APIs.
TOOL_PATH = re.compile(
    r"/design-pilot/[0-9a-f-]{36}/tools/(?:read|capabilities|operation|html)\Z"
)


def issue_access(user, candidate_id):
    """Trusted human operation. Return plaintext once; persist its digest only."""
    with transaction.atomic():
        run = host.owned_candidate(user, candidate_id)
        host.snapshot(run)
        token = secrets.token_urlsafe(32)
        expires = timezone.now() + LIFETIME
        DesignPilotCandidate.objects.filter(pk=run.pk).update(
            tool_token_digest=hashlib.sha256(token.encode()).hexdigest(),
            tool_expires_at=expires,
            tool_requests=0,
        )
        return token, expires


def revoke_access(user, candidate_id):
    run = host.owned_candidate(user, candidate_id)
    DesignPilotCandidate.objects.filter(pk=run.pk).update(
        tool_token_digest=None,
        tool_expires_at=None,
    )


class CredentialRejected(Exception):
    pass


def _claim(request, candidate_id):
    """Call inside the transaction that executes the selected operation."""
    header = request.headers.get("Authorization", "")
    if not re.fullmatch(r"Bearer [A-Za-z0-9_-]{43}", header):
        raise CredentialRejected
    digest = hashlib.sha256(header[7:].encode()).hexdigest()
    active = DesignPilotCandidate.objects.filter(
        pk=candidate_id,
        tool_token_digest=digest,
        tool_expires_at__gt=timezone.now(),
        tool_requests__lt=MAX_REQUESTS,
    )
    run = active.select_related("owner").first()
    if run is None:
        raise CredentialRejected
    # Ignore request.user/session entirely. Re-fetch the credential owner's
    # active membership and candidate group through the same trusted host.
    try:
        run = host.owned_candidate(run.owner, candidate_id)
    except (Http404, PermissionDenied):
        raise CredentialRejected from None
    if active.update(tool_requests=F("tool_requests") + 1) != 1:
        raise CredentialRejected
    return run


def _error(message, status):
    response = JsonResponse({"error": message}, status=status)
    if status == 401:
        response["WWW-Authenticate"] = 'Bearer realm="synthetic-candidate"'
    return response


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Repeated fields")
        result[key] = value
    return result


def _invalid_constant(_value):
    raise ValueError("Nonfinite value")


def _read(run):
    revision, _ = host.review_artifact(run)
    data = host.snapshot(run).read()
    # The public transport uses the host's render-bound revision, never the
    # internal operation kernel's revision as a substitute.
    data["revision"] = revision
    data["source_name"] = run.source_name
    data["warnings"] = run.warnings
    data["review_url"] = reverse("design_pilot:review", args=[run.pk])
    return JsonResponse(data)


def _dispatch(request, run, action):
    method = "POST" if action == "operation" else "GET"
    if request.method != method:
        response = _error("Method not supported", 405)
        response["Allow"] = method
        return response
    if set(request.GET) - ({"revision"} if action == "html" else set()):
        return _error("Query fields are not supported here", 400)
    if action == "capabilities":
        catalog = design_capabilities()
        catalog["operations"] = ["read", "set_theme", "set_table_width", "html_review"]
        catalog["choices"].pop("cover")
        catalog["html_review"] = {"supported": True, "requires_current_revision": True}
        catalog["limits"] = {
            "requests": MAX_REQUESTS,
            "lifetime_seconds": int(LIFETIME.total_seconds()),
            "operation_bytes": 4096,
        }
        return JsonResponse(catalog)
    if action == "html":
        revision, html = host.review_artifact(run)
        if request.GET.getlist("revision") != [revision]:
            return _error("HTML revision is stale; read the candidate again", 409)
        response = HttpResponse(html)
        response["Content-Security-Policy"] = (
            "sandbox; default-src 'none'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
        )
        return response
    if action == "operation":
        if request.content_type != "application/json" or len(request.body) > 4096:
            return _error(
                "Use an application/json operation no larger than 4096 bytes", 400
            )
        try:
            command = json.loads(
                request.body.decode("utf-8"),
                object_pairs_hook=_unique_object,
                parse_constant=_invalid_constant,
            )
        except (ValueError, UnicodeError, RecursionError):
            return _error("Use a JSON object with unique fields and finite values", 400)
        run = host.update_candidate(run.owner, run.pk, command)
    return _read(run)


@csrf_exempt
def tool(request, candidate_id, action):
    """No session fallback, token issuance, arbitrary command or human authority."""
    host.require_profile()
    try:
        with transaction.atomic():
            run = _claim(request, candidate_id)
            # Savepoint ensures any rendering/CAS failure undoes the design
            # mutation but still consumes the admitted request's quota.
            try:
                with transaction.atomic():
                    response = _dispatch(request, run, action)
            except DesignRequestError as exc:
                response = _error(str(exc), 409)
    except CredentialRejected:
        response = _error("Candidate credential is invalid, expired or exhausted", 401)
    except OperationalError:
        response = _error(
            "Local database is busy; read the candidate before retrying", 409
        )
    response["Cache-Control"] = "no-store"
    response["Referrer-Policy"] = "no-referrer"
    response["X-Content-Type-Options"] = "nosniff"
    return response
