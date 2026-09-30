"""Local identity primitives for a future, authorized external Word handoff adapter.

This module does not authenticate a sender or accept files. An approved ingress
adapter must construct ``TrustedHandoffPrincipal`` from verified credentials and
policy, never from request-body fields.
"""

from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, transaction

from .models import (
    ExternalSourceHandoff,
    ExternalSourceHandoffCurrent,
    ExternalSourceHandoffResult,
    Nofo,
)
from .word_handoff_lifecycle import ReviewDecision


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
    """Create the first immutable result, or retry that exact initial link."""
    handoff, nofo = _locked_scope(principal, handoff_id, nofo_id)
    selection = ExternalSourceHandoffCurrent.objects.filter(handoff=handoff).first()
    if selection is not None:
        if (
            selection.result.supersedes_id is None
            and selection.result.linked_nofo_uuid == nofo.pk
        ):
            if selection.result.nofo_id is None:
                raise ValidationError("A deleted NOFO link cannot be restored.")
            return selection.result
        raise ValidationError(
            "A linked handoff requires an explicit replacement decision."
        )
    result = ExternalSourceHandoffResult.objects.create(
        handoff=handoff, nofo=nofo, linked_nofo_uuid=nofo.pk
    )
    ExternalSourceHandoffCurrent.objects.create(handoff=handoff, result=result)
    return result


@transaction.atomic
def replace_handoff_result(
    *, principal, handoff_id, nofo_id, expected_current_result_id, review
):
    """Atomically append a replacement and advance the one current selector.

    ``review`` is evidence supplied by a future trusted adapter, not authentication
    or an authorization check implemented by this module.
    """
    handoff, nofo = _locked_scope(principal, handoff_id, nofo_id)
    if not isinstance(review, ReviewDecision):
        raise PermissionDenied("An explicit trusted replacement decision is required.")
    for value in (
        review.reviewer_id,
        review.authorization_reference,
        review.decision_id,
    ):
        _require_opaque(value, "review", 255)
    selection = ExternalSourceHandoffCurrent.objects.select_for_update().get(
        handoff=handoff
    )
    prior = selection.result
    if prior.pk != expected_current_result_id:
        raise ValidationError("Current result changed; replacement is stale.")
    if prior.linked_nofo_uuid == nofo.pk:
        raise ValidationError("A result's NOFO cannot be relinked or reused.")
    result = ExternalSourceHandoffResult.objects.create(
        handoff=handoff,
        nofo=nofo,
        linked_nofo_uuid=nofo.pk,
        supersedes=prior,
        reviewer_id=review.reviewer_id,
        authorization_reference=review.authorization_reference,
        decision_id=review.decision_id,
    )
    # The public manager blocks selector writes. This narrowly scoped ORM update
    # is the only intended mutation path, guarded by the receipt lock and CAS.
    changed = (
        models.QuerySet(model=ExternalSourceHandoffCurrent, using=selection._state.db)
        .filter(pk=handoff.pk, result_id=prior.pk)
        .update(result=result)
    )
    if changed != 1:
        raise ValidationError("Current result changed; replacement is stale.")
    return result


def _locked_scope(principal, handoff_id, nofo_id):
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
    return handoff, nofo
