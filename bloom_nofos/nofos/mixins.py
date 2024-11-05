from django.core.exceptions import PermissionDenied
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
