from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _


class BloomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifier
    for authentication instead of username.
    """

    def create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given email and password.
        """
        if not email:
            raise ValueError(_("Email is required"))
        email = self.normalize_email(email).lower()

        group = extra_fields.get("group", "")
        if not group:
            raise ValueError(_("Group is required"))

        if group != "bloom" and extra_fields.get("is_staff"):
            raise ValueError(_("Non-bloom users cannot be staff users."))

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("group", "bloom")
        extra_fields.setdefault(
            "force_password_reset", False
        )  # Default to False for superusers

        if extra_fields.get("group") != "bloom":
            raise ValueError(_("Superuser must have group=Bloomworks."))
        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self.create_user(email, password, **extra_fields)
