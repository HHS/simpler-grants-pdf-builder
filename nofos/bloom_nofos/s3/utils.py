import logging
import os
import uuid
from datetime import datetime

import boto3
from botocore.client import Config
from botocore.exceptions import SSOTokenLoadError, TokenRetrievalError, ClientError
from django.conf import settings

logger = logging.getLogger("s3")


def strip_s3_hostname_suffix(value):
    return value.split(".", 1)[0] if value else value


def get_image_url_from_s3(path):
    """
    Generate a presigned URL for an image file stored in S3.

    This function validates that the object at the given path is an image by checking
    its ContentType metadata. Only objects with ContentType starting with "image/"
    are allowed, ensuring security by preventing access to non-image files.

    Supported image formats include:
    - JPEG (image/jpeg)
    - PNG (image/png)
    - And any other valid image/* MIME types, including those with parameters

    Args:
        path (str): The S3 object key/path to the image file

    Returns:
        str: A presigned URL for the image if valid, None otherwise

    Security:
        - Only image ContentTypes are accepted (must start with "image/")

    Errors:
        - Logs warnings for authentication errors (expired/missing tokens)
        - Logs warnings for S3 access errors
        - Returns None for any errors or invalid content types
    """
    bucket_name = strip_s3_hostname_suffix(settings.GENERAL_S3_BUCKET_URL)

    if not bucket_name:
        raise Exception(
            "No AWS bucket configured. Please set GENERAL_S3_BUCKET_URL in your environment."
        )

    try:
        s3 = boto3.client("s3", config=Config(signature_version="s3v4"))
        metadata = s3.head_object(Bucket=bucket_name, Key=path)
        content_type = metadata.get("ContentType") if metadata else None
        if content_type and content_type.startswith("image/"):
            return s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket_name, "Key": path},
                ExpiresIn=3600,
            )
        return None

    except TokenRetrievalError:
        logger.warning(
            "Your AWS SSO token has expired.",
        )

    except SSOTokenLoadError:
        logger.warning(
            "No AWS SSO token found.",
        )

    except ClientError as e:
        logger.warning(
            f"An error occurred while accessing the AWS bucket: {e}",
        )

    except Exception as e:
        logger.warning(
            f"An error occurred while accessing the AWS bucket: {e}",
        )

    return None


def upload_file_to_s3(file, key_prefix):
    """
    Upload a file to S3 and return the key (path) if successful.

    Args:
        file: Django UploadedFile object
        key_prefix: S3 key prefix (folder) for the uploaded file

    Returns:
        str: S3 key/path of the uploaded file, or None if upload failed

    Raises:
        Exception: Various S3-related exceptions for proper error handling in views
    """
    bucket_name = strip_s3_hostname_suffix(settings.GENERAL_S3_BUCKET_URL)

    if not bucket_name:
        raise Exception(
            "No AWS bucket configured. Please set GENERAL_S3_BUCKET_URL in your environment."
        )

    try:
        # Generate unique filename to prevent conflicts
        s3_key = f"{key_prefix}/{format_filename_for_s3(file.name)}"

        logger.error(f"Uploading file to S3: {s3_key}")
        # Initialize S3 client
        s3 = boto3.client("s3", config=Config(signature_version="s3v4"))

        # Upload file to S3
        s3.upload_fileobj(
            file,
            bucket_name,
            s3_key,
            ExtraArgs={
                "ContentType": file.content_type,
                "Metadata": {
                    "original_filename": file.name,
                    "uploaded_at": datetime.now().isoformat(),
                },
            },
        )
        return s3_key

    except TokenRetrievalError:
        logger.error("AWS SSO token has expired.")
        raise Exception("AWS authentication failed. Please contact an administrator.")

    except SSOTokenLoadError:
        logger.error("No AWS SSO token found.")
        raise Exception("AWS authentication failed. Please contact an administrator.")

    except ClientError as e:
        logger.warning(
            f"An error occurred while accessing the AWS bucket: {e}",
        )
        raise Exception(f"File upload failed: {e}")

    except Exception as e:
        logger.error(f"Unexpected error uploading to S3: {e}")
        raise Exception(f"File upload failed: {e}")


def format_filename_for_s3(filename):
    """
    Format a filename for safe use as an S3 object key following the [AWS S3 naming conventions](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-keys.html#object-key-guidelines)

    Replaces unsafe characters with hyphens, keeping only alphanumeric characters
    and AWS S3 safe special characters: ! - _ . * ' ( )

    Args:
        filename (str): Original filename to format

    Returns:
        str: S3-safe filename with unsafe characters replaced by hyphens

    Examples:
        format_filename_for_s3("my file@#$%.txt") -> "my-file----.txt"
        format_filename_for_s3("document_with spaces.pdf") -> "document_with-spaces.pdf"
    """
    import re

    if not filename:
        return filename

    # Define safe characters: alphanumeric + ! - _ . * ' ( )
    # Replace any character that is NOT in this safe set with a hyphen
    safe_pattern = r"[^a-zA-Z0-9!\-_.*'()]"
    formatted = re.sub(safe_pattern, "-", filename)

    # Collapse multiple consecutive hyphens into single hyphens
    formatted = re.sub(r"-+", "-", formatted)

    # Remove leading/trailing hyphens but preserve other safe characters
    formatted = formatted.strip("-")

    return formatted


def remove_file_from_s3(key):
    """
    Remove a file from S3.
    """
    bucket_name = strip_s3_hostname_suffix(settings.GENERAL_S3_BUCKET_URL)

    if not bucket_name:
        raise Exception(
            "No AWS bucket configured. Please set GENERAL_S3_BUCKET_URL in your environment."
        )

    try:
        s3 = boto3.client("s3", config=Config(signature_version="s3v4"))
        s3.delete_object(Bucket=bucket_name, Key=key)

    except TokenRetrievalError:
        logger.error("AWS SSO token has expired.")
        raise Exception("AWS authentication failed. Please contact an administrator.")

    except SSOTokenLoadError:
        logger.error("No AWS SSO token found.")
        raise Exception("AWS authentication failed. Please contact an administrator.")

    except ClientError as e:
        logger.warning(
            f"An error occurred while accessing the AWS bucket: {e}",
        )
        raise Exception(f"File removal failed: {e}")

    except Exception as e:
        logger.error(f"Unexpected error removing file from S3: {e}")
        raise Exception(f"File removal failed: {e}")
