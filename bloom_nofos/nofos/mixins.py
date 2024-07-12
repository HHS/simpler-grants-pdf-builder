from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from .models import Nofo


def has_nofo_group_permission_func(user, nofo):
    # If not a 'bloom' user and the group doesn't match, fail
    if user.group != "bloom" and user.group != nofo.group:
        return False

    return True


# Note that this Mixin requires a self.get_object method
class GroupAccessObjectMixin:
    def dispatch(self, request, *args, **kwargs):
        # Temporarily retrieve the object to check permissions before it gets deleted
        obj = self.get_object()

        if not has_nofo_group_permission_func(request.user, obj):
            raise PermissionDenied("You don’t have permission to view this NOFO.")

        # Continue with normal processing, which will include deletion
        return super().dispatch(request, *args, **kwargs)


def check_nofo_group_permission(func):
    def wrapper(request, pk, subsection_pk, *args, **kwargs):
        nofo = get_object_or_404(Nofo, pk=pk)

        if not has_nofo_group_permission_func(request.user, nofo):
            raise PermissionDenied("You don’t have permission to view this NOFO.")

        return func(request, pk, subsection_pk, *args, **kwargs)

    return wrapper
