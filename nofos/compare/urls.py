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
    # path(
    #     "import/document/<uuid:pk>",
    #     views.ContentGuideDuplicateView.as_view(),
    #     name="guide_duplicate",
    # ),
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
    # path(
    #     "<uuid:pk>/compare",
    #     views.ContentGuideCompareView.as_view(),
    #     name="guide_compare",
    # ),
    path(
        "<uuid:pk>/import/to-doc",
        views.CompareImportToDocView.as_view(),
        name="compare_import_to_doc",
    ),
    # path(
    #     "<uuid:pk>/compare/<uuid:new_nofo_id>",
    #     views.ContentGuideCompareView.as_view(),
    #     name="guide_compare_result",
    # ),
    # path(
    #     "<uuid:pk>/compare/<uuid:new_nofo_id>/csv/",
    #     views.ContentGuideDiffCSVView.as_view(),
    #     name="guide_compare_result_csv",
    # ),
    # path(
    #     "<uuid:pk>/section/<uuid:section_pk>/subsection/<uuid:subsection_pk>/edit",
    #     views.ContentGuideSubsectionEditView.as_view(),
    #     name="subsection_edit",
    # ),
]
