from django.views.generic import ListView
from .models import Post


class PostsListView(ListView):
    model = Post
    template_name = "posts_list.html"
