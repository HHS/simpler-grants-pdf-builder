import re

import boto3
from botocore.client import Config
from botocore.exceptions import SSOTokenLoadError, TokenRetrievalError
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.cache import cache
from django.views.generic import TemplateView

from .utils import get_display_size


class ImageListView(UserPassesTestMixin, TemplateView):
    template_name = "uploads/images.html"

    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request, *args, **kwargs):
        if request.GET.get("cache") == "false":
            cache.delete("uploads_images")
            messages.success(request, "Image cache has been cleared.")

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bucket_name = settings.GENERAL_S3_BUCKET_URL
        context["images"] = []
        context["GENERAL_S3_BUCKET_URL"] = bucket_name

        # Missing bucket config
        if not bucket_name:
            messages.error(
                self.request,
                "No AWS bucket configured. Please set <code>GENERAL_S3_BUCKET_URL</code> in your environment.",
            )
            return context

        # Try to get cached images
        cached_images = cache.get("uploads_images")
        if cached_images:
            context["images"] = cached_images
            return context

        try:
            s3 = boto3.client("s3", config=Config(signature_version="s3v4"))
            response = s3.list_objects_v2(Bucket=bucket_name)
            images = []

            for obj in response.get("Contents", []):
                key = obj["Key"]
                if re.search(r"\.(jpe?g|png)$", key, re.IGNORECASE):

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
