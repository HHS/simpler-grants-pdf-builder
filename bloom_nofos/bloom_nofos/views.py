from constance import config
from django.contrib.auth.views import RedirectURLMixin
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.timezone import now, timedelta
from django.views.generic import TemplateView

from .forms import DocraptorTestModeForm


def index(request):
    # Redirect logged-in users to the NOFO index page
    if request.user.is_authenticated:
        return redirect("nofos:nofo_index")

    return render(request, "index.html")


def page_not_found(request, exception=None):
    return render(request, "404.html", status=404)


def server_error(request, exception=None):
    return render(request, "500.html", status=500)


class TestModeView(RedirectURLMixin, TemplateView):
    template_name = "docraptor_live_mode.html"

    def post(self, request, *args, **kwargs):
        form = DocraptorTestModeForm(request.POST)
        if form.is_valid():

            # If LIVE MODE is TRUE, set the timestamp to the current time
            if form.cleaned_data["docraptor_live_mode"]:
                # Set the timestamp to 5 minutes and 1 second in the past
                setattr(config, "DOCRAPTOR_LIVE_MODE", now())

            # If LIVE MODE is False, set the timestamp to 2 mins and 1 second
            else:
                # Set the timestamp to the current time
                setattr(
                    config,
                    "DOCRAPTOR_LIVE_MODE",
                    now() - timedelta(minutes=2, seconds=1),
                )

            next_url = request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts=request.get_host()
            ):
                return redirect(next_url)

        return self.render_to_response({"form": form})


# Note: commenting this out because it is handled by middleware. Explanation in the commit message.
# def bad_request(request, exception=None):
#     return render(request, "400.html", status=400)
