import getpass
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.audit.context import acting_as
from apps.domains.models import Domain


class Command(BaseCommand):
    help = "Create the first administrator and the top-level domain. Safe to run again."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--root-domain", default="Global")
        parser.add_argument(
            "--password-env",
            default="NLIUE_ADMIN_PASSWORD",
            help="Environment variable holding the password. Prompts when it is not set.",
        )

    def handle(self, *args, email, root_domain, password_env, **options):
        User = get_user_model()
        with acting_as(label="system:bootstrap"):
            domain, made_domain = Domain.objects.get_or_create(
                parent=None, name=root_domain, defaults={"kind": "organisation"}
            )
            if User.objects.filter(email__iexact=email).exists():
                self.stdout.write("Administrator already exists; nothing changed for the user.")
            else:
                password = os.environ.get(password_env) or getpass.getpass("Password: ")
                try:
                    validate_password(password, User(email=email))
                except ValidationError as exc:
                    raise CommandError(" ".join(exc.messages)) from None
                User.objects.create_superuser(email=email, password=password)
                self.stdout.write(self.style.SUCCESS(f"Created administrator {email}."))
        self.stdout.write(
            f"Top-level domain: {domain.name} ({'new' if made_domain else 'existing'})"
        )
