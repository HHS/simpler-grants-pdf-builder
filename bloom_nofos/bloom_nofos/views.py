from constance import config
from django.contrib.auth.views import RedirectURLMixin
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import TemplateView

from .forms import DocraptorTestModeForm


def index(request):
    return render(request, "index.html")


def page_not_found(request, exception=None):
    return render(request, "404.html", status=404)


def server_error(request, exception=None):
    return render(request, "500.html", status=500)


class TestModeView(RedirectURLMixin, TemplateView):
    template_name = "docraptor_test_mode.html"

    def post(self, request, *args, **kwargs):
        form = DocraptorTestModeForm(request.POST)
        if form.is_valid():
            setattr(
                config, "DOCRAPTOR_TEST_MODE", form.cleaned_data["docraptor_test_mode"]
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
