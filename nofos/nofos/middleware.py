from bloom_nofos.utils import parse_docraptor_ip_addresses
from constance import config
from django.contrib.auth.views import redirect_to_login
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

        resolved = resolve(request.path)

        if resolved.app_name == self.APP_NAME:
            safe_ips = parse_docraptor_ip_addresses(config.DOCRAPTOR_IPS)
            incoming_ip = request.headers.get("x-forwarded-for")
            is_view_url = match_view_url(request.get_full_path())
            is_secure = request.is_secure()

            print(
                "[NOFOS_LOGIN_MIDDLEWARE]",
                {
                    "path": request.get_full_path(),
                    "host": request.get_host(),
                    "method": request.method,
                    "user_authenticated": user.is_authenticated,
                    "user_id": getattr(user, "id", None),
                    "incoming_ip": incoming_ip,
                    "is_view_url": is_view_url,
                    "is_secure": is_secure,
                    "incoming_ip_in_docraptor_allowlist": bool(
                        incoming_ip and incoming_ip in safe_ips
                    ),
                },
                flush=True,
            )

            if (
                is_view_url
                and is_secure
                and incoming_ip
                and len(incoming_ip)
                and incoming_ip in safe_ips
            ):
                print(
                    "[NOFOS_LOGIN_MIDDLEWARE_ALLOW_DOC_RAPTOR_IP]",
                    {
                        "incoming_ip": incoming_ip,
                        "path": request.get_full_path(),
                    },
                    flush=True,
                )
                pass

            elif not user.is_authenticated:
                path = request.get_full_path()
                print(
                    "[NOFOS_LOGIN_MIDDLEWARE_REDIRECT_TO_LOGIN]",
                    {
                        "path": path,
                        "host": request.get_host(),
                        "incoming_ip": incoming_ip,
                        "cookies_present": list(request.COOKIES.keys()),
                    },
                    flush=True,
                )
                return redirect_to_login(path)

            elif user.force_password_reset:
                print(
                    "[NOFOS_LOGIN_MIDDLEWARE_FORCE_PASSWORD_RESET]",
                    {
                        "user_id": user.id,
                        "path": request.get_full_path(),
                    },
                    flush=True,
                )
                return redirect("users:user_force_password_reset")

        return self.get_response(request)
