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
    path(
        "<int:pk>/compare",
        views.ContentGuideCompareView.as_view(),
        name="guide_compare",
    ),
    path(
        "<int:pk>/edit/title",
        views.ContentGuideEditTitleView.as_view(),
        name="guide_edit_title",
    ),
    path(
        "guides/<int:pk>/section/<int:section_pk>/subsection/<int:subsection_pk>/edit",
        views.ContentGuideSubsectionEditView.as_view(),
        name="subsection_edit",
    ),
]
