from django.shortcuts import render


def index(request):
    return render(request, "index.html")


def page_not_found(request, exception=None):
    return render(request, "404.html", status=404)


def server_error(request, exception=None):
    return render(request, "500.html", status=500)


# Note: commenting this out because it is handled by middleware. Explanation in the commit message.
# def bad_request(request, exception=None):
#     return render(request, "400.html", status=400)
