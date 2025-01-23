from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend

User = get_user_model()


class LoginGovBackend(BaseBackend):
    """
    Authentication backend for Login.gov users.
    Creates or updates local user based on Login.gov data.
    """

    def authenticate(self, request, **kwargs):
        login_gov_data = kwargs.get("login_gov_data")
        if not login_gov_data:
            return None

        email = login_gov_data.get("email")
        sub = login_gov_data.get("sub")  # Login.gov unique identifier

        if not email or not sub:
            return None

        try:
            user = User.objects.get(email=email)
            # Update Login.gov ID if not set
            if not user.login_gov_user_id:
                user.login_gov_user_id = sub
                user.save()
        except User.DoesNotExist:
            # Create new user
            user = User.objects.create(
                email=email,
                login_gov_user_id=sub,
                username=email,  # Using email as username
            )

        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
