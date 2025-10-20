from django.urls import path

from . import views

app_name = "composer"

urlpatterns = [
    path("", views.ComposerListView.as_view(), name="composer_index"),
    path("import/", views.ComposerImportView.as_view(), name="composer_import"),
    path(
        "<uuid:pk>/delete", views.ComposerArchiveView.as_view(), name="composer_archive"
    ),
]
