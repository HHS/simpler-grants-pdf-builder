from django.views.generic import ListView
from django.shortcuts import render

from .models import Post


class PostsListView(ListView):
    model = Post


def simple_upload(request):
    if request.method == "POST" and request.FILES["myfile"]:
        myfile = request.FILES["myfile"]
        # first_line = ""
        # with open(myfile) as f:
        first_line = myfile.readline()

        print("FIRST_LINE: {}".format(first_line))
        return render(request, "posts/upload.html", {"uploaded_file_url": first_line})
    return render(request, "posts/upload.html")
