import logging

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
