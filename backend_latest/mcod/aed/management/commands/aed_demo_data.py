"""
Loads FICTIONAL demo data for the AED prototype: three data providers (institutions) with AED v1 resources
(mcod/aed/tests/fixtures/providers) and the institution owning the national dataset, then builds the national dataset.
"""

import os

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.test import override_settings
from django.utils import timezone

from mcod.aed.models import DATA_STANDARD_AED_V1
from mcod.aed.services import ensure_aed_tags, validate_resource

PROVIDERS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "tests", "fixtures", "providers")
NATIONAL_ORGANIZATION = {"title": "Krajowy rejestr AED (prototyp)", "slug": "krajowy-rejestr-aed-prototyp", "abbreviation": "AED"}
PROVIDERS = [
    ("dostawca_jst_otwock.csv", "Urząd Miasta Testowego (fikcyjny)", "urzad-miasta-testowego-fikcyjny", "local"),
    ("dostawca_wlasciciel_warszawa.csv", "Przychodnia Testowa Sp. z o.o. (fikcyjna)", "przychodnia-testowa-fikcyjna", "private"),
    ("dostawca_osm_mapa.csv", "Fundacja Mapa AED (fikcyjna)", "fundacja-mapa-aed-fikcyjna", "private"),
]
DEMO_EMAIL = "aed-prototyp@example.invalid"


def get_or_create_organization(title: str, slug: str, institution_type: str, abbreviation: str = "TEST"):
    from mcod.organizations.models import Organization

    organization = Organization.objects.filter(slug=slug).first()
    if organization is None:
        organization = Organization.objects.create(
            title=title,
            slug=slug,
            abbreviation=abbreviation,
            institution_type=institution_type,
            email=DEMO_EMAIL,
            city="Warszawa",
            postal_code="00-001",
            street="Testowa",
            street_number="1",
            status="published",
        )
    return organization


def create_provider_resource(organization, file_name: str):
    from mcod.datasets.models import Dataset
    from mcod.resources.models import Resource, ResourceFile

    title = f"Defibrylatory AED – {organization.title}"
    dataset = Dataset.objects.filter(organization=organization, title=title).first()
    if dataset is None:
        dataset = Dataset.objects.create(
            title=title,
            notes="Fikcyjne dane demonstracyjne prototypu Misja AED (wzorcowy zakres danych AED v1).",
            organization=organization,
            license_chosen=Dataset.LICENSE_CC_BY,
            update_frequency="monthly",
            has_dynamic_data=False,
            has_high_value_data=False,
            has_high_value_data_from_ec_list=False,
            has_research_data=False,
            status="published",
        )
    resource = Resource.objects.filter(dataset=dataset).first()
    if resource is None:
        resource = Resource.objects.create(
            title=f"AED – {organization.title} (standard AED v1)",
            description="Plik zgodny ze wzorcowym zakresem danych AED v1. Dane fikcyjne.",
            dataset=dataset,
            has_dynamic_data=False,
            has_high_value_data=False,
            has_high_value_data_from_ec_list=False,
            has_research_data=False,
            contains_protected_data=False,
            status="published",
            data_date=timezone.localdate(),
            data_standard=DATA_STANDARD_AED_V1,
        )
        with open(os.path.join(PROVIDERS_DIR, file_name), "rb") as f:
            content = f.read()
        ResourceFile.objects.create(
            resource=resource, is_main=True, file=SimpleUploadedFile(file_name, content, content_type="text/csv")
        )
    ensure_aed_tags(dataset)
    return Resource.raw.get(pk=resource.pk)


class Command(BaseCommand):
    help = "Loads fictional AED demo providers and builds the national AED dataset (prototype only)."

    def add_arguments(self, parser):
        parser.add_argument("--no-build", action="store_true", help="Only load providers, do not build the national dataset.")

    def handle(self, *args, **options):
        if not settings.AED_ENABLED:
            raise CommandError("Set AED_ENABLED=True to load AED demo data.")
        with transaction.atomic():
            national = get_or_create_organization(
                NATIONAL_ORGANIZATION["title"], NATIONAL_ORGANIZATION["slug"], "state", NATIONAL_ORGANIZATION["abbreviation"]
            )
            resources = []
            for file_name, title, slug, institution_type in PROVIDERS:
                organization = get_or_create_organization(title, slug, institution_type)
                resources.append(create_provider_resource(organization, file_name))
        for resource in resources:
            report = validate_resource(resource)
            self.stdout.write(
                f"resource {resource.pk}: compliant={report.is_compliant} errors={report.errors_count} "
                f"warnings={report.warnings_count}"
            )
        self.stdout.write(f"AED_NATIONAL_ORGANIZATION_ID={national.pk}  (set it in .env)")
        if options["no_build"]:
            return
        from mcod.aed.national import build_national_dataset

        with override_settings(AED_NATIONAL_ORGANIZATION_ID=settings.AED_NATIONAL_ORGANIZATION_ID or national.pk):
            result = build_national_dataset()
        for key, value in result.as_dict().items():
            self.stdout.write(f"{key}: {value}")
