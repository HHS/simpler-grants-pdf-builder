from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404

from .models import Nofo


def has_nofo_group_permission_func(user, nofo):
    # Check if the NOFO is archived
    if nofo.archived is not None:
        # If archived, only 'bloom' users can access
        return user.group == "bloom"

    # If not a 'bloom' user and the group doesn't match, fail
    if user.group != "bloom" and user.group != nofo.group:
        return False

    return True


# Note that this Mixin requires a self.get_object method
class GroupAccessObjectMixin:
    def dispatch(self, request, *args, **kwargs):
        # Get the NOFO by pk since "get_object" could also be a subsection
        pk = self.kwargs.get("pk")
        nofo = get_object_or_404(Nofo, pk=pk)

        if not has_nofo_group_permission_func(request.user, nofo):
            raise PermissionDenied("You don’t have permission to view this NOFO.")

        # Continue with normal processing, which will include deletion
        return super().dispatch(request, *args, **kwargs)


class SuperuserRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied("You don’t have permission to view this page.")

        return super().dispatch(request, *args, **kwargs)


class PreventIfPublishedMixin:
    published_error_message = "This object is published and can’t be changed."

    def dispatch(self, request, *args, **kwargs):
        nofo = getattr(self, "nofo", None) or self.get_object()

        # Throw exception if the object is published and not modified
        if nofo.status == "published" and not nofo.modifications:
            return HttpResponseBadRequest(self.published_error_message)

        return super().dispatch(request, *args, **kwargs)


class PreventIfArchivedOrCancelledMixin:
    archived_error_message = "This NOFO is archived and can’t be changed."
    cancelled_error_message = "This NOFO was cancelled and can’t be changed."

    def dispatch(self, request, *args, **kwargs):
        nofo = getattr(self, "nofo", None) or self.get_object()
        # Throw exception if the object is archived
        if nofo.archived:
            return HttpResponseBadRequest(self.archived_error_message)

        # Throw exception if the object is cancelled _and there is_ an error message
        if nofo.status == "cancelled" and self.cancelled_error_message:
            return HttpResponseBadRequest(self.cancelled_error_message)

        return super().dispatch(request, *args, **kwargs)
