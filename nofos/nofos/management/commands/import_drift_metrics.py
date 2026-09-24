import json
from collections import defaultdict
from datetime import datetime, time

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Sum
from django.utils import timezone
from easyaudit.models import CRUDEvent

from nofos.metrics import METRICS_SINCE, opdiv_choices
from nofos.metrics_signals import EXCLUDED_GROUPS
from nofos.models import ImportAttempt

NOFO_METADATA_FIELDS = {
    "agency",
    "application_deadline",
    "assistance_listing_number",
    "author",
    "keywords",
    "number",
    "opdiv",
    "short_name",
    "subagency",
    "subagency2",
    "subject",
    "tagline",
    "title",
}


def _date_boundary(value, option):
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise CommandError(f"{option} must use YYYY-MM-DD format") from exc
    return timezone.make_aware(datetime.combine(parsed, time.min))


class Command(BaseCommand):
    help = (
        "Print aggregate-only Word import drift signals from ImportAttempt and "
        "django-easy-audit data. No document text, field values, filenames, or "
        "user identifiers are emitted."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--since",
            default=METRICS_SINCE.strftime("%Y-%m-%d"),
            help="First date to include, as YYYY-MM-DD.",
        )
        parser.add_argument(
            "--until",
            help="Exclusive end date, as YYYY-MM-DD (default: now).",
        )
        parser.add_argument(
            "--group",
            default="all",
            help="OpDiv group to include (default: all external groups).",
        )

    def handle(self, *args, **options):
        start = _date_boundary(options["since"], "--since")
        end = (
            _date_boundary(options["until"], "--until")
            if options["until"]
            else timezone.now()
        )
        if end <= start:
            raise CommandError("--until must be later than --since")

        group = options["group"]
        valid_groups = {key for key, _ in opdiv_choices()}
        if group != "all" and group not in valid_groups:
            raise CommandError(f"Unknown OpDiv group: {group}")

        metrics = []
        metrics.extend(self._import_metrics(start, end, group))
        metrics.extend(self._audit_metrics(start, end, group))

        self.stdout.write("metric\tvalue\taffected_objects")
        for metric, value, affected_objects in metrics:
            self.stdout.write(f"{metric}\t{value}\t{affected_objects}")

    def _import_metrics(self, start, end, group):
        attempts = ImportAttempt.objects.filter(
            created_at__gte=start,
            created_at__lt=end,
            metrics_included=True,
        )
        if group != "all":
            attempts = attempts.filter(metrics_group=group)

        successful = attempts.filter(error_code="")
        rows = [
            ("imports.attempts", attempts.count(), "N/A"),
            (
                "imports.reimport_attempts",
                attempts.filter(is_reimport=True).count(),
                "N/A",
            ),
            ("imports.failed_attempts", attempts.exclude(error_code="").count(), "N/A"),
            (
                "imports.attempts_with_warnings",
                successful.filter(warning_count__gt=0).count(),
                "N/A",
            ),
            (
                "imports.warning_count",
                successful.aggregate(total=Sum("warning_count"))["total"] or 0,
                "N/A",
            ),
        ]
        for row in (
            attempts.exclude(error_code="")
            .values("error_code")
            .annotate(count=Count("id"))
            .order_by("error_code")
        ):
            code = row["error_code"]
            metric = f"imports.error.{code.lower()}"
            rows.append((metric, row["count"], "N/A"))
        return rows

    def _audit_metrics(self, start, end, group):
        window = CRUDEvent.objects.filter(
            datetime__gte=start,
            datetime__lt=end,
            content_type__app_label="nofos",
            content_type__model__in=["nofo", "section", "subsection"],
        )
        unknown_user_count = window.filter(user__isnull=True).count()
        internal_count = window.filter(user__group__in=EXCLUDED_GROUPS).count()

        if group == "all":
            events = window.filter(user__isnull=False).exclude(
                user__group__in=EXCLUDED_GROUPS
            )
        else:
            events = window.filter(user__group=group)

        counts = defaultdict(int)
        objects = defaultdict(set)
        counts["audit.eligible_events"] = events.count()
        counts["audit.unknown_user_events"] = unknown_user_count
        counts["audit.internal_events_excluded"] = internal_count

        for event in events.select_related("content_type").iterator():
            model = event.content_type.model
            object_key = (model, str(event.object_id))

            if event.event_type == CRUDEvent.CREATE:
                signal = f"audit.{model}_created_events"
                counts[signal] += 1
                objects[signal].add(object_key)
                continue
            if event.event_type == CRUDEvent.DELETE:
                signal = f"audit.{model}_deleted_events"
                counts[signal] += 1
                objects[signal].add(object_key)
                continue
            if event.event_type != CRUDEvent.UPDATE:
                continue

            try:
                fields = json.loads(event.changed_fields)
            except (TypeError, json.JSONDecodeError):
                fields = None
            if not isinstance(fields, dict):
                counts["audit.unreadable_changed_fields"] += 1
                objects["audit.unreadable_changed_fields"].add(object_key)
                continue

            action = fields.get("action")
            if action:
                if action in {"nofo_import", "nofo_reimport"}:
                    signal = f"action.{action}"
                elif action == "nofo_print":
                    modes = fields.get("print_mode")
                    mode = modes[0] if isinstance(modes, list) and modes else "unknown"
                    if mode not in {"test", "live"}:
                        mode = "unknown"
                    signal = f"action.nofo_print.{mode}"
                else:
                    # Audit values are data, not safe output labels. Bucket any
                    # future or malformed action instead of echoing its value.
                    signal = "action.other"
                counts[signal] += 1
                objects[signal].add(object_key)
                continue

            for field in fields:
                signal = self._field_signal(model, field)
                if signal is None:
                    continue
                counts[signal] += 1
                objects[signal].add(object_key)

        preferred_order = [
            "audit.eligible_events",
            "audit.unknown_user_events",
            "audit.internal_events_excluded",
        ]
        ordered_signals = preferred_order + sorted(set(counts) - set(preferred_order))
        return [
            (signal, counts[signal], len(objects[signal]) if objects[signal] else "N/A")
            for signal in ordered_signals
        ]

    @staticmethod
    def _field_signal(model, field):
        if field in {"updated", "updated_by"}:
            return None
        if model in {"section", "subsection"} and field == "name":
            return "edit.heading_text"
        if model == "subsection" and field == "tag":
            return "edit.heading_level"
        if model in {"section", "subsection"} and field == "order":
            return "edit.structure_order"
        if model == "subsection" and field == "body":
            return "edit.subsection_body"
        if model == "subsection" and field == "callout_box":
            return "edit.callout_box"
        if model == "nofo" and field in NOFO_METADATA_FIELDS:
            return "edit.nofo_metadata"
        return "edit.other"
