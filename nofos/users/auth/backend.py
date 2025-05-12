from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()


class LoginGovBackend(ModelBackend):
    """
    Authentication backend that supports both Login.gov and password authentication.
    """

    def _get_group_from_email(self, email):
        """Determine group based on email domain."""
        domain = email.lower().split("@")[1]

        domain_to_group = {
            "bloomworks.digital": "bloom",
            "hrsa.gov": "hrsa",
            "acf.hhs.gov": "acf",
        }

        return domain_to_group.get(domain, "bloom")

    def authenticate(self, request, **kwargs):
        login_gov_data = kwargs.get("login_gov_data")
        if login_gov_data:
            return self._authenticate_login_gov(login_gov_data)
        return self._authenticate_password(request, **kwargs)

    def _authenticate_login_gov(self, login_gov_data):
        """Handle Login.gov authentication"""
        email = login_gov_data.get("email")
        sub = login_gov_data.get("sub")

        if not email or not sub:
            return None

        try:
            user = User.objects.get(email=email)
            if not user.login_gov_user_id:
                user.login_gov_user_id = sub
                user.save()
        except User.DoesNotExist:
            group = self._get_group_from_email(email)
            user = User.objects.create(
                email=email,
                login_gov_user_id=sub,
                group=group,
                is_active=True,
                force_password_reset=False,
            )

        return user

    def _authenticate_password(self, request, username=None, password=None, **kwargs):
        """Handle traditional password authentication"""
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if username is None or password is None:
            return None

        user = User.objects.filter(email=username).first()

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None

    def get_user(self, user_id):
        return User.objects.filter(pk=user_id).first()
