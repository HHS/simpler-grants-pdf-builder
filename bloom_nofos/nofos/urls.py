from django.urls import path

from . import views

app_name = "nofos"
urlpatterns = [
    path("", views.NofosListView.as_view(), name="nofo_list"),
    path("import", views.nofo_import, name="nofo_import"),
    path("<int:pk>/import", views.nofo_import, name="nofo_import_overwrite"),
    path("<int:pk>/import/title", views.nofo_import_title, name="nofo_import_title"),
    path("<int:pk>", views.NofosDetailView.as_view(), name="nofo_detail"),
    path("<int:pk>/edit", views.NofosEditView.as_view(), name="nofo_edit"),
    path("<int:pk>/edit/coach", views.nofo_coach, name="nofo_edit_coach"),
    path("<int:pk>/edit/title", views.nofo_title, name="nofo_edit_title"),
    path(
        "<int:pk>/edit/subsection/<int:subsection_pk>",
        views.nofo_subsection_edit,
        name="subsection_edit",
    ),
]
