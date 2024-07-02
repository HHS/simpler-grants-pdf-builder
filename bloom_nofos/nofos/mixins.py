from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from .models import Nofo


class GroupAccessMixin:
    def dispatch(self, request, *args, **kwargs):
        # Call the base implementation first to get a self.object defined
        response = super().dispatch(request, *args, **kwargs)

        # If not a 'bloom' user and the group doesn't match, fail
        if request.user.group != "bloom" and request.user.group != self.object.group:
            raise PermissionDenied("You don’t have permission to view this NOFO.")

        return response


def check_nofo_group_permission(func):
    def wrapper(request, pk, subsection_pk, *args, **kwargs):
        nofo = get_object_or_404(Nofo, pk=pk)

        if request.user.group != "bloom" and request.user.group != nofo.group:
            raise PermissionDenied("You don’t have permission to view this NOFO.")

        return func(request, pk, subsection_pk, *args, **kwargs)

    return wrapper
