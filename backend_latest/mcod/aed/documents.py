from django.conf import settings as dj_settings
from django_elasticsearch_dsl import fields
from django_elasticsearch_dsl.registries import registry

from mcod.aed.aggregation import _comparable
from mcod.aed.models import AedRecord
from mcod.core.db.elastic import Document

DATE_FIELDS = ("data_aktualizacji", "data_ostatniej_kontroli", "data_waznosci_elektrod", "data_waznosci_baterii")


class AedDocument(Document):
    """
    Search index of the national AED dataset ("aed"). Only fields used for filtering and sorting are indexed;
    API responses are built from the database records (AedRecord) with a whitelist of schema fields.
    """

    id_aed_krajowe = fields.KeywordField()
    location = fields.GeoPointField()
    miejscowosc = fields.KeywordField()
    miejscowosc_lc = fields.KeywordField()
    kod_teryt_gminy = fields.KeywordField()
    status_urzadzenia = fields.KeywordField()
    status_weryfikacji = fields.KeywordField()
    dostep_publiczny = fields.BooleanField()
    nazwa_obiektu = fields.TextField()
    data_aktualizacji = fields.DateField()
    data_ostatniej_kontroli = fields.DateField()
    data_waznosci_elektrod = fields.DateField()
    data_waznosci_baterii = fields.DateField()
    liczba_zrodel = fields.IntegerField()

    class Index:
        name = dj_settings.ELASTICSEARCH_INDEX_NAMES.get("aed", "aed")
        settings = dj_settings.ELASTICSEARCH_DSL_INDEX_SETTINGS

    class Django:
        model = AedRecord
        ignore_signals = True  # indexed in bulk by mcod.aed.national.build_national_dataset
        queryset_pagination = 1000

    def prepare_id_aed_krajowe(self, instance):
        return str(instance.pk)

    def prepare_location(self, instance):
        return {"lat": instance.szerokosc_geograficzna, "lon": instance.dlugosc_geograficzna}

    def prepare_miejscowosc_lc(self, instance):
        return _comparable(instance.miejscowosc)

    def prepare_status_weryfikacji(self, instance):
        return instance.data.get("status_weryfikacji")

    def prepare_nazwa_obiektu(self, instance):
        return instance.data.get("nazwa_obiektu")

    def _date(self, instance, name):
        return instance.data.get(name) or None

    def prepare_data_aktualizacji(self, instance):
        return self._date(instance, "data_aktualizacji")

    def prepare_data_ostatniej_kontroli(self, instance):
        return self._date(instance, "data_ostatniej_kontroli")

    def prepare_data_waznosci_elektrod(self, instance):
        return self._date(instance, "data_waznosci_elektrod")

    def prepare_data_waznosci_baterii(self, instance):
        return self._date(instance, "data_waznosci_baterii")


if dj_settings.AED_ENABLED:
    registry.register_document(AedDocument)
