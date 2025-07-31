import re

import boto3
from bloom_nofos.s3.utils import strip_s3_hostname_suffix
from botocore.client import Config
from botocore.exceptions import SSOTokenLoadError, TokenRetrievalError
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.cache import cache
from django.views.generic import TemplateView

from nofos.models import Nofo
from .utils import get_display_size


class ImageListView(UserPassesTestMixin, TemplateView):
    template_name = "uploads/images.html"

    def test_func(self):
        return self.request.user.is_superuser

    def get_nofos_using_images(self, image_keys):
        """
        Returns a dictionary mapping image keys to lists of NOFOs that use them.

        Args:
            image_keys: List of S3 image keys to check

        Returns:
            dict: {image_key: [list of NOFO objects], ...}
        """
        if not image_keys:
            return {}

        # Query NOFOs that have cover_image matching any of our S3 keys
        nofos_using_images = (
            Nofo.objects.filter(
                cover_image__in=image_keys,
                archived__isnull=True,  # Exclude archived NOFOs
            )
            .select_related()
            .only(
                "id", "title", "short_name", "number", "opdiv", "status", "cover_image"
            )
        )

        # Create mapping of image key to list of NOFOs
        key_to_nofos = {}
        for nofo in nofos_using_images:
            key = nofo.cover_image
            if key not in key_to_nofos:
                key_to_nofos[key] = []
            key_to_nofos[key].append(nofo)

        return key_to_nofos

    def get(self, request, *args, **kwargs):
        if request.GET.get("cache") == "false":
            cache.delete("uploads_images_basic")
            messages.success(request, "Image cache has been cleared.")

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bucket_name = strip_s3_hostname_suffix(settings.GENERAL_S3_BUCKET_URL)
        context["images"] = []
        context["GENERAL_S3_BUCKET_URL"] = bucket_name

        # Missing bucket config
        if not bucket_name:
            messages.error(
                self.request,
                "No AWS bucket configured. Please set <code>GENERAL_S3_BUCKET_URL</code> in your environment.",
            )
            return context

        # Try to get cached basic image data (without NOFO usage info)
        cached_images = cache.get("uploads_images_basic")
        if cached_images:
            # We have cached S3 image data, now add fresh NOFO usage information
            image_keys = [img["key"] for img in cached_images]
            key_to_nofos = self.get_nofos_using_images(image_keys)

            # Add NOFO usage information to each cached image
            for image in cached_images:
                image["used_by_nofos"] = key_to_nofos.get(image["key"], [])

            context["images"] = cached_images
            return context

        try:
            s3 = boto3.client("s3", config=Config(signature_version="s3v4"))
            response = s3.list_objects_v2(Bucket=bucket_name)
            images = []
            image_keys = []

            # First pass: collect image data and keys
            for obj in response.get("Contents", []):
                key = obj["Key"]
                if re.search(r"\.(jpe?g|png)$", key, re.IGNORECASE):
                    image_keys.append(key)

                    url = s3.generate_presigned_url(
                        "get_object",
                        Params={"Bucket": bucket_name, "Key": key},
                        ExpiresIn=3600,
                    )

                    images.append(
                        {
                            "key": key,
                            "url": url,
                            "size_display": get_display_size(obj["Size"]),
                            "last_modified": obj["LastModified"],
                            "etag": obj["ETag"].strip('"'),
                        }
                    )

            # Sort by last modified, descending. More recent image is first.
            images.sort(key=lambda img: img["last_modified"], reverse=True)

            # Get NOFO usage information for all images
            key_to_nofos = self.get_nofos_using_images(image_keys)

            # Add NOFO usage information to each image
            for image in images:
                image["used_by_nofos"] = key_to_nofos.get(image["key"], [])

            context["images"] = images

            # Cache for 15 minutes
            cache.set("uploads_images", images, timeout=60 * 15)

        # Token error (eg, for an expired token)
        except TokenRetrievalError:
            messages.error(
                self.request,
                "Your AWS SSO token has expired. Please run <code>aws sso login</code> in your terminal to refresh it.",
            )

        except SSOTokenLoadError:
            messages.error(
                self.request,
                "No AWS SSO token found. Please run <code>aws sso login</code> in your terminal to authenticate.",
            )

        except Exception as e:
            messages.error(
                self.request,
                f"An error occurred while accessing the AWS bucket: {e}",
            )

        return context
