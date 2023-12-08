from django.contrib.auth.views import redirect_to_login
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import redirect
from django.urls import resolve

from .utils import match_view_url


# https://stackoverflow.com/a/70108758
class NofosLoginRequiredMiddleware:
    """All urls starting with the given prefix require the user to be logged in"""

    APP_NAME = "nofos"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not hasattr(request, "user"):
            raise ImproperlyConfigured(
                "Oops, Django’s authentication middleware is not correctly installed."
            )

        user = request.user
        if (
            resolve(request.path).app_name == self.APP_NAME
        ):  # match app_name defined in myapp.urls.py
            if (
                match_view_url(request.get_full_path())  # is a view URL
                and request.headers.get(settings.VIEW_DOCUMENT_HEADER)  # has header val
                and request.headers.get(settings.VIEW_DOCUMENT_HEADER).startswith(
                    settings.VIEW_DOCUMENT_VALUE  # includes the value we expect
                )
            ):
                pass

            elif not user.is_authenticated:
                path = request.get_full_path()
                return redirect_to_login(path)

            elif user.force_password_reset:
                return redirect("users:user_force_password_reset")

        return self.get_response(request)
