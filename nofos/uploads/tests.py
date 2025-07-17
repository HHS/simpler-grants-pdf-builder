from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from botocore.exceptions import TokenRetrievalError
from datetime import datetime, timezone
from .utils import get_display_size

User = get_user_model()


class GetDisplaySizeTests(SimpleTestCase):

    def test_bytes(self):
        self.assertEqual(get_display_size(0), "0 B")
        self.assertEqual(get_display_size(512), "512 B")
        self.assertEqual(get_display_size(1023), "1023 B")

    def test_kilobytes(self):
        self.assertEqual(get_display_size(1024), "1.0 KB")
        self.assertEqual(get_display_size(1536), "1.5 KB")
        self.assertEqual(get_display_size(10 * 1024), "10.0 KB")

    def test_megabytes(self):
        self.assertEqual(get_display_size(1024 * 1024), "1.0 MB")
        self.assertEqual(get_display_size(5 * 1024 * 1024), "5.0 MB")
        self.assertEqual(get_display_size(3145728), "3.0 MB")  # 3 MB


class ImageListViewTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            email="grant+super@grants.gov", password="pass"
        )
        self.regular_user = User.objects.create_user(
            email="grant@grants.gov", password="pass", group="acf"
        )
        self.url = reverse("uploads_images")

    @override_settings(AWS_STORAGE_BUCKET_NAME="fake-bucket")
    @patch("uploads.views.boto3.client")
    def test_superuser_sees_images(self, mock_boto_client):
        # Mock S3 client and response
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        mock_s3.list_objects_v2.return_value = {
            "Contents": [
                {
                    "Key": "images/photo1.jpg",
                    "Size": 1048576,
                    "LastModified": datetime(2024, 1, 1, tzinfo=timezone.utc),
                    "ETag": '"abc123"',
                }
            ]
        }
        mock_s3.generate_presigned_url.return_value = "https://fake-url/photo1.jpg"

        self.client.force_login(self.superuser)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "images/photo1.jpg")
        self.assertContains(response, "1.0 MB")
        self.assertContains(response, "https://fake-url/photo1.jpg")

    @override_settings(AWS_STORAGE_BUCKET_NAME=None)
    def test_missing_bucket_shows_error(self):
        self.client.force_login(self.superuser)
        response = self.client.get(self.url)
        self.assertContains(response, "No AWS bucket configured", status_code=200)

    @override_settings(AWS_STORAGE_BUCKET_NAME="fake-bucket")
    @patch("uploads.views.boto3.client")
    def test_token_missing_shows_message(self, mock_boto_client):
        from botocore.exceptions import SSOTokenLoadError

        mock_boto_client.side_effect = SSOTokenLoadError(
            profile_name="grants", error_msg="Token for grants does not exist"
        )

        self.client.force_login(self.superuser)
        response = self.client.get(self.url)

        self.assertContains(response, "No AWS SSO token found")

    @override_settings(AWS_STORAGE_BUCKET_NAME="fake-bucket")
    @patch("uploads.views.boto3.client")
    def test_token_retrieval_error_shows_message(self, mock_boto_client):
        mock_boto_client.side_effect = TokenRetrievalError(
            provider="sso", error_msg="Token has expired and refresh failed"
        )

        self.client.force_login(self.superuser)
        response = self.client.get(self.url)
        self.assertContains(response, "Your AWS SSO token has expired")

    def test_non_superuser_is_denied(self):
        self.client.force_login(self.regular_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
