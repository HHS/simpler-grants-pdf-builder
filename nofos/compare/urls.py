from django.urls import path

from . import views

app_name = "compare"

urlpatterns = [
    path("", views.CompareListView.as_view(), name="compare_index"),
    path(
        "import",
        views.CompareImportView.as_view(),
        name="compare_import",
    ),
    path(
        "import/duplicate/<uuid:pk>",
        views.CompareDuplicateView.as_view(),
        name="compare_duplicate",
    ),
    path(
        "<uuid:pk>/import/title",
        views.CompareImportTitleView.as_view(),
        name="compare_import_title",
    ),
    path(
        "<uuid:pk>/delete",
        views.CompareArchiveView.as_view(),
        name="compare_archive",
    ),
    path("<uuid:pk>/edit", views.CompareEditView.as_view(), name="compare_edit"),
    path(
        "<uuid:pk>/edit/title",
        views.CompareEditTitleView.as_view(),
        name="compare_edit_title",
    ),
    path(
        "<uuid:pk>/edit/group",
        views.CompareEditGroupView.as_view(),
        name="compare_edit_group",
    ),
    path(
        "<uuid:pk>/document",
        views.CompareDocumentView.as_view(),
        name="compare_document",
    ),
    path(
        "<uuid:pk>/import/document",
        views.CompareImportToDocView.as_view(),
        name="compare_import_to_doc",
    ),
    path(
        "<uuid:pk>/document/<uuid:new_nofo_id>",
        views.CompareDocumentView.as_view(),
        name="compare_document_result",
    ),
    path(
        "<uuid:pk>/document/<uuid:new_nofo_id>/csv",
        views.CompareDocumentCSVView.as_view(),
        name="compare_document_result_csv",
    ),
]
