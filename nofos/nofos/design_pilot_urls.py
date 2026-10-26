from django.urls import path

from . import design_pilot_tools as tools
from . import design_pilot_views as views

app_name = "design_pilot"
urlpatterns = [
    path("", views.index, name="index"),
    path("<uuid:candidate_id>/", views.review, name="review"),
    path("<uuid:candidate_id>/operation", views.operation, name="operation"),
    path("<uuid:candidate_id>/acknowledge", views.acknowledge, name="acknowledge"),
    path("<uuid:candidate_id>/html", views.document, name="document"),
    path("<uuid:candidate_id>/access", views.issue_access, name="issue_access"),
    path(
        "<uuid:candidate_id>/access/revoke", views.revoke_access, name="revoke_access"
    ),
    *[
        path(
            f"<uuid:candidate_id>/tools/{action}",
            tools.tool,
            {"action": action},
            name=f"tool_{action}",
        )
        for action in ("read", "capabilities", "operation", "html")
    ],
]
