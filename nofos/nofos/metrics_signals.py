"""Capture metric facts at write time, never by refreshing a report.

Bulk inserts bypass Django signals. Imports of historical/bulk data must explicitly
populate the metric facts, as the baseline migration does.
"""

import json
from uuid import UUID

from django.db.models import Q
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from easyaudit.models import CRUDEvent
from users.models import BloomUser

from .models import ImportAttempt, MetricsActivity, MetricsActor, MetricsNofo, Nofo

EXCLUDED_GROUPS = {"bloom", "staging"}


def actor_for(user, using):
    actor, _ = MetricsActor.objects.using(using).get_or_create(
        user_id=user.pk,
        defaults={
            "joined_at": user.date_joined,
            "included": user.group not in EXCLUDED_GROUPS,
            "group": user.group,
        },
    )
    return actor


@receiver(post_save, sender=BloomUser)
def record_signup(sender, instance, created, raw, using, **kwargs):
    if created and not raw:
        actor_for(instance, using)


@receiver(post_save, sender=Nofo)
def record_nofo(sender, instance, created, raw, using, **kwargs):
    if created and not raw:
        MetricsNofo.objects.using(using).get_or_create(
            id=instance.pk,
            defaults={
                "created_at": instance.created,
                "included": instance.group not in EXCLUDED_GROUPS,
                "group": instance.group,
            },
        )


@receiver(pre_save, sender=ImportAttempt)
def classify_import(sender, instance, raw, using, **kwargs):
    if instance._state.adding and not raw:
        group = (
            BloomUser.objects.using(using)
            .filter(pk=instance.user_id)
            .values_list("group", flat=True)
            .first()
        )
        instance.metrics_group = group or ""
        instance.metrics_included = (
            None if group is None else group not in EXCLUDED_GROUPS
        )


@receiver(post_save, sender=CRUDEvent)
def record_activity(sender, instance, created, raw, using, **kwargs):
    if not created or raw:
        return
    content_type = instance.content_type
    if content_type.app_label != "nofos" or content_type.model not in {
        "nofo",
        "section",
        "subsection",
    }:
        return
    if instance.user_id:
        user = BloomUser.objects.using(using).get(pk=instance.user_id)
        if user.group not in EXCLUDED_GROUPS:
            MetricsActivity.objects.using(using).get_or_create(
                actor=actor_for(user, using),
                group=user.group,
                month=timezone.localtime(instance.datetime).date().replace(day=1),
            )
    if content_type.model != "nofo" or instance.event_type != CRUDEvent.UPDATE:
        return
    try:
        fields = json.loads(instance.changed_fields)
        nofo_id = UUID(str(instance.object_id))
    except (TypeError, ValueError):
        return
    if (
        not isinstance(fields, dict)
        or fields.get("action") != "nofo_print"
        or fields.get("print_mode") != ["live"]
    ):
        return
    # Conditional update makes concurrent/out-of-order prints keep the earliest time.
    MetricsNofo.objects.using(using).filter(
        id=nofo_id, created_at__lte=instance.datetime
    ).filter(
        Q(first_live_at__isnull=True) | Q(first_live_at__gt=instance.datetime)
    ).update(
        first_live_at=instance.datetime
    )
