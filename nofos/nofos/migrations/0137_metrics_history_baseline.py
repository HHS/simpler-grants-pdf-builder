"""Freeze surviving history once; earlier deletions/group membership are unknowable."""

import json
from uuid import UUID

from django.db import migrations
from django.db.models import Q
from django.utils import timezone


def baseline(apps, schema_editor):
    alias = schema_editor.connection.alias
    Actor = apps.get_model("nofos", "MetricsActor")
    NofoFact = apps.get_model("nofos", "MetricsNofo")
    Activity = apps.get_model("nofos", "MetricsActivity")
    User = apps.get_model("users", "BloomUser")
    Nofo = apps.get_model("nofos", "Nofo")
    Attempt = apps.get_model("nofos", "ImportAttempt")
    Event = apps.get_model("easyaudit", "CRUDEvent")
    excluded = {"bloom", "staging"}

    actors = {}
    for user in User.objects.using(alias).all().iterator():
        actor, _ = Actor.objects.using(alias).get_or_create(
            user_id=user.pk,
            defaults={
                "joined_at": user.date_joined,
                "included": user.group not in excluded,
            },
        )
        actors[user.pk] = (actor.pk, user.group not in excluded)
    for nofo in Nofo.objects.using(alias).all().iterator():
        NofoFact.objects.using(alias).get_or_create(
            id=nofo.pk,
            defaults={
                "created_at": nofo.created,
                "included": nofo.group not in excluded,
            },
        )

    # Missing users have unknown eligibility. Do not silently count them as external.
    Attempt.objects.using(alias).filter(
        metrics_included__isnull=True, user__isnull=False
    ).exclude(user__group__in=excluded).update(metrics_included=True)
    Attempt.objects.using(alias).filter(
        metrics_included__isnull=True, user__group__in=excluded
    ).update(metrics_included=False)

    events = (
        Event.objects.using(alias)
        .filter(
            content_type__app_label="nofos",
            content_type__model__in=["nofo", "section", "subsection"],
        )
        .values(
            "user_id",
            "datetime",
            "content_type__model",
            "event_type",
            "object_id",
            "changed_fields",
        )
    )
    seen_activity = set()
    for event in events.iterator():
        actor = actors.get(event["user_id"])
        if actor and actor[1]:
            month = timezone.localtime(event["datetime"]).date().replace(day=1)
            key = (actor[0], month)
            if key not in seen_activity:
                Activity.objects.using(alias).get_or_create(
                    actor_id=actor[0], month=month
                )
                seen_activity.add(key)
        if event["content_type__model"] != "nofo" or event["event_type"] != 2:
            continue
        try:
            fields = json.loads(event["changed_fields"])
            nofo_id = UUID(str(event["object_id"]))
        except (TypeError, ValueError):
            continue
        if (
            not isinstance(fields, dict)
            or fields.get("action") != "nofo_print"
            or fields.get("print_mode") != ["live"]
        ):
            continue
        NofoFact.objects.using(alias).filter(
            id=nofo_id, created_at__lte=event["datetime"]
        ).filter(
            Q(first_live_at__isnull=True) | Q(first_live_at__gt=event["datetime"])
        ).update(
            first_live_at=event["datetime"]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("nofos", "0136_metrics_history"),
        ("users", "0011_alter_bloomuser_group"),
    ]
    # Intentionally irreversible: rerunning a baseline after rollback could reclassify history.
    operations = [migrations.RunPython(baseline)]
