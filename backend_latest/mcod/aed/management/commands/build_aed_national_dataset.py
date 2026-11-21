from django.core.management.base import BaseCommand

from mcod.aed.national import build_national_dataset


class Command(BaseCommand):
    help = "Builds the national AED dataset from all AED v1 resources (deduplication, ES index, publication)."

    def add_arguments(self, parser):
        parser.add_argument("--no-publish", action="store_true", help="Do not create/update the portal dataset.")
        parser.add_argument("--no-index", action="store_true", help="Do not update the Elasticsearch index.")

    def handle(self, *args, **options):
        result = build_national_dataset(publish_dataset=not options["no_publish"], index=not options["no_index"])
        for key, value in result.as_dict().items():
            self.stdout.write(f"{key}: {value}")
