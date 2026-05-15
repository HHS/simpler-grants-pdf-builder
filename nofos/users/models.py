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
        help_text="The OpDiv for this user. If they are a Bloom coach/admin, this should say 'Bloomworks'.",
    )
    is_opdiv_admin = models.BooleanField(
        default=False,
        help_text="Allow this user to manage other OpDiv users in their group.",
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

    @property
    def can_manage_users(self):
        return self.is_superuser or self.is_opdiv_admin

    def can_manage_user(self, other_user):
        if self.is_superuser:
            return True

        if not self.is_opdiv_admin:
            return False

        if self.pk == other_user.pk:
            return False

        if other_user.is_superuser:
            return False

        return self.group == other_user.group

    def save(self, *args, **kwargs):
        # Ensure the email is stored in lowercase
        if self.email:
            self.email = self.email.lower()

        # Normalize empty Login.gov ID to None
        if not self.login_gov_user_id:
            self.login_gov_user_id = None

        if self.is_superuser and self.group != "bloom":
            raise ValidationError("Only users in the 'bloom' group can be superusers.")

        # Keep Django admin access derived from Superuser status.
        self.is_staff = self.is_superuser

        # Superusers already have broader privileges, so keep this role separate.
        if self.is_superuser:
            self.is_opdiv_admin = False

        super().save(*args, **kwargs)
