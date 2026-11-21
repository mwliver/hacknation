"""API views of the national AED dataset: /aed, /aed/nearest, /aed/{id}, /aed/stats."""

from functools import partial
from types import SimpleNamespace

import falcon
from django.core.paginator import Paginator
from django.db.models import Max
from django.utils import timezone

from mcod.aed import schema, search
from mcod.aed.deserializers import AedListRequest, AedNearestRequest
from mcod.aed.models import AedRecord, AedSourceLink
from mcod.aed.national import typed_value
from mcod.aed.readiness import open_now, readiness
from mcod.aed.serializers import AedRecordApiResponse, AedStatsApiResponse
from mcod.core.api.handlers import BaseHdlr
from mcod.core.api.views import JsonAPIView
from mcod.core.versioning import versioned


class _Window:
    """Sequence of ``total`` items of which only the current page is materialized (for the django Paginator)."""

    def __init__(self, total: int, items: list, offset: int):
        self.total, self.items, self.offset = total, items, offset

    def __len__(self):
        return self.total

    def __getitem__(self, key):
        start = (key.start or 0) - self.offset
        stop = (key.stop or self.total) - self.offset
        return self.items[max(start, 0) : max(stop, 0)]


def _page(items: list, total: int, page: int, per_page: int, offset: int):
    paginator = Paginator(_Window(total, items, offset), per_page)
    return paginator.page(min(page, paginator.num_pages))


def _now():
    now = timezone.now()
    return timezone.localdate(now), now


def records_by_ids(ids):
    records = AedRecord.objects.filter(pk__in=ids).prefetch_related("source_links__resource")
    by_id = {str(r.pk): r for r in records}
    return [by_id[i] for i in ids if i in by_id]


def _sources(record):
    return [
        {
            "dysponent": link.dysponent,
            "zrodlo_danych": link.zrodlo_danych,
            "zrodlo_id": link.zrodlo_id,
            "id_aed": link.id_aed,
            "zasob_id": link.resource_id,
            "zbior_id": link.resource.dataset_id if link.resource is not None else None,
            "zrodlo_wygrywajace": link.is_primary,
        }
        for link in record.source_links.all()
    ]


def present_record(record, today, now, distance=None, with_sources=False) -> SimpleNamespace:
    """API representation: only fields of the v1 schema + computed fields (never forbidden columns)."""
    attrs = {name: typed_value(name, record.data.get(name, "")) for name in schema.all_field_names()}
    attrs.update(
        id_aed_krajowe=str(record.pk),
        liczba_zrodel=record.liczba_zrodel,
        gotowosc=readiness(record.data, today),
        otwarte_teraz=open_now(record.data, now),
        odleglosc_m=None if distance is None else int(round(distance)),
        zrodla=_sources(record) if with_sources else [],
    )
    return SimpleNamespace(id=str(record.pk), **attrs)


def _total(response) -> int:
    total = response.hits.total
    return total if isinstance(total, int) else total["value"]


class AedListView(JsonAPIView):
    """GET /aed – national AED records with filters, pagination and optional map clusters (``klastry=true``)."""

    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(BaseHdlr):
        deserializer_schema = AedListRequest
        serializer_schema = partial(AedRecordApiResponse, many=True)

        def _get_data(self, cleaned, *args, **kwargs):
            today, now = _now()
            page, per_page = cleaned.get("page", 1), cleaned.get("per_page", 25)
            offset = (page - 1) * per_page
            s = search.base_search(cleaned, today).sort("miejscowosc", "id_aed_krajowe")
            clusters = None
            if cleaned.get("klastry"):
                clusters = search.clusters_from(search.clusters_aggregation(s[:0], cleaned["precyzja"]).execute())
            open_filter = cleaned.get("otwarte_teraz")
            if open_filter is None:
                response = s[offset : offset + per_page].execute()
                total, records = _total(response), records_by_ids(search.ids_from(response))
            else:
                window = records_by_ids(search.ids_from(s[: search.OPEN_NOW_WINDOW].execute()))
                matching = [r for r in window if open_now(r.data, now) is open_filter]
                total, records = len(matching), matching[offset : offset + per_page]
            if not total:
                return []
            result = _page([present_record(r, today, now) for r in records], total, page, per_page, offset)
            result.aggregations = {"klastry": clusters} if clusters is not None else {}
            return result


class AedNearestView(JsonAPIView):
    """GET /aed/nearest?lat=&lon=&limit=5&max_km=2 – the nearest AEDs sorted by distance (``odleglosc_m``)."""

    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(BaseHdlr):
        deserializer_schema = AedNearestRequest
        serializer_schema = partial(AedRecordApiResponse, many=True)

        def _get_data(self, cleaned, *args, **kwargs):
            today, now = _now()
            open_filter = cleaned.get("otwarte_teraz")
            size = cleaned["limit"] if open_filter is None else search.OPEN_NOW_WINDOW
            response = search.nearest_search(
                cleaned["lat"],
                cleaned["lon"],
                cleaned["max_km"],
                size,
                cleaned,
                today,
                cleaned["include_unavailable"],
            ).execute()
            distances = {hit.meta.id: hit.meta.sort[0] for hit in response}
            records = records_by_ids(search.ids_from(response))
            if open_filter is not None:
                records = [r for r in records if open_now(r.data, now) is open_filter]
            return [present_record(r, today, now, distance=distances[str(r.pk)]) for r in records[: cleaned["limit"]]]


class AedDetailView(JsonAPIView):
    """GET /aed/{id} – one national AED record with the list of its data sources."""

    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(BaseHdlr):
        serializer_schema = AedRecordApiResponse

        def clean(self, id, *args, **kwargs):
            return {}

        def _get_data(self, cleaned, id, *args, **kwargs):
            record = AedRecord.objects.filter(pk=id).exclude(status_urzadzenia="NIESPRAWNY").first()
            if record is None:
                raise falcon.HTTPNotFound()
            today, now = _now()
            return present_record(record, today, now, with_sources=True)


class AedStatsView(JsonAPIView):
    """GET /aed/stats – counters for the campaign page."""

    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(BaseHdlr):
        serializer_schema = AedStatsApiResponse

        def _get_data(self, cleaned, *args, **kwargs):
            today, _ = _now()
            records = list(AedRecord.objects.exclude(status_urzadzenia="NIESPRAWNY").only("data"))
            total = len(records)
            counts = {}
            for record in records:
                value = readiness(record.data, today)
                counts[value] = counts.get(value, 0) + 1
            with_electrodes = sum(1 for r in records if r.data.get("data_waznosci_elektrod"))
            last = AedRecord.objects.aggregate(last=Max("modified"))["last"]
            links = AedSourceLink.objects.all()
            return SimpleNamespace(
                id="aed",
                liczba_aed=total,
                liczba_dysponentow=links.values("dysponent").distinct().count(),
                liczba_zrodel_danych=links.exclude(resource=None).values("resource").distinct().count(),
                odsetek_z_data_waznosci_elektrod=round(100.0 * with_electrodes / total, 1) if total else 0.0,
                gotowosc=counts,
                data_aktualizacji=last.isoformat() if last else None,
            )
