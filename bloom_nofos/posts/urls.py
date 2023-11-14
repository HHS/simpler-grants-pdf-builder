from django.urls import path

from . import views

app_name = "posts"
urlpatterns = [
    path("", views.PostsListView.as_view(), name="posts_list"),
    path("upload", views.nofo_upload, name="posts_upload"),
    path("<int:pk>/name", views.nofo_name, name="posts_name"),
]
