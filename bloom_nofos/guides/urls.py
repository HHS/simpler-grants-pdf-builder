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
    path(
        "<uuid:pk>/import/title",
        views.ContentGuideImportTitleView.as_view(),
        name="guide_import_title",
    ),
    path(
        "<uuid:pk>/delete",
        views.ContentGuideArchiveView.as_view(),
        name="guide_archive",
    ),
    path("<uuid:pk>/edit", views.ContentGuideEditView.as_view(), name="guide_edit"),
    path(
        "<uuid:pk>/edit/title",
        views.ContentGuideEditTitleView.as_view(),
        name="guide_edit_title",
    ),
    path(
        "<uuid:pk>/compare",
        views.ContentGuideCompareView.as_view(),
        name="guide_compare",
    ),
    path(
        "guides/<uuid:pk>/section/<uuid:section_pk>/subsection/<uuid:subsection_pk>/edit",
        views.ContentGuideSubsectionEditView.as_view(),
        name="subsection_edit",
    ),
]
