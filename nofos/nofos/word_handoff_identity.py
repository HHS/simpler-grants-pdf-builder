"""Local identity primitives for a future, authorized external Word handoff adapter.

This module does not authenticate a sender or accept files. An approved ingress
adapter must construct ``TrustedHandoffPrincipal`` from verified credentials and
policy, never from request-body fields.
"""

from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from .models import ExternalSourceHandoff, Nofo


@dataclass(frozen=True)
class TrustedHandoffPrincipal:
    source_system: str
    authorized_group: str


def _require_opaque(value, field_name, max_length):
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise ValidationError({field_name: "A non-empty opaque string is required."})
    return value


def _validate_principal(principal):
    if not isinstance(principal, TrustedHandoffPrincipal):
        raise PermissionDenied("A trusted handoff principal is required.")
    _require_opaque(principal.source_system, "source_system", 128)
    allowed_groups = {key for key, _ in settings.GROUP_CHOICES} - {"bloom", "staging"}
    if principal.authorized_group not in allowed_groups:
        raise PermissionDenied("The principal has no permitted OpDiv scope.")


@transaction.atomic
def record_handoff(*, principal, source_record_id, source_version):
    """Return (receipt, created), reusing the exact identity tuple on retries.

    Version labels are opaque. This does not decide ordering or whether a retry's
    document bytes match an earlier delivery.
    """
    _validate_principal(principal)
    source_record_id = _require_opaque(source_record_id, "source_record_id", 255)
    source_version = _require_opaque(source_version, "source_version", 255)
    receipt, created = ExternalSourceHandoff.objects.get_or_create(
        source_system=principal.source_system,
        source_record_id=source_record_id,
        source_version=source_version,
        defaults={"group": principal.authorized_group},
    )
    if receipt.group != principal.authorized_group:
        raise PermissionDenied("This handoff belongs to a different OpDiv scope.")
    return receipt, created


@transaction.atomic
def link_handoff_to_nofo(*, principal, handoff_id, nofo_id):
    """Make a first, scope-matched NOFO link; never reassign a linked receipt."""
    _validate_principal(principal)
    handoff = ExternalSourceHandoff.objects.select_for_update().get(pk=handoff_id)
    if (
        handoff.source_system != principal.source_system
        or handoff.group != principal.authorized_group
    ):
        raise PermissionDenied("This handoff is outside the principal's scope.")
    nofo = Nofo.objects.select_for_update().get(pk=nofo_id)
    if nofo.group != handoff.group:
        raise PermissionDenied("The NOFO is outside the handoff's OpDiv scope.")
    if handoff.linked_nofo_uuid is not None and handoff.linked_nofo_uuid != nofo.pk:
        raise ValidationError("A handoff's NOFO link cannot be reassigned.")
    if handoff.linked_nofo_uuid is not None and handoff.nofo_id is None:
        raise ValidationError("A deleted NOFO link cannot be restored or reassigned.")
    if handoff.nofo_id is None:
        handoff.nofo = nofo
        handoff.linked_nofo_uuid = nofo.pk
        handoff.save(update_fields=["nofo", "linked_nofo_uuid"])
    return handoff
