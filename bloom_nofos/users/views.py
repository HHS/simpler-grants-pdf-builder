import csv
import json
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.timezone import make_aware
from django.views import View
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView
from easyaudit.models import CRUDEvent
from nofos.models import Nofo, Subsection

from .auth.login_gov import LoginGovClient
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


class ExportNofoReportView(View):
    """
    Handles exporting all NOFOs the logged-in user has edited.
    """

    def post(self, request, *args, **kwargs):
        form = ExportNofoReportForm(request.POST)

        if not form.is_valid():
            return render(
                request, "users/user_view.html", {"nofo_export_form": form}, status=400
            )

        user = request.user

        events_filters = {
            "event_type": 2,  # UPDATE events
            "content_type__model__in": ["nofo", "subsection"],
            "user": request.user,
        }

        # Define the date range (convert naive datetime to aware datetime)
        start_date = form.cleaned_data.get("start_date")
        end_date = form.cleaned_data.get("end_date")

        # Convert dates to timezone-aware datetimes (set to start/end of the day)
        if start_date:
            start_date = make_aware(datetime.combine(start_date, datetime.min.time()))
            events_filters["datetime__gte"] = start_date

        if end_date:
            end_date = make_aware(datetime.combine(end_date, datetime.max.time()))
            events_filters["datetime__lte"] = end_date

        # Query CRUDEvent for NOFO edits within date range
        events = CRUDEvent.objects.filter(**events_filters).values(
            "object_id", "datetime", "content_type__model", "changed_fields"
        )

        # Organize events into a dict mapping NOFO IDs to edit counts
        nofo_edit_counts = {}

        for event in events:
            object_id = event["object_id"]
            model = event["content_type__model"]

            # Determine NOFO ID
            if model == "nofo":
                nofo_id = object_id

            elif model == "subsection":
                nofo_id = (
                    Subsection.objects.filter(id=object_id)
                    .values_list("section__nofo_id", flat=True)
                    .first()
                )
                if not nofo_id:
                    continue  # Skip if we can't resolve NOFO ID

            # Skip events where the only change was "updated" timestamp
            try:
                changed_fields = json.loads(event["changed_fields"])
                if (
                    changed_fields
                    and "updated" in changed_fields
                    and len(changed_fields) == 1
                ):
                    continue
            except json.JSONDecodeError:
                continue  # Skip events with invalid JSON

            # Count edits for each NOFO
            nofo_id = int(nofo_id)
            nofo_edit_counts[nofo_id] = nofo_edit_counts.get(nofo_id, 0) + 1

        # Fetch NOFO details for the edited NOFOs
        nofos = (
            Nofo.objects.filter(id__in=nofo_edit_counts.keys())
            .filter(Q(archived__isnull=True))
            .values("id", "number", "title", "status")
        )

        # Prepare CSV response
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="edited_nofos.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "NOFO ID",
                "NOFO Number",
                "NOFO Title",
                "Nofo Status",
                "User Email",
                "Edits",
            ]
        )

        for nofo in nofos:
            writer.writerow(
                [
                    nofo["id"],
                    nofo["number"],
                    nofo["title"],
                    nofo["status"],
                    user.email,
                    nofo_edit_counts[nofo["id"]],
                ]
            )

        return response  # Return the generated CSV file


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
