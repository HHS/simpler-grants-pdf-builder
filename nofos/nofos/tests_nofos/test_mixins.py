from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.views.generic import View
from users.models import BloomUser

from nofos.mixins import PublishToSggRequiredMixin


class _PublishToSggView(PublishToSggRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return HttpResponse("ok")


class PublishToSggRequiredMixinTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _dispatch_as(self, user):
        request = self.factory.get("/fake-publish-url/")
        request.user = user
        return _PublishToSggView.as_view()(request)

    def test_superuser_is_allowed(self):
        user = BloomUser.objects.create_user(
            email="super@user.com", password="foo", group="bloom", is_superuser=True
        )
        response = self._dispatch_as(user)
        self.assertEqual(response.status_code, 200)

    def test_opdiv_admin_is_allowed(self):
        user = BloomUser.objects.create_user(
            email="opdiv-admin@user.com",
            password="foo",
            group="hrsa",
            is_opdiv_admin=True,
        )
        response = self._dispatch_as(user)
        self.assertEqual(response.status_code, 200)

    def test_regular_user_is_denied(self):
        user = BloomUser.objects.create_user(
            email="normal@user.com", password="foo", group="hrsa"
        )
        with self.assertRaises(PermissionDenied):
            self._dispatch_as(user)
