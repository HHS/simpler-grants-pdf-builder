"""
URL configuration for bloom_nofos project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path, re_path
from django.views.generic.base import RedirectView
from nofos.api.api import api

from . import views

handler404 = views.page_not_found
handler500 = views.server_error


favicon_view = RedirectView.as_view(url="/static/favicon/favicon.ico", permanent=True)

admin.site.site_header = "NOFO Builder admin area"  # default: "Django Administration"
admin.site.index_title = "Dashboard"  # default: "Site administration"
admin.site.site_title = "NOFO Builder admin area"  # default: "Django site admin"

app_name = "bloom_nofos"
urlpatterns = [
    re_path(
        r"^robots.txt",
        lambda x: HttpResponse("User-Agent: *\nDisallow: /", content_type="text/plain"),
        name="robots_file",
    ),
    re_path(r"^favicon\.ico$", favicon_view),
    path("martor/", include("martor.urls")),
    path("nofos/", include("nofos.urls")),
    path("guides/", include("guides.urls")),
    path("users/", include("users.urls")),
    path("admin/", admin.site.urls),
    path("test-mode", views.TestModeView.as_view(), name="test_mode"),
    path("", views.index, name="index"),
    path("404/", views.page_not_found),
    path("api/", api.urls),
]
