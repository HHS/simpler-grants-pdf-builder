from unittest.mock import MagicMock, patch

from cryptography.hazmat.primitives.asymmetric import rsa
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from users.auth.backend import LoginGovBackend
from users.auth.login_gov import LoginGovClient

User = get_user_model()

test_login_gov_settings = {
    "LOGIN_GOV": {
        "CLIENT_ID": "test_client_id",
        "OIDC_URL": "https://test.login.gov",
        "REDIRECT_URI": "http://localhost:8000/users/login/callback",
        "ACR_VALUES": "http://idmanagement.gov/ns/assurance/ial/1",
    }
}

test_login_gov_settings_with_key = {
    "LOGIN_GOV": {
        "CLIENT_ID": "test_client_id",
        "OIDC_URL": "https://test.login.gov",
        "REDIRECT_URI": "http://localhost:8000/users/login/callback",
        "ACR_VALUES": "http://idmanagement.gov/ns/assurance/ial/1",
        "PRIVATE_KEY": "test_private_key",
        "PUBLIC_KEY": "test_public_key",
    }
}


@override_settings(**test_login_gov_settings)
class LoginGovClientTests(TestCase):
    def setUp(self):
        # Create a test RSA key for JWT operations
        self.private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048
        )

    def test_init_without_private_key(self):
        """Test that LoginGovClient raises an exception when private key is not found."""
        with self.assertRaises(Exception) as context:
            LoginGovClient()
        self.assertTrue(
            "Private key not configured in settings.LOGIN_GOV['PRIVATE_KEY']"
            in str(context.exception)
        )

    @override_settings(**test_login_gov_settings_with_key)
    @patch("users.auth.login_gov.load_pem_private_key")
    @patch("users.auth.login_gov.requests.get")
    def test_get_login_gov_public_key(self, mock_get, mock_load_key):
        """Test fetching Login.gov public key."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "keys": [{"kty": "RSA", "n": "test_n", "e": "AQAB", "kid": "test_kid"}]
        }
        mock_get.return_value = mock_response
        mock_load_key.return_value = self.private_key

        client = LoginGovClient()
        key = client._get_login_gov_public_key("test_kid")
        self.assertIsNotNone(key)

    @override_settings(**test_login_gov_settings_with_key)
    @patch("users.auth.login_gov.load_pem_private_key")
    def test_get_authorization_url(self, mock_load_key):
        """Test generating authorization URL."""
        mock_load_key.return_value = self.private_key

        client = LoginGovClient()
        url, state, nonce = client.get_authorization_url()

        self.assertTrue(
            url.startswith("https://test.login.gov/openid_connect/authorize")
        )
        self.assertIn("client_id=test_client_id", url)
        self.assertIn("response_type=code", url)
        self.assertIn("state=" + state, url)
        self.assertIn("nonce=" + nonce, url)

    @override_settings(**test_login_gov_settings_with_key)
    @patch("users.auth.login_gov.load_pem_private_key")
    @patch("users.auth.login_gov.requests.post")
    @patch("users.auth.login_gov.jwt.encode")
    def test_get_token(self, mock_jwt_encode, mock_post, mock_load_key):
        """Test exchanging code for tokens."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "id_token": "test_id_token",
        }
        mock_post.return_value = mock_response
        mock_load_key.return_value = self.private_key
        mock_jwt_encode.return_value = "test.jwt.token"

        client = LoginGovClient()
        tokens = client.get_token("test_code")

        self.assertEqual(tokens["access_token"], "test_access_token")
        self.assertEqual(tokens["id_token"], "test_id_token")

    @override_settings(**test_login_gov_settings_with_key)
    @patch("users.auth.login_gov.load_pem_private_key")
    @patch("users.auth.login_gov.jwt.get_unverified_header")
    @patch("users.auth.login_gov.jwt.decode")
    @patch("users.auth.login_gov.requests.get")
    def test_validate_id_token(self, mock_get, mock_decode, mock_header, mock_load_key):
        """Test validating ID token."""
        mock_header.return_value = {"kid": "test_kid"}
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "keys": [{"kty": "RSA", "n": "test_n", "e": "AQAB", "kid": "test_kid"}]
        }
        mock_get.return_value = mock_response
        mock_decode.return_value = {
            "sub": "test_sub",
            "email": "test@example.com",
            "nonce": "test_nonce",
        }
        mock_load_key.return_value = self.private_key

        client = LoginGovClient()
        decoded = client.validate_id_token("test.jwt.token", "test_nonce")

        self.assertEqual(decoded["sub"], "test_sub")
        self.assertEqual(decoded["email"], "test@example.com")


class LoginGovBackendTests(TestCase):
    def setUp(self):
        self.backend = LoginGovBackend()
        # Create a test user
        self.existing_user = User.objects.create(
            email="existing@bloomworks.digital",
            group="Bloomworks",
        )

    def test_group_assignment_bloomworks(self):
        """Test group assignment for Bloomworks domain"""
        group = self.backend._get_group_from_email("test@bloomworks.digital")
        self.assertEqual(group, "bloom")

    def test_group_assignment_hrsa(self):
        """Test group assignment for HRSA domain"""
        group = self.backend._get_group_from_email("test@hrsa.gov")
        self.assertEqual(group, "hrsa")

    def test_group_assignment_unknown_domain(self):
        """Test group assignment for unknown domain defaults to bloom"""
        group = self.backend._get_group_from_email("test@unknown.com")
        self.assertEqual(group, "bloom")

    def test_authenticate_login_gov_existing_user(self):
        """Test authenticating existing user with Login.gov"""
        login_gov_data = {
            "email": "existing@bloomworks.digital",
            "sub": "test-sub-id",
        }
        user = self.backend.authenticate(None, login_gov_data=login_gov_data)
        self.assertIsNotNone(user)
        self.assertEqual(user.email, "existing@bloomworks.digital")
        self.assertEqual(user.login_gov_user_id, "test-sub-id")

    def test_authenticate_login_gov_new_user(self):
        """Test authenticating new user with Login.gov"""
        login_gov_data = {
            "email": "new@hrsa.gov",
            "sub": "test-sub-id",
        }
        user = self.backend.authenticate(None, login_gov_data=login_gov_data)
        self.assertIsNotNone(user)
        self.assertEqual(user.email, "new@hrsa.gov")
        self.assertEqual(user.group, "hrsa")
        self.assertEqual(user.login_gov_user_id, "test-sub-id")
        self.assertTrue(user.is_active)
        self.assertFalse(user.force_password_reset)

    def test_authenticate_login_gov_invalid_data(self):
        """Test authentication fails with invalid Login.gov data"""
        # Missing email
        self.assertIsNone(
            self.backend.authenticate(None, login_gov_data={"sub": "test-sub-id"})
        )
        # Missing sub
        self.assertIsNone(
            self.backend.authenticate(
                None, login_gov_data={"email": "test@example.com"}
            )
        )
        # Empty data
        self.assertIsNone(self.backend.authenticate(None, login_gov_data={}))

    def test_get_user_exists(self):
        """Test getting existing user by ID"""
        user = self.backend.get_user(self.existing_user.id)
        self.assertEqual(user, self.existing_user)

    def test_get_user_does_not_exist(self):
        """Test getting non-existent user returns None"""
        self.assertIsNone(self.backend.get_user(999))


class UsersManagersTests(TestCase):
    def test_create_user(self):
        User = get_user_model()
        user = User.objects.create_user(
            email="normal@user.com", password="foo", group="acf"
        )
        self.assertEqual(user.email, "normal@user.com")
        self.assertEqual(user.group, "acf")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        try:
            # username is None for the AbstractUser option
            # username does not exist for the AbstractBaseUser option
            self.assertIsNone(user.username)
        except AttributeError:
            pass
        with self.assertRaises(TypeError):
            User.objects.create_user()
        with self.assertRaises(TypeError):
            User.objects.create_user(email="")
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="foo")
        with self.assertRaises(ValueError):
            # Non-bloom users can't be staff
            User.objects.create_user(
                email="normal@user.com", password="foo", group="cdc", is_staff=True
            )

    def test_create_superuser(self):
        User = get_user_model()
        admin_user = User.objects.create_superuser(
            email="super@user.com", password="foo"
        )
        self.assertEqual(admin_user.email, "super@user.com")
        self.assertTrue(admin_user.is_active)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        try:
            # username is None for the AbstractUser option
            # username does not exist for the AbstractBaseUser option
            self.assertIsNone(admin_user.username)
        except AttributeError:
            pass

    def test_create_superuser_fails_if_is_superuser_false(self):
        User = get_user_model()
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="super@user.com", password="foo", is_superuser=False
            )

    def test_create_superuser_fails_if_group_is_not_bloom(self):
        User = get_user_model()
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="super@user.com", password="foo", group="cdc"
            )
