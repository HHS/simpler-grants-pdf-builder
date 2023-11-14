from django.urls import path

from . import views

app_name = "nofos"
urlpatterns = [
    path("", views.NofosListView.as_view(), name="nofo_list"),
    path("upload", views.nofo_import, name="nofo_import"),
    path("<int:pk>/name", views.nofo_name, name="nofo_name"),
]
