from django.core.management.base import BaseCommand

from nofos.management.commands.data.hhs_policy_language_fy27_draft import (
    SLOTS,
    TEMPLATE_VERSION,
)
from nofos.policy_language_ingest import ingest_policy_language_slots


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
        ingest_policy_language_slots(
            SLOTS,
            TEMPLATE_VERSION,
            self.stdout,
            self.style,
            dry_run=options["dry_run"],
        )
