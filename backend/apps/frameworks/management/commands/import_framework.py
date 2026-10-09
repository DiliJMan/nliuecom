from django.core.management.base import BaseCommand, CommandError

from apps.audit.context import acting_as
from apps.frameworks import loader
from apps.frameworks.importers import PARSERS
from apps.frameworks.importers.spec import ImportProblem


class Command(BaseCommand):
    help = "Load a framework from a file you hold: an SCF workbook, a licensed ISO 27001 PDF, or a project JSON file."

    def add_arguments(self, parser):
        parser.add_argument("kind", choices=sorted(PARSERS))
        parser.add_argument("path")
        parser.add_argument(
            "--replace", action="store_true", help="Overwrite a framework with the same slug"
        )

    def handle(self, *args, kind, path, replace, **options):
        parse, _ = PARSERS[kind]
        try:
            spec = parse(path)
            for note in spec.notes:
                self.stdout.write(self.style.WARNING(note))
            with acting_as(label=f"system:import_framework:{kind}"):
                framework = loader.load(spec, replace=replace)
        except ImportProblem as exc:
            raise CommandError(str(exc)) from None
        count = framework.nodes.count()
        links = framework.nodes.filter(mappings_out__isnull=False).distinct().count()
        self.stdout.write(
            self.style.SUCCESS(f"Loaded {framework}: {count} requirements, {links} with mappings.")
        )
