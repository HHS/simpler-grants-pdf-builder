import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from ninja import NinjaAPI
from ninja.security import HttpBearer

from nofos.models import Nofo, Section, Subsection
from nofos.nofo import _build_document

from .schemas import ErrorSchema, NofoSchema, SuccessSchema


class BearerAuth(HttpBearer):
    def authenticate(self, request, token):
        if token and settings.API_TOKEN and token == settings.API_TOKEN:
            return token
        return None


# Create a separate API instance for health check without namespace
health_api = NinjaAPI(auth=None, urls_namespace=None)


@health_api.api_operation(["GET", "HEAD"], "/health", auth=None)
def health_check(request):
    """Health check endpoint that returns 200 OK."""
    return 200, {"status": "ok"}


# Main API instance for other endpoints
api = NinjaAPI(
    auth=BearerAuth(),
    urls_namespace="api",
    docs_url="/docs",
)


@api.post("/nofos", response={201: SuccessSchema, 400: ErrorSchema})
def create_nofo(request, payload: NofoSchema):
    try:
        data = payload.dict(exclude_unset=True)
        sections = data.pop("sections", [])

        # Raise validation error if sections is empty
        if not sections:
            raise ValidationError({"__all__": ["NOFO must have at least one section"]})

        # Remove fields we dont want set on import
        excluded_fields = ["id", "archived", "status", "group"]
        for field in excluded_fields:
            data.pop(field, None)

        # Create NOFO
        nofo = Nofo(**data)
        nofo.group = "bloom"
        nofo.full_clean()
        nofo.save()

        _build_document(nofo, sections, Section, Subsection)
        nofo.save()

        serialized_nofo = NofoSchema.from_orm(nofo)
        return_response = api.create_response(request, serialized_nofo, status=201)
        return_response.headers["Location"] = f"/api/nofos/{nofo.id}"
        return return_response

    except ValidationError as e:
        return 400, {"message": "Model validation error", "details": e.message_dict}
    except Exception as e:
        return 400, {"message": str(e)}


def strip_null_and_blank_nofo_keys(nofo_dict, *, preserve_keys):
    """
    Remove top-level keys whose value is None or "".
    Leaves preserved keys (like "sections") completely untouched.
    """
    cleaned = {}
    for k, v in nofo_dict.items():
        if k in preserve_keys:
            cleaned[k] = v
            continue

        if v is None or v == "":
            continue

        cleaned[k] = v

    return cleaned


@api.get("/nofos/{nofo_id}", response={200: dict, 404: ErrorSchema})
def get_nofo(request, nofo_id: uuid.UUID):
    """Export a NOFO by ID"""
    try:
        nofo = Nofo.objects.get(id=nofo_id, archived__isnull=True)

        nofo_dict = NofoSchema.from_orm(nofo).dict(exclude_none=True)
        # remove blank keys from the dict
        nofo_dict = strip_null_and_blank_nofo_keys(
            nofo_dict, preserve_keys=["sections"]
        )

        # Sort sections and subsections
        nofo_dict["sections"] = sorted(nofo_dict["sections"], key=lambda x: x["order"])
        for section in nofo_dict["sections"]:
            section["subsections"] = sorted(
                section["subsections"], key=lambda x: x["order"]
            )

        # Return raw JSON so Ninja doesn't re-apply NofoSchema and re-add keys
        # the problem with NofoSchema is that it will return keys with blanks and nulls
        return JsonResponse(nofo_dict, status=200)

    except Nofo.DoesNotExist:
        return 404, {"message": "NOFO not found"}
