import re

import boto3
from botocore.client import Config
from botocore.exceptions import SSOTokenLoadError, TokenRetrievalError
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import TemplateView

from .utils import get_display_size


class ImageListView(UserPassesTestMixin, TemplateView):
    template_name = "uploads/images.html"

    def test_func(self):
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        context["images"] = []
        context["AWS_STORAGE_BUCKET_NAME"] = bucket_name

        # Missing bucket config
        if not bucket_name:
            messages.error(
                self.request,
                "No AWS bucket configured. Please set <code>AWS_STORAGE_BUCKET_NAME</code> in your environment.",
            )
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

        return context
