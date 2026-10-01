from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class LoginGovBackend(ModelBackend):
    """
    Email and password authentication backend.
    """

    def authenticate(self, request, **kwargs):
        return self._authenticate_password(request, **kwargs)

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
