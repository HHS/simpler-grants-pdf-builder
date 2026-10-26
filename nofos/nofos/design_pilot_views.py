"""Human-only UI for the isolated synthetic profile, not an agent transport."""

from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ValidationError
from django.db import OperationalError
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from . import design_pilot_host as host
from . import design_pilot_review as candidate_review
from . import design_pilot_tools as tools
from .design_candidate import DesignRequestError


class LocalPilotBoundary:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.headers.get("Authorization") and not tools.TOOL_PATH.fullmatch(
            request.path
        ):
            return HttpResponseNotFound()
        if request.META.get("REMOTE_ADDR") not in {"127.0.0.1", "::1"} or not (
            request.path.startswith(("/design-pilot/", "/static/"))
            or request.path in {"/users/login/", "/users/logout/"}
        ):
            return HttpResponseNotFound()
        response = self.get_response(request)
        response["Cache-Control"] = "no-store"
        # Preserve same-origin POST Origin on HTTP localhost without disclosing
        # candidate URLs to other sites. no-referrer yields Origin:null here.
        response.setdefault("Referrer-Policy", "same-origin")
        response.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data:; connect-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
        )
        return response


def pilot_view(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        host.require_profile()
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        host.current_owner(request.user)
        return view(request, *args, **kwargs)

    return wrapped


def error(request, message, status=400, *, acknowledgment_reason=""):
    candidate_id = request.resolver_match.kwargs.get("candidate_id")
    return render(
        request,
        "nofos/design_pilot_error.html",
        {
            "message": message,
            "acknowledgment_reason": acknowledgment_reason,
            "candidate_url": (
                reverse("design_pilot:review", args=[candidate_id])
                if candidate_id
                else None
            ),
        },
        status=status,
    )


@pilot_view
@require_http_methods(["GET", "POST"])
def index(request):
    message = ""
    if request.method == "POST":
        if request.POST.get("synthetic") != "yes":
            message = "Confirm that the file contains invented information only."
        else:
            try:
                run = host.import_candidate(request.user, request.FILES.get("source"))
                return redirect("design_pilot:review", candidate_id=run.pk)
            except ValidationError as exc:
                message = " ".join(exc.messages)
            except DesignRequestError as exc:
                message = str(exc)
    return render(
        request,
        "nofos/design_pilot_upload.html",
        {"upload_error": message},
        status=400 if message else 200,
    )


@pilot_view
@require_GET
def review(request, candidate_id):
    return _review_response(request, candidate_id)


def _review_response(request, candidate_id, *, message="", draft=None, status=200):
    try:
        run = host.owned_candidate(request.user, candidate_id)
        report = candidate_review.report(run)
    except DesignRequestError as exc:
        return error(
            request,
            str(exc),
            409,
            acknowledgment_reason=(draft or {}).get("reason", ""),
        )
    except OperationalError:
        return error(
            request,
            "The local database is busy. Return to review before trying again.",
            409,
            acknowledgment_reason=(draft or {}).get("reason", ""),
        )
    draft_restored = False
    if draft:
        for finding in report["findings"]:
            if (
                finding["id"] == draft.get("finding_id")
                and finding["digest"] == draft.get("finding_digest")
                and finding["severity"] == "warning"
                and not finding["decision"]
            ):
                finding["draft_reason"] = draft.get("reason", "")
                draft_restored = True
    access_status = "none"
    if run.tool_token_digest:
        if not run.tool_expires_at or run.tool_expires_at <= timezone.now():
            access_status = "expired"
        elif run.tool_requests >= tools.MAX_REQUESTS:
            access_status = "exhausted"
        else:
            access_status = "active"
    return render(
        request,
        "nofos/design_pilot_review.html",
        {
            "run": run,
            "revision": report["revision"],
            "report": report,
            "review_error": message,
            "acknowledgment_reason": (draft or {}).get("reason", ""),
            "draft_restored": draft_restored,
            "review_sections": run.nofo.sections.order_by(
                "order", "pk"
            ).prefetch_related("subsections"),
            "choices": host.candidate_capabilities(request.user, run)["choices"],
            "sections": run.nofo.sections.order_by("order", "pk"),
            "tool_access_status": access_status,
            "tool_access_active": access_status == "active",
            "tool_request_limit": tools.MAX_REQUESTS,
            "tool_expires_at": run.tool_expires_at,
            "tool_requests": run.tool_requests,
        },
        status=status,
    )


@pilot_view
@require_POST
def acknowledge(request, candidate_id):
    if len(request.body) > 4096 or any(
        len(values) != 1 for _, values in request.POST.lists()
    ):
        return error(request, "Use one current warning review form.")
    command = request.POST.dict()
    command.pop("csrfmiddlewaretoken", None)
    try:
        candidate_review.acknowledge(request.user, candidate_id, command)
    except DesignRequestError as exc:
        return _review_response(
            request, candidate_id, message=str(exc), draft=command, status=409
        )
    except OperationalError:
        return error(
            request,
            "The local database is busy. Return to review before trying again.",
            409,
            acknowledgment_reason=command.get("reason", ""),
        )
    return redirect("design_pilot:review", candidate_id=candidate_id)


@pilot_view
@require_POST
def operation(request, candidate_id):
    if len(request.body) > 4096:
        return error(request, "Design request is too large.")
    if any(len(values) != 1 for _name, values in request.POST.lists()):
        return error(request, "Repeated fields are not supported.")
    command = request.POST.dict()
    command.pop("csrfmiddlewaretoken", None)
    if command.get("operation") == "set_table_width":
        if command.get("value") not in {"true", "false"}:
            return error(request, "Choose a table width.")
        command["value"] = command["value"] == "true"
    try:
        host.update_candidate(request.user, candidate_id, command)
    except DesignRequestError as exc:
        return error(request, str(exc), 409)
    except OperationalError:
        return error(
            request,
            "The local database is busy. Return to review before trying again.",
            409,
        )
    return redirect("design_pilot:review", candidate_id=candidate_id)


@pilot_view
@require_GET
def document(request, candidate_id):
    run = host.owned_candidate(request.user, candidate_id)
    try:
        revision, html = host.review_artifact(run)
        if request.GET.get("revision") != revision:
            raise DesignRequestError(
                "This review link is stale. Return to the candidate for its current HTML."
            )
    except DesignRequestError as exc:
        return error(request, str(exc), 409)
    response = HttpResponse(html)
    response["Content-Security-Policy"] = (
        "sandbox; default-src 'none'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    )
    response["Cache-Control"] = "no-store"
    response["Referrer-Policy"] = "no-referrer"
    return response


@pilot_view
@require_POST
def issue_access(request, candidate_id):
    try:
        token, expires = tools.issue_access(request.user, candidate_id)
    except DesignRequestError as exc:
        return error(request, str(exc), 409)
    response = render(
        request,
        "nofos/design_pilot_access.html",
        {
            "token": token,
            "expires": expires,
            "candidate_id": candidate_id,
        },
    )
    response["Cache-Control"] = "no-store"
    return response


@pilot_view
@require_POST
def revoke_access(request, candidate_id):
    tools.revoke_access(request.user, candidate_id)
    return redirect("design_pilot:review", candidate_id=candidate_id)
