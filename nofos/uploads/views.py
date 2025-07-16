from django.views.generic import TemplateView
from django.contrib.auth.mixins import UserPassesTestMixin
from django.conf import settings
from django.contrib import messages
from botocore.exceptions import TokenRetrievalError
import boto3
import re


class ImageListView(UserPassesTestMixin, TemplateView):
    template_name = "uploads/images.html"

    def test_func(self):
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        context["images"] = []
        context["AWS_STORAGE_BUCKET_NAME"] = bucket_name

        try:
            s3 = boto3.client("s3")
            response = s3.list_objects_v2(Bucket=bucket_name)

            images = []
            for obj in response.get("Contents", []):
                key = obj["Key"]
                if re.search(r"\.(jpe?g|png)$", key, re.IGNORECASE):
                    images.append(key)

            context["images"] = images

        except TokenRetrievalError as e:
            # Handle SSO token expiration gracefully
            messages.error(
                self.request,
                "Your AWS SSO token has expired. Please run <code>aws sso login</code> in your terminal to refresh it.",
            )

        return context
