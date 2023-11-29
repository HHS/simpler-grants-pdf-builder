from django.contrib import messages
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse
from django.views.generic import DetailView

from .models import BloomUser


class BloomUserDetailView(DetailView):
    model = BloomUser

    def get_object(self):
        """
        Returns the request's user.
        """
        return self.request.user

    template_name = "users/user_view.html"


class BloomPasswordChangeView(PasswordChangeView):
    template_name = "users/password_change.html"

    def get_success_url(self):
        return reverse("users:user_view")

    def form_valid(self, form):
        messages.success(self.request, "Your password has been changed.")
        return super().form_valid(form)
