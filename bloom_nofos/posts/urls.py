from django.urls import path

from .views import PostsListView

app_name = "posts"
urlpatterns = [
    path("", PostsListView.as_view(), name="posts_list"),
]
