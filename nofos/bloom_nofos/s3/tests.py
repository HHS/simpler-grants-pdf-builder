from unittest.mock import MagicMock, patch

from botocore.exceptions import SSOTokenLoadError, TokenRetrievalError
from django.test import TestCase, override_settings

from .utils import get_image_url_from_s3, strip_s3_hostname_suffix


class StripS3HostnameSuffixTests(TestCase):
    def test_full_hostname_strips_suffix(self):
        value = "nofos-dev-general-purpose20250513180715444700000002.s3.us-east-1.amazonaws.com"
        result = strip_s3_hostname_suffix(value)
        self.assertEqual(result, "nofos-dev-general-purpose20250513180715444700000002")

    def test_value_with_no_dot_returns_original(self):
        value = "nofos-bucket-name"
        result = strip_s3_hostname_suffix(value)
        self.assertEqual(result, value)

    def test_none_value_returns_none(self):
        result = strip_s3_hostname_suffix(None)
        self.assertIsNone(result)

    def test_empty_string_returns_empty(self):
        result = strip_s3_hostname_suffix("")
        self.assertEqual(result, "")


class GetImageUrlFromS3Test(TestCase):
    @override_settings(GENERAL_S3_BUCKET_URL="test-bucket.s3.amazonaws.com")
    @patch("bloom_nofos.s3.utils.boto3.client")
    def test_successful_url_generation(self, mock_boto_client):
        """Test successful presigned URL generation."""
        # Setup mock
        mock_s3_client = MagicMock()
        mock_s3_client.generate_presigned_url.return_value = (
            "https://test-bucket.s3.amazonaws.com/test-path?signature=xyz"
        )
        mock_boto_client.return_value = mock_s3_client

        # Test function
        result = get_image_url_from_s3("test-path/image.jpg")

        # Assertions
        self.assertEqual(
            result, "https://test-bucket.s3.amazonaws.com/test-path?signature=xyz"
        )
        mock_boto_client.assert_called_once()
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": "test-path/image.jpg"},
            ExpiresIn=3600,
        )

    @override_settings(GENERAL_S3_BUCKET_URL="test-bucket")
    @patch("bloom_nofos.s3.utils.boto3.client")
    def test_bucket_name_without_suffix(self, mock_boto_client):
        """Test with bucket name that has no hostname suffix."""
        mock_s3_client = MagicMock()
        mock_s3_client.generate_presigned_url.return_value = "https://test-url"
        mock_boto_client.return_value = mock_s3_client

        result = get_image_url_from_s3("image.jpg")

        self.assertEqual(result, "https://test-url")
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": "image.jpg"},
            ExpiresIn=3600,
        )

    @override_settings(GENERAL_S3_BUCKET_URL="test-bucket.s3.amazonaws.com")
    @patch("bloom_nofos.s3.utils.boto3.client")
    def test_token_retrieval_error(self, mock_boto_client):
        """Test handling of TokenRetrievalError."""
        mock_boto_client.side_effect = TokenRetrievalError(
            provider="test", error_msg="Token expired"
        )

        result = get_image_url_from_s3("test-path")

        self.assertIsNone(result)

    @override_settings(GENERAL_S3_BUCKET_URL="test-bucket.s3.amazonaws.com")
    @patch("bloom_nofos.s3.utils.boto3.client")
    def test_sso_token_load_error(self, mock_boto_client):
        """Test handling of SSOTokenLoadError."""
        mock_boto_client.side_effect = SSOTokenLoadError(error_msg="No SSO token found")

        result = get_image_url_from_s3("test-path")

        self.assertIsNone(result)

    @override_settings(GENERAL_S3_BUCKET_URL="test-bucket.s3.amazonaws.com")
    @patch("bloom_nofos.s3.utils.boto3.client")
    def test_general_exception(self, mock_boto_client):
        """Test handling of general exceptions."""
        mock_boto_client.side_effect = Exception("Network error")

        result = get_image_url_from_s3("test-path")

        self.assertIsNone(result)

    @override_settings(GENERAL_S3_BUCKET_URL="test-bucket.s3.amazonaws.com")
    @patch("bloom_nofos.s3.utils.boto3.client")
    def test_s3_client_generate_url_exception(self, mock_boto_client):
        """Test exception during presigned URL generation."""
        mock_s3_client = MagicMock()
        mock_s3_client.generate_presigned_url.side_effect = Exception("S3 API error")
        mock_boto_client.return_value = mock_s3_client

        result = get_image_url_from_s3("test-path")

        self.assertIsNone(result)

    @override_settings(GENERAL_S3_BUCKET_URL="")
    @patch("bloom_nofos.s3.utils.boto3.client")
    def test_empty_bucket_url(self, mock_boto_client):
        """Test with empty bucket URL setting."""
        mock_s3_client = MagicMock()
        mock_s3_client.generate_presigned_url.return_value = "https://test-url"
        mock_boto_client.return_value = mock_s3_client

        result = get_image_url_from_s3("test-path")

        # Should still work with empty bucket name
        self.assertEqual(result, "https://test-url")
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "", "Key": "test-path"},
            ExpiresIn=3600,
        )

    def test_empty_path(self):
        """Test with empty path parameter."""
        with override_settings(GENERAL_S3_BUCKET_URL="test-bucket"):
            with patch("bloom_nofos.s3.utils.boto3.client") as mock_boto_client:
                mock_s3_client = MagicMock()
                mock_s3_client.generate_presigned_url.return_value = "https://test-url"
                mock_boto_client.return_value = mock_s3_client

                result = get_image_url_from_s3("")

                self.assertEqual(result, "https://test-url")
                mock_s3_client.generate_presigned_url.assert_called_once_with(
                    "get_object",
                    Params={"Bucket": "test-bucket", "Key": ""},
                    ExpiresIn=3600,
                )
