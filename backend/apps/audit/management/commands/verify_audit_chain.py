from django.core.management.base import BaseCommand, CommandError

from apps.audit.service import verify_chain


class Command(BaseCommand):
    help = "Check the audit log hash chain. Exits non-zero at the first broken record."

    def handle(self, *args, **options):
        intact, bad_id, checked = verify_chain()
        if not intact:
            raise CommandError(f"Audit chain broken at event {bad_id} after {checked} records.")
        self.stdout.write(self.style.SUCCESS(f"Audit chain intact: {checked} records checked."))
