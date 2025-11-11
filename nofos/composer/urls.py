from django.urls import path

from . import views

app_name = "composer"

urlpatterns = [
    path("", views.ComposerListView.as_view(), name="composer_index"),
    path("import", views.ComposerImportView.as_view(), name="composer_import"),
    path(
        "<uuid:pk>/import/title",
        views.ComposerImportTitleView.as_view(),
        name="composer_import_title",
    ),
    path(
        "<uuid:pk>/delete", views.ComposerArchiveView.as_view(), name="composer_archive"
    ),
    path(
        "<uuid:pk>/history",
        views.ComposerHistoryView.as_view(),
        name="composer_history",
    ),
    path(
        "<uuid:pk>",
        views.compare_section_redirect,
        name="composer_document_redirect",
    ),
    path(
        "<uuid:pk>/edit/title",
        views.ComposerEditTitleView.as_view(),
        name="composer_edit_title",
    ),
    path(
        "<uuid:pk>/section/<uuid:section_pk>",
        views.ComposerSectionView.as_view(),
        name="section_view",
    ),
    path(
        "<uuid:pk>/preview",
        views.ComposerPreviewView.as_view(),
        name="composer_preview",
    ),
    path(
        "<uuid:pk>/section/<uuid:section_pk>/subsection/create",
        views.ComposerSubsectionCreateView.as_view(),
        name="subsection_create",
    ),
    path(
        "<uuid:pk>/section/<uuid:section_pk>/subsection/<uuid:subsection_pk>/edit",
        views.ComposerSubsectionEditView.as_view(),
        name="subsection_edit",
    ),
    path(
        "<uuid:pk>/section/<uuid:section_pk>/subsection/<uuid:subsection_pk>/delete",
        views.ComposerSubsectionDeleteView.as_view(),
        name="subsection_confirm_delete",
    ),
    path(
        "<uuid:pk>/section/<uuid:section_pk>/subsection/<uuid:subsection_pk>/instructions/edit",
        views.ComposerSubsectionInstructionsEditView.as_view(),
        name="instructions_edit",
    ),
]
