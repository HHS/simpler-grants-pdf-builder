from django.urls import path

from . import views

app_name = "nofos"
urlpatterns = [
    path("", views.NofosListView.as_view(), name="nofo_list"),
    path("upload", views.nofo_import, name="nofo_import"),
    path("<int:pk>", views.NofosDetailView.as_view(), name="nofo_detail"),
    path("<int:pk>/edit", views.NofosEditView.as_view(), name="nofo_edit"),
    path("<int:pk>/edit/name", views.nofo_name, name="edit_name"),
]
