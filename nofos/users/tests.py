from django.contrib.auth import get_user_model
from django.test import TestCase
from users.auth.backend import LoginGovBackend

User = get_user_model()


class LoginGovBackendTests(TestCase):
    """The backend keeps its historical name; it now only handles passwords."""

    def setUp(self):
        self.backend = LoginGovBackend()
        self.existing_user = User.objects.create_user(
            email="existing@bloomworks.digital",
            password="correct-password",
            group="bloom",
        )

    def test_authenticate_with_correct_password(self):
        user = self.backend.authenticate(
            None, username="existing@bloomworks.digital", password="correct-password"
        )
        self.assertEqual(user, self.existing_user)

    def test_authenticate_with_wrong_password(self):
        self.assertIsNone(
            self.backend.authenticate(
                None, username="existing@bloomworks.digital", password="wrong"
            )
        )

    def test_authenticate_inactive_user(self):
        self.existing_user.is_active = False
        self.existing_user.save()
        self.assertIsNone(
            self.backend.authenticate(
                None,
                username="existing@bloomworks.digital",
                password="correct-password",
            )
        )

    def test_login_gov_data_no_longer_authenticates(self):
        self.assertIsNone(
            self.backend.authenticate(
                None,
                login_gov_data={
                    "email": "existing@bloomworks.digital",
                    "sub": "test-sub-id",
                },
            )
        )

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


class BloomUserCanPublishToSggTests(TestCase):
    def test_superuser_can_publish_to_sgg(self):
        user = User.objects.create_user(
            email="super@user.com", password="foo", group="bloom", is_superuser=True
        )
        self.assertTrue(user.can_publish_to_sgg)

    def test_opdiv_admin_can_publish_to_sgg(self):
        user = User.objects.create_user(
            email="opdiv-admin@user.com",
            password="foo",
            group="hrsa",
            is_opdiv_admin=True,
        )
        self.assertTrue(user.can_publish_to_sgg)

    def test_regular_user_cannot_publish_to_sgg(self):
        user = User.objects.create_user(
            email="normal@user.com", password="foo", group="hrsa"
        )
        self.assertFalse(user.can_publish_to_sgg)
