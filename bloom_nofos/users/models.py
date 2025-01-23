from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
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
        default=True,
        help_text="Require this user to reset their password the next time they log in",
    )
    group = models.CharField(
        max_length=16,
        choices=settings.GROUP_CHOICES,
        default="bloom",
        help_text="The OpDiv for this user. If they are a Bloom coaches/admins, this should say 'Bloomworks'.",
    )
    login_gov_user_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text="Unique identifier from Login.gov",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = BloomUserManager()

    def __str__(self):
        if not self.full_name:
            return self.email

        return "{} ({})".format(self.email, self.full_name)

    def save(self, *args, **kwargs):
        # Ensure the email is stored in lowercase
        if self.email:
            self.email = self.email.lower()

        if (self.is_superuser or self.is_staff) and self.group != "bloom":
            raise ValidationError(
                "Only users in the 'bloom' group can be staff or superusers."
            )
        super().save(*args, **kwargs)
