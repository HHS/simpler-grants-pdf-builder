import csv

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import PasswordChangeView
from django.db.models import ProtectedError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render, resolve_url
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
)

from .auth.login_gov import LoginGovClient
from .exports import export_nofo_report, get_filename
from .forms import (
    BloomUserNameForm,
    BloomUserTeamCreateForm,
    BloomUserTeamGroupForm,
    BloomUserTeamNameForm,
    BloomUserTeamSuperuserForm,
    ExportNofoReportForm,
    LoginForm,
)
from .models import BloomUser


class BloomUserTeamAdminMixin(LoginRequiredMixin, UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        return self.request.user.is_superuser

    def redirect_invalid_operation(self, message, pk=None):
        self.request.session["error_heading"] = "Error: invalid operation"
        messages.error(self.request, message)

        if pk is None:
            pk = self.object.pk

        return redirect("users:user_team_detail", pk=pk)

    def another_superuser_exists(self, user):
        return BloomUser.objects.filter(is_superuser=True).exclude(pk=user.pk).exists()


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


class BloomUserNameView(LoginRequiredMixin, UpdateView):
    model = BloomUser
    form_class = BloomUserNameForm
    template_name = "users/user_edit_name.html"
    success_url = reverse_lazy("users:user_view")

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "You changed your name.")
        return super().form_valid(form)


###########################################################
######################## TEAM VIEWS #######################
###########################################################


class BloomUserTeamView(BloomUserTeamAdminMixin, ListView):
    model = BloomUser
    template_name = "users/user_team.html"
    context_object_name = "team_users"

    def get_queryset(self):
        return BloomUser.objects.all().order_by("email")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["error_heading"] = self.request.session.pop("error_heading", "Error")
        context["success_heading"] = self.request.session.pop("success_heading", "")
        return context


class BloomUserTeamDetailView(BloomUserTeamAdminMixin, DetailView):
    model = BloomUser
    template_name = "users/user_team_detail.html"
    context_object_name = "team_user"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["error_heading"] = self.request.session.pop("error_heading", "Error")
        context["success_heading"] = self.request.session.pop(
            "success_heading", "User updated"
        )
        return context


class BloomUserTeamCreateView(BloomUserTeamAdminMixin, CreateView):
    model = BloomUser
    form_class = BloomUserTeamCreateForm
    template_name = "users/user_team_create.html"
    success_url = reverse_lazy("users:user_team")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, "You added a new user: {}".format(self.object.email)
        )
        return response


class BloomUserTeamDeleteView(BloomUserTeamAdminMixin, DeleteView):
    model = BloomUser
    template_name = "users/user_team_confirm_delete.html"
    context_object_name = "team_user"
    success_url = reverse_lazy("users:user_team")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        if self.object.pk == request.user.pk:
            messages.error(request, "You can’t delete your own user account.")
            return redirect(self.success_url)

        if self.object.is_superuser and not self.another_superuser_exists(self.object):
            messages.error(request, "You can’t delete the last Superuser.")
            return redirect(self.success_url)

        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        user_to_delete = self.object
        email = user_to_delete.email

        if user_to_delete.pk == self.request.user.pk:
            messages.error(self.request, "You can’t delete your own user account.")
            return redirect(self.success_url)

        if user_to_delete.is_superuser and not self.another_superuser_exists(
            user_to_delete
        ):
            messages.error(self.request, "You can’t delete the last Superuser.")
            return redirect(self.success_url)

        try:
            user_to_delete.delete()
        except ProtectedError:
            messages.error(
                self.request,
                "This user could not be deleted because other records depend on them.",
            )
            return redirect(self.success_url)

        self.request.session["error_heading"] = "User deleted"
        messages.error(self.request, "You deleted user: {}.".format(email))
        return redirect(self.success_url)


class BaseBloomUserTeamEditView(BloomUserTeamAdminMixin, UpdateView):
    model = BloomUser
    template_name = "users/user_team_edit_form.html"
    context_object_name = "team_user"

    title = ""
    edit_object = ""
    intro2 = ""

    def get_success_url(self):
        return reverse_lazy("users:user_team_detail", args=[self.object.pk])

    def get_back_href(self):
        return reverse_lazy("users:user_team_detail", args=[self.object.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        context["back_text"] = self.object.email
        context["back_href"] = self.get_back_href()

        if self.edit_object:
            context["edit_object"] = self.edit_object

        if self.intro2:
            context["intro2"] = self.intro2

        return context

    def get_user_display_name(self):
        return self.object.full_name or self.object.email


class BloomUserTeamNameEditView(BaseBloomUserTeamEditView):
    form_class = BloomUserTeamNameForm
    title = "Change user name"
    edit_object = "name"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            "You changed this user’s name to “{}”.".format(self.object.full_name),
        )
        return response


class BloomUserTeamGroupEditView(BaseBloomUserTeamEditView):
    form_class = BloomUserTeamGroupForm
    title = "Change user group"
    edit_object = "group"
    intro2 = "A user’s group controls which NOFOs they have access to."

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            "You changed {}’s group to “{}”.".format(
                self.get_user_display_name(),
                self.object.group,
            ),
        )
        return response


class BloomUserTeamSuperuserEditView(BaseBloomUserTeamEditView):
    form_class = BloomUserTeamSuperuserForm
    template_name = "users/user_team_edit_superuser.html"
    title = "Change Superuser status"

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()

        if self.object.group != "bloom":
            return self.redirect_invalid_operation(
                "Only Bloom users can be assigned Superuser status."
            )

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        new_is_superuser = form.cleaned_data["is_superuser"]

        if self.object.pk == self.request.user.pk and not new_is_superuser:
            return self.redirect_invalid_operation(
                "You can’t remove Superuser status from your own account."
            )

        if (
            self.object.is_superuser
            and not new_is_superuser
            and not self.another_superuser_exists(self.object)
        ):
            return self.redirect_invalid_operation(
                "You can’t remove the last Superuser."
            )

        response = super().form_valid(form)

        user_name = self.get_user_display_name()
        superuser_message = (
            "You made {} a Superuser.".format(user_name)
            if self.object.is_superuser
            else "You removed Superuser privileges from {}.".format(user_name)
        )
        messages.success(self.request, superuser_message)
        return response


class BloomUserTeamPasswordResetView(BloomUserTeamAdminMixin, FormView):
    form_class = SetPasswordForm
    template_name = "users/user_team_edit_password.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return self.handle_no_permission()

        self.team_user = get_object_or_404(BloomUser, pk=kwargs["pk"])

        if self.team_user.pk == request.user.pk:
            request.session["error_heading"] = "Error: invalid operation"
            messages.error(
                request,
                "Use your account page to change your own password.",
            )
            return redirect("users:user_team_detail", pk=self.team_user.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.team_user
        return kwargs

    def get_success_url(self):
        return reverse_lazy("users:user_team_detail", args=[self.team_user.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["team_user"] = self.team_user
        context["title"] = "Reset user password"
        context["back_text"] = self.team_user.email
        context["back_href"] = reverse_lazy(
            "users:user_team_detail", args=[self.team_user.pk]
        )
        return context

    def form_valid(self, form):
        form.save()

        self.team_user.force_password_reset = True
        self.team_user.save(update_fields=["force_password_reset"])

        self.request.session["success_heading"] = "Password reset"
        messages.success(
            self.request,
            "You reset {}’s password. They will have to create a new one the next time they next log in.".format(
                self.team_user.full_name or self.team_user.email
            ),
        )
        return super().form_valid(form)


###########################################################
####################### DATA EXPORTS ######################
###########################################################


class ExportNofoReportView(FormView):
    template_name = "users/export_nofo_report.html"
    form_class = ExportNofoReportForm

    def get_form_kwargs(self):
        """Pass the current user to the form so that it can customize field choices."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        # Get the date range from the validated form
        start_date = form.cleaned_data.get("start_date")
        end_date = form.cleaned_data.get("end_date")

        # Get the group based on user_scope (either 'user' or 'group')
        group = (
            self.request.user.group
            if form.cleaned_data.get("user_scope") == "group"
            else None
        )

        csv_rows = export_nofo_report(
            start_date=start_date,
            end_date=end_date,
            user=self.request.user,
            group=group,
        )

        # Prepare CSV response
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="{}"'.format(
            get_filename(
                base_filename="nofo_export",
                group=group,
                start_date=start_date,
                end_date=end_date,
            )
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
    redirect_to = request.POST.get("next") or request.GET.get("next") or ""

    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"].strip().lower()
        password = form.cleaned_data["password"]
        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            if redirect_to and url_has_allowed_host_and_scheme(
                redirect_to, allowed_hosts={request.get_host()}
            ):
                return redirect(redirect_to)
            return redirect(resolve_url(settings.LOGIN_REDIRECT_URL))
        else:
            messages.error(request, "Invalid email or password.")

    return render(request, "users/login.html", {"form": form, "next": redirect_to})
