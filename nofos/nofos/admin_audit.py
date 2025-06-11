from django.contrib import admin
from easyaudit.models import CRUDEvent, LoginEvent, RequestEvent
from import_export import resources
from import_export.admin import ImportExportModelAdmin


def safe_unregister(model):
    if model in admin.site._registry:
        admin.site.unregister(model)


safe_unregister(CRUDEvent)
safe_unregister(LoginEvent)
safe_unregister(RequestEvent)


# Resources
class CRUDEventResource(resources.ModelResource):
    class Meta:
        model = CRUDEvent
        use_bulk = True
        batch_size = 10000


class LoginEventResource(resources.ModelResource):
    class Meta:
        model = LoginEvent
        use_bulk = True
        batch_size = 10000


class RequestEventResource(resources.ModelResource):
    class Meta:
        model = RequestEvent
        use_bulk = True
        batch_size = 10000


# Admin classes with import/export enabled
@admin.register(CRUDEvent)
class CRUDEventAdmin(ImportExportModelAdmin):
    resource_classes = [CRUDEventResource]

    list_display = [
        "event_type",
        "content_type",
        "object_id",
        "object_repr",
        "user",
        "datetime",
    ]
    date_hierarchy = "datetime"


@admin.register(LoginEvent)
class LoginEventAdmin(ImportExportModelAdmin):
    resource_classes = [LoginEventResource]

    list_display = [
        "datetime",
        "login_type",
        "user",
        "username",
        "remote_ip",
    ]
    date_hierarchy = "datetime"


@admin.register(RequestEvent)
class RequestEventAdmin(ImportExportModelAdmin):
    resource_classes = [RequestEventResource]

    list_display = ["datetime", "user", "method", "url", "remote_ip"]
    date_hierarchy = "datetime"
