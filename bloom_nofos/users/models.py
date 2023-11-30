from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from .managers import BloomUserManager


class BloomUser(AbstractUser):
    username = None
    first_name = None
    last_name = None
    full_name = models.CharField(blank=True, max_length=150, verbose_name="full name")
    email = models.EmailField(_("email address"), unique=True)
    force_password_reset = models.BooleanField(
        default=False,
        help_text="Require this user to reset their password the next time they log in",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = BloomUserManager()

    def __str__(self):
        return self.email
