from django.urls import path

from . import views

app_name = "composer"

urlpatterns = [
    path("", views.ComposerListView.as_view(), name="composer_index"),
    path("import", views.ComposerImportView.as_view(), name="composer_import"),
    path(
        "<uuid:pk>/delete", views.ComposerArchiveView.as_view(), name="composer_archive"
    ),
    path(
        "<uuid:pk>",
        views.guide_section_redirect,
        name="composer_document_redirect",
    ),
    path(
        "<uuid:pk>/section/<uuid:section_pk>",
        views.GuideSectionView.as_view(),
        name="composer_document_section",
    ),
]
