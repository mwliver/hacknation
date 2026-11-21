import os

from django.core.management.base import BaseCommand

from mcod.aed import export


class Command(BaseCommand):
    help = "Generates the AED v1 model data scope files (XLSX, CSV, JSON schema) from mcod/aed/schema/aed_v1.json."

    def add_arguments(self, parser):
        parser.add_argument("--out", default="data/aed_export", help="Output directory (created if missing).")

    def handle(self, *args, **options):
        out_dir = options["out"]
        os.makedirs(out_dir, exist_ok=True)
        outputs = {
            export.XLSX_FILENAME: export.build_xlsx(with_examples=True),
            export.CSV_FILENAME: export.build_csv(with_examples=True),
            export.SCHEMA_FILENAME: export.build_schema_json(),
        }
        for filename, content in outputs.items():
            path = os.path.join(out_dir, filename)
            with open(path, "wb") as f:
                f.write(content)
            self.stdout.write(f"Saved {path} ({len(content)} B)")
