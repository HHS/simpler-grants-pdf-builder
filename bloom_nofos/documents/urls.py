from django.urls import path

from . import views

app_name = "documents"
urlpatterns = [
    # ex: /documents/
    path("", views.IndexView.as_view(), name="index"),
    # ex: /documents/5/
    path("<int:pk>/", views.DetailView.as_view(), name="detail"),
    path("<int:pk>/edit/title", views.edit_title, name="edit_title"),
]
