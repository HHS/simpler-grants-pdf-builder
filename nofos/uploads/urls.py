from django.urls import path

from . import views

urlpatterns = [
    path("images/", views.ImageListView.as_view(), name="uploads_images"),
]
