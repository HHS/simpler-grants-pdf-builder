from django.urls import path
from . import views

app_name = "guides"

urlpatterns = [
    path("", views.ContentGuideListView.as_view(), name="guide_index"),
    path(
        "import",
        views.ContentGuideImportView.as_view(),
        name="guide_import",
    ),
    path("<int:pk>/edit", views.ContentGuideEditView.as_view(), name="guide_edit"),
]
