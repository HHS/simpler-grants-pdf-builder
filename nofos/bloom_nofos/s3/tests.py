from io import BytesIO
from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError, SSOTokenLoadError, TokenRetrievalError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from .utils import (
    get_image_url_from_s3,
    remove_file_from_s3,
    strip_s3_hostname_suffix,
    upload_file_to_s3,
)


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
    def test_empty_bucket_url_raises_exception(self):
        """Test that empty bucket URL raises exception."""
        with self.assertRaisesMessage(Exception, "No AWS bucket configured"):
            get_image_url_from_s3("test-path")

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

    @override_settings(GENERAL_S3_BUCKET_URL="test-bucket.s3.amazonaws.com")
    @patch("bloom_nofos.s3.utils.boto3.client")
    def test_image_content_types_accepted(self, mock_boto_client):
        """Test that various image MIME types are accepted, including those with parameters."""
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client

        # Test different image MIME types including ones with parameters
        image_types = [
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/webp",
            "image/svg+xml",
            "image/bmp",
            "image/tiff",
            "image/jpeg; charset=utf-8",
            "image/png; boundary=something",
            "image/svg+xml; charset=utf-8",
        ]

        for content_type in image_types:
            with self.subTest(content_type=content_type):
                mock_s3_client.head_object.return_value = {"ContentType": content_type}
                mock_s3_client.generate_presigned_url.return_value = (
                    f"https://test-url.com"
                )

                result = get_image_url_from_s3("test-image")

                self.assertIsNotNone(result, f"Should generate URL for {content_type}")
                self.assertTrue(
                    result.startswith("https://"),
                    f"Should return valid URL for {content_type}",
                )

    @override_settings(GENERAL_S3_BUCKET_URL="test-bucket.s3.amazonaws.com")
    @patch("bloom_nofos.s3.utils.boto3.client")
    def test_non_image_content_types_rejected(self, mock_boto_client):
        """Test that non-image MIME types are rejected."""
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client

        # Test non-image MIME types
        non_image_types = [
            "text/plain",
            "application/pdf",
            "video/mp4",
            "audio/mpeg",
            "application/json",
            "text/html",
        ]

        for content_type in non_image_types:
            with self.subTest(content_type=content_type):
                mock_s3_client.head_object.return_value = {"ContentType": content_type}

                result = get_image_url_from_s3("test-file")

                self.assertIsNone(result, f"Should reject {content_type}")

    @override_settings(GENERAL_S3_BUCKET_URL="test-bucket.s3.amazonaws.com")
    @patch("bloom_nofos.s3.utils.boto3.client")
    def test_invalid_content_types_rejected(self, mock_boto_client):
        """Test that objects with missing, None, or empty ContentType are rejected."""
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client

        # Test various invalid ContentType scenarios
        invalid_scenarios = [
            ({}, "missing ContentType"),
            ({"ContentType": None}, "None ContentType"),
            ({"ContentType": ""}, "empty ContentType"),
        ]

        for metadata_response, description in invalid_scenarios:
            with self.subTest(scenario=description):
                mock_s3_client.head_object.return_value = metadata_response

                result = get_image_url_from_s3("test-file")

                self.assertIsNone(result, f"Should reject objects with {description}")

    @override_settings(GENERAL_S3_BUCKET_URL="test-bucket.s3.amazonaws.com")
    @patch("bloom_nofos.s3.utils.boto3.client")
    def test_head_object_client_error(self, mock_boto_client):
        """Test handling of ClientError from head_object call."""
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client

        # Simulate ClientError when calling head_object
        mock_s3_client.head_object.side_effect = ClientError(
            error_response={"Error": {"Code": "NoSuchKey", "Message": "Key not found"}},
            operation_name="HeadObject",
        )

        result = get_image_url_from_s3("nonexistent-file")

        self.assertIsNone(result, "Should return None when file doesn't exist")


class UploadFileToS3Test(TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.test_file_content = b"Test file content"
        self.mock_file = SimpleUploadedFile(
            "test_image.jpg", self.test_file_content, content_type="image/jpeg"
        )

    @override_settings(GENERAL_S3_BUCKET_URL="test-bucket.s3.amazonaws.com")
    @patch("bloom_nofos.s3.utils.boto3.client")
    def test_successful_upload(self, mock_boto_client):
        """Test successful file upload to S3."""
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client

        result = upload_file_to_s3(self.mock_file, "cover-images")

        self.assertEqual(result, "cover-images/test_image.jpg")
        mock_boto_client.assert_called_once()
        mock_s3_client.upload_fileobj.assert_called_once()

        # Verify upload parameters
        call_args = mock_s3_client.upload_fileobj.call_args
        self.assertEqual(call_args[0][0], self.mock_file)  # file object
        self.assertEqual(call_args[0][1], "test-bucket")  # bucket name
        self.assertEqual(call_args[0][2], "cover-images/test_image.jpg")  # s3 key

        # Check ExtraArgs
        extra_args = call_args[1]["ExtraArgs"]
        self.assertEqual(extra_args["ContentType"], "image/jpeg")
        self.assertIn("original_filename", extra_args["Metadata"])
        self.assertIn("uploaded_at", extra_args["Metadata"])
        self.assertEqual(extra_args["Metadata"]["original_filename"], "test_image.jpg")

    @override_settings(GENERAL_S3_BUCKET_URL="test-bucket.s3.amazonaws.com")
    @patch("bloom_nofos.s3.utils.boto3.client")
    def test_aws_authentication_errors(self, mock_boto_client):
        """Test handling of various AWS authentication errors."""
        error_scenarios = [
            (
                TokenRetrievalError(provider="test", error_msg="Token expired"),
                "AWS authentication failed. Please contact an administrator.",
            ),
            (
                SSOTokenLoadError(error_msg="No SSO token found"),
                "AWS authentication failed. Please contact an administrator.",
            ),
        ]

        for exception, expected_message in error_scenarios:
            with self.subTest(exception=exception.__class__.__name__):
                mock_boto_client.side_effect = exception

                with self.assertRaisesMessage(Exception, expected_message):
                    upload_file_to_s3(self.mock_file, "test-prefix")

    @override_settings(GENERAL_S3_BUCKET_URL="test-bucket.s3.amazonaws.com")
    @patch("bloom_nofos.s3.utils.boto3.client")
    def test_client_error_handling(self, mock_boto_client):
        """Test handling of AWS ClientError."""
        mock_boto_client.side_effect = ClientError(
            error_response={
                "Error": {"Code": "AccessDenied", "Message": "Access denied"}
            },
            operation_name="PutObject",
        )

        with self.assertRaisesMessage(
            Exception,
            "File upload failed: An error occurred (AccessDenied) when calling the PutObject operation: Access denied",
        ):
            upload_file_to_s3(self.mock_file, "test-prefix")

    @override_settings(GENERAL_S3_BUCKET_URL="test-bucket.s3.amazonaws.com")
    @patch("bloom_nofos.s3.utils.boto3.client")
    def test_upload_fileobj_exception(self, mock_boto_client):
        """Test handling of exception during upload_fileobj call."""
        mock_s3_client = MagicMock()
        mock_s3_client.upload_fileobj.side_effect = Exception("Upload failed")
        mock_boto_client.return_value = mock_s3_client

        with self.assertRaisesMessage(Exception, "File upload failed: Upload failed"):
            upload_file_to_s3(self.mock_file, "test-prefix")


class RemoveFileFromS3Test(TestCase):
    @override_settings(GENERAL_S3_BUCKET_URL="test-bucket.s3.amazonaws.com")
    @patch("bloom_nofos.s3.utils.boto3.client")
    def test_successful_removal(self, mock_boto_client):
        """Test successful file removal from S3."""
        mock_s3_client = MagicMock()
        mock_boto_client.return_value = mock_s3_client

        # Should not raise any exception
        remove_file_from_s3("test-key/image.jpg")

        mock_boto_client.assert_called_once()
        mock_s3_client.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key="test-key/image.jpg"
        )

    @override_settings(GENERAL_S3_BUCKET_URL="test-bucket.s3.amazonaws.com")
    @patch("bloom_nofos.s3.utils.boto3.client")
    def test_aws_authentication_errors(self, mock_boto_client):
        """Test handling of various AWS authentication errors."""
        error_scenarios = [
            (
                TokenRetrievalError(provider="test", error_msg="Token expired"),
                "AWS authentication failed. Please contact an administrator.",
            ),
            (
                SSOTokenLoadError(error_msg="No SSO token found"),
                "AWS authentication failed. Please contact an administrator.",
            ),
        ]

        for exception, expected_message in error_scenarios:
            with self.subTest(exception=exception.__class__.__name__):
                mock_boto_client.side_effect = exception

                with self.assertRaisesMessage(Exception, expected_message):
                    remove_file_from_s3("test-key")

    @override_settings(GENERAL_S3_BUCKET_URL="test-bucket.s3.amazonaws.com")
    @patch("bloom_nofos.s3.utils.boto3.client")
    def test_client_error_handling(self, mock_boto_client):
        """Test handling of AWS ClientError."""
        mock_s3_client = MagicMock()
        mock_s3_client.delete_object.side_effect = ClientError(
            error_response={"Error": {"Code": "NoSuchKey", "Message": "Key not found"}},
            operation_name="DeleteObject",
        )
        mock_boto_client.return_value = mock_s3_client

        with self.assertRaisesMessage(
            Exception,
            "File removal failed: An error occurred (NoSuchKey) when calling the DeleteObject operation: Key not found",
        ):
            remove_file_from_s3("nonexistent-key")

        mock_s3_client.delete_object.assert_called_once()

    @override_settings(GENERAL_S3_BUCKET_URL="test-bucket.s3.amazonaws.com")
    @patch("bloom_nofos.s3.utils.boto3.client")
    def test_delete_object_exception(self, mock_boto_client):
        """Test handling of exception during delete_object call."""
        mock_s3_client = MagicMock()
        mock_s3_client.delete_object.side_effect = Exception("Delete failed")
        mock_boto_client.return_value = mock_s3_client

        with self.assertRaisesMessage(Exception, "File removal failed: Delete failed"):
            remove_file_from_s3("test-key")
