from django.urls import path

from .views import PostsListView

urlpatterns = [
    path("", PostsListView.as_view(), name="posts_list"),
]
