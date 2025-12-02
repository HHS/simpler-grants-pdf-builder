from composer.models import ContentGuide, ContentGuideSection, ContentGuideSubsection
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404

from .models import Nofo


def has_group_permission_func(user, document):
    if not user.is_authenticated:
        return False

    # Check if the NOFO is archived
    if document.archived is not None:
        # If archived, only 'bloom' users can access
        return user.group == "bloom"

    # If not a 'bloom' user and the group doesn't match, fail
    if user.group != "bloom" and user.group != document.group:
        return False

    return True


def GroupAccessObjectMixinFactory(model_class):
    """
    Returns a mixin class that restricts access to objects of `model_class`
    based on the current user's group and the object's `archived` status.
    """

    class GroupAccessObjectMixin:
        def dispatch(self, request, *args, **kwargs):
            pk = self.kwargs.get("pk")
            obj = get_object_or_404(model_class, pk=pk)

            if not has_group_permission_func(request.user, obj):
                object_name = model_class._meta.verbose_name
                raise PermissionDenied(
                    f"You don’t have permission to view this {object_name}."
                )

            return super().dispatch(request, *args, **kwargs)

    return GroupAccessObjectMixin


class SuperuserRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied("You don’t have permission to view this page.")

        return super().dispatch(request, *args, **kwargs)


class BaseResponseMixin:
    def render_response(self, response):
        raise NotImplementedError("Subclasses must implement render_response")


class HttpResponseBadRequestMixin(BaseResponseMixin):
    def render_response(self, response):
        return HttpResponseBadRequest(response)


class JsonResponseBadRequestMixin(BaseResponseMixin):
    def render_response(self, response):
        return JsonResponse({"success": False, "message": response}, status=400)


class PreventIfPublishedBaseMixin(BaseResponseMixin):
    """Base mixin that prevents editing published objects. Subclasses override response format."""

    published_error_message = "This object is published and can't be changed."

    def dispatch(self, request, *args, **kwargs):
        nofo = getattr(self, "nofo", None) or self.get_object()

        # Throw exception if the object is published and not modified
        if nofo.status == "published" and not nofo.modifications:
            return self.render_response(self.published_error_message)

        return super().dispatch(request, *args, **kwargs)


class PreventIfPublishedMixin(PreventIfPublishedBaseMixin, HttpResponseBadRequestMixin):
    """Prevents editing published objects, returns HttpResponseBadRequest."""

    pass


class PreventIfArchivedBaseMixin(BaseResponseMixin):
    """Prevents editing archived objects, returns HttpResponseBadRequest."""

    archived_error_message = "This NOFO is archived and can't be changed."

    def dispatch(self, request, *args, **kwargs):
        nofo = getattr(self, "nofo", None) or self.get_object()

        # Check if the object is archived
        if nofo.archived:
            return self.render_response(self.archived_error_message)

        return super().dispatch(request, *args, **kwargs)


class PreventIfCancelledBaseMixin(BaseResponseMixin):
    """Base mixin that prevents editing cancelled objects. Subclasses override response format."""

    cancelled_error_message = "This NOFO was cancelled and can't be changed."

    def dispatch(self, request, *args, **kwargs):
        nofo = getattr(self, "nofo", None) or self.get_object()

        # Check if the object is cancelled _and there is_ an error message
        if nofo.status == "cancelled" and self.cancelled_error_message:
            return self.render_response(self.cancelled_error_message)

        return super().dispatch(request, *args, **kwargs)


class PreventIfArchivedOrCancelledMixin(
    PreventIfArchivedBaseMixin,
    PreventIfCancelledBaseMixin,
    HttpResponseBadRequestMixin,
):
    """Prevents editing archived or cancelled objects, returns HttpResponseBadRequest."""

    pass


class PreventIfContentGuideArchivedMixin:
    """
    Prevents editing archived ContentGuide objects.

    This mixin works with views where:
    - The object is a ContentGuide
      directly
    - The object is a ContentGuideSection or ContentGuideSubsection (checks parent)

    Returns HttpResponseBadRequest with an error message if the ContentGuide is archived.

    Usage examples:
        # For a view where the object is a ContentGuide directly
        class ComposerEditTitleView(PreventContentGuideArchivedMixin, UpdateView):
            model = ContentGuide
            ...

        # For a view where the object is a ContentGuideSubsection
        class ComposerSubsectionEditView(PreventContentGuideArchivedMixin, UpdateView):
            model = ContentGuideSubsection
            ...

        # Can be combined with other mixins (put it early in the MRO)
        class MyView(PreventContentGuideArchivedMixin, LoginRequiredMixin, UpdateView):
            ...
    """

    archived_error_message = "This Content Guide is archived and can't be changed."

    def dispatch(self, request, *args, **kwargs):
        # Get the document object - either directly or via parent relationships
        document = self._get_content_guide_document()

        # Check if the document is archived
        if document and document.archived:
            return HttpResponseBadRequest(self.archived_error_message)

        return super().dispatch(request, *args, **kwargs)

    def _get_content_guide_document(self):
        """
        Get the ContentGuide or ContentGuideInstance from the view object.

        Handles multiple scenarios:
        1. View object is ContentGuide or ContentGuideInstance directly
        2. View object is ContentGuideSection (has get_document() method)
        3. View object is ContentGuideSubsection (has section.get_document() method)
        4. View has a 'document' attribute set during get_object() or dispatch()
        """
        # Check if the view has already set a document attribute
        if hasattr(self, "document"):
            return self.document

        # Try to get the object from the view
        obj = getattr(self, "object", None)
        if obj is None:
            # Object hasn't been set yet, try to get it
            try:
                obj = self.get_object()
            except Exception:
                # Can't get object yet, return None
                return None

        # Check object type and navigate to the document
        if isinstance(obj, ContentGuide):
            return obj
        elif isinstance(obj, ContentGuideSection):
            # Section has `get_document()` method
            return obj.get_document()
        elif isinstance(obj, ContentGuideSubsection):
            # Subsection has `section` attribute
            return obj.section.get_document()

        return None
