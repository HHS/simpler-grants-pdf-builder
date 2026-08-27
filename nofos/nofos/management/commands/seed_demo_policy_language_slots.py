from django.core.management.base import BaseCommand
from django.db import transaction

from nofos.management.commands.data.demo_policy_language_slots import (
    SLOTS,
    TEMPLATE_VERSION,
    VERSIONED_PAIR,
)
from nofos.models import PolicyLanguageSlot, PolicyLanguageVariant
from nofos.policy_language_ingest import ingest_policy_language_slots


class Command(BaseCommand):
    help = (
        "Seeds fictional DEMO-* PolicyLanguageSlot/PolicyLanguageVariant rows so "
        "the Department Governance export flag can be demoed - locally or on a "
        "shared dev environment - without any real HHS canonical text. Every "
        "slot_key here is prefixed DEMO- and every variant's canonical_text is "
        "made up for this purpose; none of it is HHS Department Governance "
        "language. Safe to run repeatedly. Intended for a dev/demo database, "
        "not production - it adds content unrelated to real NOFO clearance."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing anything.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        ingest_policy_language_slots(
            SLOTS, TEMPLATE_VERSION, self.stdout, self.style, dry_run=dry_run
        )
        self._seed_versioned_pair(dry_run)

    def _seed_versioned_pair(self, dry_run):
        """
        DEMO-004 needs an old + current pair (is_current=False -> True,
        superseded_by set) to demonstrate "matches_prior_version" - see the
        VERSIONED_PAIR docstring in the data module. Created directly here,
        idempotently, rather than through ingest_policy_language_slots, which
        only ever supersedes a row it finds already in the database and so
        can't produce this pairing in a single pass.
        """
        slot_key = VERSIONED_PAIR["slot_key"]
        if PolicyLanguageSlot.objects.filter(slot_key=slot_key).exists():
            self.stdout.write(f"Unchanged: {slot_key} versioned pair already seeded")
            return

        if dry_run:
            self.stdout.write(
                f"Would create: {slot_key} versioned pair (superseded + current)"
            )
            return

        shared_fields = {
            "name": VERSIONED_PAIR["name"],
            "slot_type": VERSIONED_PAIR["slot_type"],
            "match_scope": VERSIONED_PAIR.get("match_scope", "whole_subsection"),
            "required": VERSIONED_PAIR.get("required", False),
            "flag_prominently": VERSIONED_PAIR.get("flag_prominently", False),
        }

        with transaction.atomic():
            old = PolicyLanguageSlot.objects.create(
                slot_key=slot_key,
                template_version=VERSIONED_PAIR["old_template_version"],
                is_current=False,
                **shared_fields,
            )
            PolicyLanguageVariant.objects.create(
                slot=old, canonical_text=VERSIONED_PAIR["old_canonical_text"]
            )

            current = PolicyLanguageSlot.objects.create(
                slot_key=slot_key,
                template_version=TEMPLATE_VERSION,
                is_current=True,
                **shared_fields,
            )
            PolicyLanguageVariant.objects.create(
                slot=current, canonical_text=VERSIONED_PAIR["new_canonical_text"]
            )

            old.superseded_by = current
            old.save(update_fields=["superseded_by"])

        self.stdout.write(f"Created: {slot_key} versioned pair (superseded + current)")
