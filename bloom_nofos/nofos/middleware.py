from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ImproperlyConfigured

from django.urls import resolve


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
            if not user.is_authenticated:
                path = request.get_full_path()
                return redirect_to_login(path)

        return self.get_response(request)
