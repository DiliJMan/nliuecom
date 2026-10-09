from django.core.management.base import BaseCommand

from apps.audit.context import acting_as
from apps.tasks import service


class Command(BaseCommand):
    help = "Email assignees about tasks that are due soon or overdue. Run it once a day."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true", help="Count what would be sent, send nothing"
        )

    def handle(self, *args, dry_run, **options):
        with acting_as(label="system:reminders"):
            result = service.send_reminders(dry_run=dry_run)
        verb = "Would send" if dry_run else "Sent"
        self.stdout.write(
            f"{verb} {result['recipients']} message(s) covering {result['tasks']} task(s)."
        )
