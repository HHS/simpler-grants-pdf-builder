from django.core.management.base import BaseCommand
from django.db import transaction

from nofos.management.commands.data.hhs_policy_language_fy27_draft import (
    SLOTS,
    TEMPLATE_VERSION,
)
from nofos.models import PolicyLanguageSlot, PolicyLanguageVariant


class Command(BaseCommand):
    help = (
        "Ingests canonical HHS Department Governance policy-language slots into "
        "PolicyLanguageSlot/PolicyLanguageVariant. Re-runnable: re-running with a "
        "revised data set supersedes the prior slot for a given slot_key (marking "
        "it is_current=False and pointing superseded_by at the new one) rather than "
        "editing it in place, so already-tagged NOFOs keep an explainable history "
        "of what canonical text was current when they were checked."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing anything.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        created, superseded, unchanged, version_updated = 0, 0, 0, 0

        with transaction.atomic():
            for slot_data in SLOTS:
                slot_data = dict(slot_data)  # avoid mutating the module-level data
                slot_key = slot_data.pop("slot_key")
                name = slot_data.pop("name")
                variants_data = slot_data.pop("variants")
                slot_data.setdefault("match_scope", "whole_subsection")

                existing = (
                    PolicyLanguageSlot.objects.filter(
                        slot_key=slot_key, is_current=True
                    )
                    .order_by("-created_at")
                    .first()
                )

                if existing and self._content_matches(
                    existing, name, slot_data, variants_data
                ):
                    if existing.template_version == TEMPLATE_VERSION:
                        unchanged += 1
                        continue

                    # Same name/fields/variants, only the version label moved
                    # (e.g. a template re-issued verbatim under a new FY tag).
                    # Update the label in place rather than superseding - a
                    # supersession implies the canonical text actually changed,
                    # which would be misleading here and would needlessly
                    # invalidate policy_language_status on NOFOs already
                    # checked against this slot.
                    if dry_run:
                        self.stdout.write(
                            f"Would update template_version: {slot_key} — {name} "
                            f"({existing.template_version} -> {TEMPLATE_VERSION})"
                        )
                    else:
                        existing.template_version = TEMPLATE_VERSION
                        existing.save(update_fields=["template_version"])
                    version_updated += 1
                    continue

                new_slot = PolicyLanguageSlot(
                    slot_key=slot_key,
                    name=name,
                    template_version=TEMPLATE_VERSION,
                    **slot_data,
                )

                if dry_run:
                    action = "Would supersede" if existing else "Would create"
                    self.stdout.write(f"{action}: {slot_key} — {name}")
                else:
                    # Flip the old row's is_current to False (and save it) BEFORE
                    # inserting the new one: both rows briefly having
                    # is_current=True at once would violate
                    # unique_current_policy_language_slot_key, even within the
                    # same transaction, since SQLite/Postgres check UNIQUE
                    # constraints immediately rather than at commit.
                    if existing:
                        existing.is_current = False
                        existing.save(update_fields=["is_current"])

                    new_slot.save()
                    for variant in variants_data:
                        PolicyLanguageVariant.objects.create(slot=new_slot, **variant)

                    if existing:
                        existing.superseded_by = new_slot
                        existing.save(update_fields=["superseded_by"])

                if existing:
                    superseded += 1
                else:
                    created += 1

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS(
                f"{'[DRY RUN] ' if dry_run else ''}"
                f"{created} created, {superseded} superseded, "
                f"{version_updated} version_updated, {unchanged} unchanged."
            )
        )

    def _content_matches(self, existing_slot, name, slot_data, variants_data):
        """True if existing_slot's name/fields/variants already match the incoming
        data exactly, regardless of template_version (checked separately by the
        caller)."""
        if existing_slot.name != name:
            return False
        for field, value in slot_data.items():
            if getattr(existing_slot, field) != value:
                return False

        existing_variants = list(
            existing_slot.variants.order_by("id").values_list(
                "label", "parameter_value", "canonical_text"
            )
        )
        incoming_variants = [
            (
                variant.get("label", ""),
                variant.get("parameter_value", ""),
                variant["canonical_text"],
            )
            for variant in variants_data
        ]
        return existing_variants == incoming_variants
