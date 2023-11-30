from django.contrib import messages
from django.contrib.auth.views import PasswordChangeView
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView

from .forms import BloomUserNameForm
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
    template_name = "users/user_edit_password.html"
    title = "Change your password"

    def get_success_url(self):
        return reverse("users:user_view")

    def form_valid(self, form):
        messages.success(self.request, "You changed your password.")
        return super().form_valid(form)


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
