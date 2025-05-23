from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from easy_audit.models import CRUDEvent, LoginEvent, RequestEvent


# Resources
class CRUDEventResource(resources.ModelResource):
    class Meta:
        model = CRUDEvent


class LoginEventResource(resources.ModelResource):
    class Meta:
        model = LoginEvent


class RequestEventResource(resources.ModelResource):
    class Meta:
        model = RequestEvent


# Admin classes with import/export enabled
@admin.register(CRUDEvent)
class CRUDEventAdmin(ImportExportModelAdmin):
    resource_classes = [CRUDEventResource]


@admin.register(LoginEvent)
class LoginEventAdmin(ImportExportModelAdmin):
    resource_classes = [LoginEventResource]


@admin.register(RequestEvent)
class RequestEventAdmin(ImportExportModelAdmin):
    resource_classes = [RequestEventResource]
