from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class WelcomeView(LoginRequiredMixin, TemplateView):
    template_name = "composer/composer_index.html"
