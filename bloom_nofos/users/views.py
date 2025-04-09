import csv

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.views import PasswordChangeView
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView, FormView

from .auth.login_gov import LoginGovClient
from .exports import export_nofo_report
from .forms import BloomUserNameForm, ExportNofoReportForm, LoginForm
from .models import BloomUser


class BloomUserDetailView(DetailView):
    model = BloomUser
    template_name = "users/user_view.html"

    def get_object(self):
        """
        Returns the request's user.
        """
        return self.request.user

    def get_context_data(self, **kwargs):
        """Pass the NOFO export form to the template."""
        context = super().get_context_data(**kwargs)
        context["nofo_export_form"] = ExportNofoReportForm()  # Add the form
        return context


class BloomPasswordChangeView(PasswordChangeView):
    form_class = SetPasswordForm
    template_name = "users/user_edit_password.html"
    title = "Change your password"
    success_url = reverse_lazy("users:user_view")
    force_password_reset = False

    def form_valid(self, form):
        messages.success(self.request, "You changed your password.")

        # once the form is successfully submitted, set "force_password_change" to False
        self.request.user.force_password_reset = False
        self.request.user.save()

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["force_password_reset"] = self.kwargs.get(
            "force_password_reset", self.force_password_reset
        )
        return context


class BloomUserNameView(View):
    model = BloomUser
    form_class = BloomUserNameForm
    template_name = "users/user_edit_name.html"

    def get(self, request):
        form = self.form_class(instance=request.user)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            full_name = request.POST["full_name"]
            request.user.full_name = full_name
            request.user.save()

            messages.success(self.request, "You changed your name.")
            return redirect("users:user_view")

        return render(request, self.template_name, {"form": form})


###########################################################
####################### DATA EXPORTS ######################
###########################################################


class ExportNofoReportView(FormView):
    template_name = "users/export_nofo_report.html"
    form_class = ExportNofoReportForm

    def get_filename(self, group, start_date, end_date):
        # Determine the file name based on provided dates.
        base_filename = "nb_export_user"
        if start_date and end_date:
            # Both dates provided: use both.
            return "{}_{}_{}.csv".format(
                base_filename, start_date.isoformat(), end_date.isoformat()
            )
        elif start_date or end_date:
            # Only one date provided: use whichever is not None.
            provided_date = start_date if start_date else end_date
            return "{}_{}.csv".format(base_filename, provided_date.isoformat())

        return "{}.csv".format(base_filename)

    def form_valid(self, form):
        # Get the date range from the validated form
        start_date = form.cleaned_data.get("start_date")
        end_date = form.cleaned_data.get("end_date")
        csv_rows = export_nofo_report(
            start_date=start_date, end_date=end_date, user=self.request.user
        )

        # Prepare CSV response
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="{}"'.format(
            self.get_filename(group=None, start_date=start_date, end_date=end_date)
        )
        writer = csv.writer(response)
        for row in csv_rows:
            writer.writerow(row)

        return response

    def form_invalid(self, form):
        # If the form is invalid, simply re-render the export page with errors.
        return self.render_to_response(self.get_context_data(form=form))


###########################################################
####################### AUTH ROUTES #######################
###########################################################


def login_view(request):
    """Initiate Login.gov authentication flow."""
    client = LoginGovClient()
    auth_url, state, nonce = client.get_authorization_url()

    # Store state and nonce in session for validation in callback
    request.session["login_gov_state"] = state
    request.session["login_gov_nonce"] = nonce

    return redirect(auth_url)


@require_http_methods(["GET"])
def callback(request):
    """Handle Login.gov callback."""
    error = request.GET.get("error")
    if error:
        messages.error(request, f"Login.gov error: {error}")
        return redirect(settings.LOGIN_URL)

    # Validate state
    state = request.GET.get("state")
    stored_state = request.session.get("login_gov_state")
    if not state or state != stored_state:
        messages.error(request, "Invalid state parameter")
        return redirect(settings.LOGIN_URL)

    # Get the authorization code
    code = request.GET.get("code")
    if not code:
        messages.error(request, "No authorization code received")
        return redirect(settings.LOGIN_URL)

    try:
        # Exchange code for tokens
        client = LoginGovClient()
        token_response = client.get_token(code)

        # Validate ID token
        id_token = token_response.get("id_token")
        if not id_token:
            messages.error(request, "No ID token in response")
            return redirect(settings.LOGIN_URL)

        stored_nonce = request.session.get("login_gov_nonce")
        user_data = client.validate_id_token(id_token, stored_nonce)

        # Authenticate user
        user = authenticate(request, login_gov_data=user_data)
        if user:
            login(request, user)

            # Clean up session
            request.session.pop("login_gov_state", None)
            request.session.pop("login_gov_nonce", None)

            # Redirect to next URL if available, otherwise to default
            next_url = request.session.get("next", settings.LOGIN_REDIRECT_URL)
            return redirect(next_url)
        else:
            messages.error(request, "Authentication failed")

    except Exception as e:
        if "Private key not configured" in str(e):
            messages.error(
                request,
                "Login.gov integration is not fully configured. Please contact your administrator.",
            )
        else:
            messages.error(request, f"Login failed: {str(e)}")

    return redirect(settings.LOGIN_URL)


def logout_view(request):
    """Handle user logout."""
    logout(request)
    return redirect(settings.LOGOUT_REDIRECT_URL)


def traditional_login_view(request):
    """Handle traditional login with username/password."""
    form = LoginForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            email = form.cleaned_data["email"].strip().lower()
            password = form.cleaned_data["password"]
            user = authenticate(request, username=email, password=password)

            if user is not None:
                login(request, user)
                next_url = request.GET.get("next", settings.LOGIN_REDIRECT_URL)
                return redirect(next_url)
            else:
                messages.error(request, "Invalid email or password.")

    return render(request, "users/login.html", {"form": form})
