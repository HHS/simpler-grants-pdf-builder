from ninja import NinjaAPI, Schema
from ninja.security import HttpBearer
from django.core.exceptions import ValidationError
from .schemas import NofoSchema, ErrorSchema, SuccessSchema
from nofos.models import Nofo
from nofos.views import _build_nofo
from django.conf import settings


class BearerAuth(HttpBearer):
    def authenticate(self, request, token):
        if token and settings.API_TOKEN and token == settings.API_TOKEN:
            return token
        return None


api = NinjaAPI(
    auth=BearerAuth(),
    urls_namespace="api",
    docs_url="/docs",
)


@api.post("/nofo/import", response={201: SuccessSchema, 400: ErrorSchema})
def import_nofo(request, payload: NofoSchema):
    try:
        data = payload.dict()
        sections = data.pop("sections", [])

        # Remove fields we dont want set on import
        excluded_fields = ["id", "archived", "status", "group"]
        for field in excluded_fields:
            data.pop(field, None)

        # Create NOFO
        nofo = Nofo(**data)
        nofo.group = "bloom"
        nofo.full_clean()
        nofo.save()

        _build_nofo(nofo, sections)
        nofo.save()

        return 201, {"message": f"NOFO {nofo.number} imported successfully"}
    except ValidationError as e:
        return 400, {"message": "Model validation error", "details": e.message_dict}
    except Exception as e:
        return 400, {"message": str(e)}


@api.get("/nofo/{nofo_id}", response={200: NofoSchema, 404: ErrorSchema})
def export_nofo(request, nofo_id: int):
    """Export a NOFO by ID"""
    try:
        nofo = Nofo.objects.get(id=nofo_id, archived__isnull=True)
        return 200, nofo
    except Nofo.DoesNotExist:
        return 404, {"message": "NOFO not found"}
