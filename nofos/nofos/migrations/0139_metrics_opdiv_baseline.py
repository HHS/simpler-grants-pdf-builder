"""Attribute surviving history once; never guess the group of deleted records."""

from django.db import migrations


def baseline(apps, schema_editor):
    alias = schema_editor.connection.alias
    Actor = apps.get_model("nofos", "MetricsActor")
    Activity = apps.get_model("nofos", "MetricsActivity")
    NofoFact = apps.get_model("nofos", "MetricsNofo")
    User = apps.get_model("users", "BloomUser")
    Nofo = apps.get_model("nofos", "Nofo")
    Attempt = apps.get_model("nofos", "ImportAttempt")
    # Only use surviving eligible groups for included facts. A current internal
    # group cannot recover the former agency of a historically eligible record.
    eligible = ["acf", "acl", "aspr", "cdc", "cms", "hrsa", "ihs", "nih"]
    for user in User.objects.using(alias).filter(group__in=eligible).iterator():
        Actor.objects.using(alias).filter(
            user_id=user.pk, included=True, group=""
        ).update(group=user.group)
        for activity in (
            Activity.objects.using(alias)
            .filter(actor__user_id=user.pk, group="")
            .iterator()
        ):
            # A new activity may already have captured the same actor/group/month.
            if (
                Activity.objects.using(alias)
                .filter(
                    actor_id=activity.actor_id, month=activity.month, group=user.group
                )
                .exists()
            ):
                activity.delete(using=alias)
            else:
                activity.group = user.group
                activity.save(using=alias, update_fields=["group"])
        Attempt.objects.using(alias).filter(
            user_id=user.pk, metrics_included=True, metrics_group=""
        ).update(metrics_group=user.group)
    for nofo in Nofo.objects.using(alias).filter(group__in=eligible).iterator():
        NofoFact.objects.using(alias).filter(
            pk=nofo.pk, included=True, group=""
        ).update(group=nofo.group)


class Migration(migrations.Migration):
    dependencies = [("nofos", "0138_metrics_opdiv")]
    operations = [migrations.RunPython(baseline)]
