from django.shortcuts import render


def index(request):
    return render(request, "index.html")


def page_not_found(request, exception=None):
    return render(request, "404.html", status=404)
