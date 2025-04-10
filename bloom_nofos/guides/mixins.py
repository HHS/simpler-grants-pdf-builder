from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from nofos.mixins import has_group_permission_func

from .models import ContentGuide

# TODO: genericize this


# Note that this Mixin requires a self.get_object method
class GroupAccessObjectContentGuideMixin:
    def dispatch(self, request, *args, **kwargs):
        # Get the NOFO by pk since "get_object" could also be a subsection
        pk = self.kwargs.get("pk")
        document = get_object_or_404(ContentGuide, pk=pk)

        if not has_group_permission_func(request.user, document):
            raise PermissionDenied(
                "You don’t have permission to view this Content Guide."
            )

        # Continue with normal processing, which will include deletion
        return super().dispatch(request, *args, **kwargs)
