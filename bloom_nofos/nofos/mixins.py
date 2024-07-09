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
        # Call the base implementation first to get a self.object defined
        response = super().dispatch(request, *args, **kwargs)

        if not has_nofo_group_permission_func(request.user, self.get_object()):
            raise PermissionDenied("You don’t have permission to view this NOFO.")

        return response


def check_nofo_group_permission(func):
    def wrapper(request, pk, subsection_pk, *args, **kwargs):
        nofo = get_object_or_404(Nofo, pk=pk)

        if not has_nofo_group_permission_func(request.user, nofo):
            raise PermissionDenied("You don’t have permission to view this NOFO.")

        return func(request, pk, subsection_pk, *args, **kwargs)

    return wrapper
