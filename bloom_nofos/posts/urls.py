from django.urls import path

from . import views

app_name = "posts"
urlpatterns = [
    path("", views.PostsListView.as_view(), name="posts_list"),
    path("upload", views.simple_upload, name="posts_upload"),
]
