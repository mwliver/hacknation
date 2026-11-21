# Misja AED – plan prac (prototyp na dane.gov.pl)

Status: **Plan zaakceptowany 2026-11-21 (wszystkie rekomendacje z sekcji 4). Faza 1 zakończona.** Gałąź: `feature/aed`.
Data: 2026-11-21

---

## 1. Wyniki eksploracji

### 1.1 Struktura repozytorium

```
hacknation/                 # repo git (monorepo zespołu)
├── backend_latest/         # Django 2.2.9 + Falcon 4 + Celery 5.5 + ES (django-elasticsearch-dsl 6.4) + Wagtail 2.13, Python 3.8
├── frontend_latest/        # Angular 18.2, Jest 29, ESLint 9 + Prettier 3, ngx-translate 16
└── docs/aed/               # dokumentacja konkursowa (ten plik)
```
Nazwy katalogów zgodne z założeniami.

### 1.2 Backend – ustalenia

| Obszar | Co jest w repo | Wniosek dla AED |
|---|---|---|
| Aplikacje `mcod/` | `academy, alerts, applications, articles, categories, cms, core, counters, datasets, discourse, guides, harvester, histories, laboratory, lib, licenses, logingovpl, newsletter, organizations, pn_apps, regions, reports, resources, schedules, search, searchhistories, showcases, special_signs, submissions, suggestions, tags, users, watchers` | nowa aplikacja `mcod/aed` w tym samym układzie (`apps.py, models.py, admin.py, documents.py, serializers.py, deserializers.py, views.py, tasks.py, management/commands, tests/`), dopisana do `INSTALLED_APPS` w `mcod/settings/base.py` |
| Modele | `datasets.Dataset`, `resources.Resource` (+ `ResourceFile`, `TaskResult`), `organizations.Organization`, `tags.Tag` (z `language`), `categories.Category` (M2M `Dataset.categories`) | bez zmian w logice; jedna nowa kolumna w `Resource` (migracja) |
| Flagi specjalne | `has_dynamic_data`, `has_high_value_data`, `has_high_value_data_from_ec_list`, `has_research_data` – `NullBooleanField` **równolegle na Resource i Dataset**; przechodzą przez: model → `forms.py` → `admin.py` (fieldsets, `*_info` dla importowanych) → `documents.py` (ES) → `serializers.py` (API i metadane) → `deserializers.py` (`FilterField`) → `mcod/search/deserializers.py` (agregacje `by_has_*`) | flaga AED przechodzi **dokładnie przez te same warstwy** (patrz 2.1) |
| Walidacja zasobów | `entrypoint_process_resource_file_validation_task` (kolejka `resources`): 1) `process_resource_res_file_task` (plik), 2) `revalidate_tabular_data` → `process_resource_file_data_task` (schemat tabeli, `data.validate()`, `data.index()` do ES `resource-<id>`), 3) link, 4) openness score, 5) ES/RDF. Wynik zapisywany w `TaskResult` (M2M `file_tasks/data_tasks/link_tasks`) + `*_tasks_last_status`. Komenda `validate_resources`. Trasy Celery w `CELERY_TASK_ROUTES` | po kroku 2 (dla zasobów AED i przy `AED_ENABLED`) dokładamy zadanie `mcod.aed.tasks.validate_aed_resource_task` na kolejce `resources` |
| Dane tabelaryczne / geo | `mcod/resources/indexed_data.py` – `TabularData` / `GeoData`, pole `point` = `GeoPoint`; `has_map` ustawiany po indeksacji | zasób krajowy CSV z kolumnami lat/lon może dostać podgląd tabeli i mapy z istniejącego mechanizmu |
| API | Falcon, `mcod/routes.py` (lista krotek), widoki `JsonAPIView` + handlery (`SearchHdlr`, `RetrieveOneHdlr`, `CreateOneHdlr`), dekorator `@versioned` (wersje `1.0`…`1.4`, frontend używa `/1.4`), odpowiedzi **JSON:API** (`application/vnd.api+json`, `marshmallow-jsonapi`), filtry `mcod/core/api/search/fields.py` (m.in. `geo_bounding_box`, `geo_distance`, agregacje kafelkowe `TileAggregationMixin`) | endpointy `/aed/...` jako zwykłe widoki `JsonAPIView`, rejestrowane w `routes.py` tylko gdy `AED_ENABLED` |
| Upload plików w API | `mcod/submissions/views.py` – multipart, `secure_filename`, `python-magic`, limity z settings | `POST /aed/validate` na tym samym wzorcu |
| Throttling | `mcod/core/api/limiter.py` – `rate_limiter` (Redis, `@rate_limiter(limits="10/minute, 500/day")`, musi być nad `@versioned`) | użyty w `POST /aed/validate` |
| Elasticsearch | `ELASTICSEARCH_INDEX_NAMES`, dokumenty `@registry.register_document` (`mcod.core.db.elastic.Document`), `GeoPointField` w `regions`, rebuild: `manage.py search_index --rebuild -f` | dokument `AedDocument`, indeks `aed` z polem `location: geo_point` |
| Celery beat | `django_celery_beat` (DatabaseScheduler), `UPDATE_TASKS_CELERY_BEAT_TIME` | zadanie okresowe `build_aed_national_dataset_task` rejestrowane migracją danych (`PeriodicTask`) |
| Panel dostawcy | Django admin + django-suit (`mcod/resources/admin.py` – fieldsets, zakładki), uprawnienia `rules` | pole wyboru standardu w formularzu zasobu + zakładka „Standard AED v1” z raportem (readonly) |
| Tłumaczenia | gettext: `translations/system/{pl,en}/LC_MESSAGES`, `django-modeltrans` dla pól modeli (`i18n = TranslationField`) | teksty backendu przez `gettext_lazy`; opisy pól PL/EN siedzą w schemacie JSON (jedno źródło) |
| Feature flagi | Unleash (`mcod/unleash.py`, `is_enabled("S69_...")`) + zwykłe `env.bool(...)` w settings | `AED_ENABLED = env.bool("AED_ENABLED", False)` – zgodnie z wymaganiem; Unleash wymaga zdalnego serwera, więc nie nadaje się do prototypu |
| Zależności | `openpyxl 3.1.5`, `defusedxml`, `tableschema`, `tabulator`, `goodtables`, `jsonschema`, `pyproj` są już w `Pipfile.lock` (`openpyxl` jest importowany bezpośrednio w `mcod/resources/dga_utils.py`); **brak** biblioteki `opening_hours` | **nie trzeba nowych zależności backendu**; podzbiór `opening_hours` implementujemy sami |
| Testy | `pytest` 6.2 + `pytest-django`, `pytest-bdd`, `factory-boy`, xdist (`-n3`), markery `component_api`, `component_cms`, `depends_on_component`; ustawienia `mcod.settings.test` | testy AED w `mcod/aed/tests/`, API z markerem `component_api` |
| Lint | `.flake8` (max 130 znaków, complexity 10), `black`, `isort` (pre-commit) | |

**Uruchamianie (lokalnie brak Pythona – wszystko przez Dockera, Docker działa):**
```bash
cd backend_latest
docker compose -f docker-compose.local.yml run mcod-local-tests -n1 mcod/aed/tests --no-cov   # testy AED
docker compose -f docker-compose.local.yml run mcod-local-tests mcod/resources --no-cov        # regresja zasobów
docker compose -f docker-compose.local.yml run --entrypoint "flake8 mcod/aed" mcod-local-tests  # lint
docker compose -f docker-compose.local.yml run mcod-local-run python manage.py migrate
```
Uwaga: kontener montuje tylko `mcod/`, `data/`, `test-data/` itd. – `../docs/aed` nie jest widoczny. Komenda eksportu będzie pisać do `data/aed_export/`, a skrypt `docs/aed/export.sh` skopiuje pliki do `docs/aed/`.

### 1.3 Frontend – ustalenia

| Obszar | Co jest w repo | Wniosek |
|---|---|---|
| Struktura | `src/app/{pages, shared, services, layout, user, ssr}`; strony jako moduły lazy (`DatasetModule`) i nowszy wzorzec **standalone + `*.routes.ts`** (`pages/broken-links/broken-links.routes.ts`) | `pages/aed/aed.routes.ts` + standalone komponenty (najnowszy wzorzec) |
| Routing | `app-routing.module.ts`, lokalizowane ścieżki `@gilsdav/ngx-translate-router` (`'!dataset'` → klucz `ROUTES.dataset` w i18n), SSR (`@angular/ssr`) | ścieżki `!aed`, `!aed/!map`, `!aed/!share` → PL `/aed`, `/aed/mapa`, `/aed/udostepnij`; EN `/en/aed/map`, `/en/aed/share` |
| i18n | `@ngx-translate`, `src/assets/i18n/pl.json` i `en.json` | nowa sekcja `"Aed": {...}` + klucze `ROUTES.*` |
| Mapy | `leaflet 1.9.4` + `@asymmetrik/ngx-leaflet`, `LeafletService` (SSR-safe), `shared/map/map.component.ts` – **klastrowanie po stronie serwera** (agregacje ES kafelkowe, `aggregationThreshold`), `NominatimGeocodeService` (geokodowanie adresu), `UserLocationData` | **bez nowej zależności**: klastrowanie z agregacji ES, wyszukiwanie adresu przez istniejący serwis Nominatim |
| UI | Bootstrap 5.3, Angular Material/CDK 18, FontAwesome, `HighContrastService`, `shared/*` (breadcrumbs, data-table, buttons, info-tooltip, forms, form-validators, feedback) | reużywamy `data-table`, `breadcrumbs`, przyciski i style |
| Feature flagi | `FeatureFlagService` + `FeatureFlagDirective` – klient Unleash (`flags.dane.gov.pl`) | patrz 2.8 – flaga frontu sterowana z backendu |
| API | `services/api/api.config.ts` (enum ścieżek, `apiVersion = '/1.4'`), `RestService`/`AbstractService` | `AedService` + wpisy `aed*` w `ApiConfig` |
| Testy / lint | `npm test` (jest, `jest-preset-angular`), `npm run lint` (`ng lint`), `npm run format` (prettier) | testy `*.spec.ts` obok komponentów |
| E2E | **brak Playwright i Cypress** | skrypt zrzutów ekranu wymaga nowej zależności – pytanie poniżej |

---

## 2. Decyzje projektowe

### 2.1 Oznaczenie AED – pole na **zasobie** (`Resource.data_standard`)
- `data_standard = CharField(max_length=20, choices=[("AED_V1", "Standard AED v1")], null=True, blank=True)` + migracja.
- **Dlaczego zasób, a nie zbiór:** walidacji podlega konkretny plik (zasób), nie zbiór; zbiór dysponenta może mieć też inne zasoby (np. PDF z regulaminem). Istniejące flagi `has_*` żyją na obu poziomach, ale ich „prawdziwa” informacja jest na zasobie (formularz zasobu ma walidację zgodności z flagami zbioru). Pole tekstowe zamiast `is_aed_v1` daje miejsce na kolejne standardy (`AED_V2`, inne zbiory wzorcowe) bez nowych migracji logiki.
- Na poziomie zbioru: właściwość wyliczana `Dataset.has_aed_v1_resources` indeksowana w ES (jak `has_research_data`), żeby frontend pokazał odznakę na stronie zbioru i można było filtrować.
- Przepływ jak `has_research_data`: `forms.py` (pole wyboru „Standard danych”), `admin.py` (fieldset), `documents.py` (`data_standard` keyword), `serializers.py`, `deserializers.py` (`FilterField` `data_standard`).
- Pole widoczne i obsługiwane wyłącznie przy `AED_ENABLED=True` (formularz ukrywa je, gdy flaga wyłączona) – zero zmian zachowania przy wyłączonej fladze.
- **Tag „AED”**: przy zapisie zasobu z `data_standard=AED_V1` sygnał `mcod/aed/signals.py` dopina do zbioru istniejące tagi `AED` (pl) i `AED` (en) (tworzone migracją danych, `get_or_create`). Dzięki temu działa istniejący filtr wyszukiwarki po tagach, bez nowego mechanizmu.

### 2.2 Schemat jako jedno źródło prawdy
- `backend_latest/mcod/aed/schema/aed_v1.json` – Frictionless Table Schema: `fields[]` z `name, type, format, title{pl,en}, description{pl,en}, example, constraints{required, enum, pattern, minimum, maximum}` oraz własne rozszerzenia z prefiksem `x-aed-` (`x-aed-presence: required|if_known|extended`, `x-aed-enum-labels{pl,en}`), plus sekcje `x-aed-forbidden-fields`, `x-aed-file-rules{pl,en}`, `x-aed-source-priority`, `x-aed-examples` (3 fikcyjne wiersze), `primaryKey: id_aed`.
- `mcod/aed/schema/__init__.py` – loader (`load_schema()`, `required_fields()`, `extended_fields()`, `enums()`) – **jedyny kod, który czyta listę pól**. Walidator, szablony, XLSX, `/aed/schema`, model i serializer API biorą pola stąd.
- Model `AedRecord` (zbiór krajowy) musi mieć kolumny w bazie – lista kolumn w modelu jest jedynym miejscem duplikacji; test `test_model_matches_schema` pilnuje zgodności.

### 2.3 Walidator (`mcod/aed/validation.py`)
- Czysta funkcja `validate_file(fileobj, filename) -> ValidationReport` (bez Django ORM) – używana i przez zadanie Celery, i przez `POST /aed/validate`.
- CSV: odczyt bajtów → próba `utf-8` (BOM tolerowany, z ostrzeżeniem) → `csv` z przecinkiem; XLSX: `openpyxl.load_workbook(read_only=True, data_only=True)`, pierwszy arkusz, `.xlsm` odrzucany, limit `AED_MAX_ROWS=50000` (przerwanie odczytu po przekroczeniu), komórki daty z Excela konwertowane do ISO.
- Raport: `{summary: {rows, errors, warnings, is_compliant}, issues: [{row, column, code, level, message_pl, message_en}]}`. W API pola po polsku zgodnie ze specyfikacją (`wiersz, kolumna, kod, poziom, komunikat_pl, komunikat_en`).
- Nagłówki zakazane: normalizacja (lowercase, usunięcie polskich znaków przez `unicodedata` + mapowanie `ł→l`, spacje/myślniki → `_`) i porównanie z listą ze schematu.
- **RODO w raporcie:** komunikaty nie zawierają wartości komórek z kolumn zakazanych ani `telefon_kontaktowy`; dla pól zakazanych raport podaje tylko nazwę kolumny. Logi zawierają wyłącznie liczniki.
- Kody reguł (stałe w `mcod/aed/validation_codes.py`, komunikaty PL/EN w jednym słowniku):
  - ERROR: `MISSING_COLUMN`, `FORBIDDEN_COLUMN`, `ROW_LENGTH`, `REQUIRED_EMPTY`, `INVALID_TYPE` (date/number/boolean/integer), `INVALID_FORMAT` (kod pocztowy, telefon), `ENUM_VALUE`, `OUT_OF_POLAND`, `DUPLICATE_ID`, `FUTURE_UPDATE_DATE`, `ENCODING`, `EMPTY_COLUMN_HEADER`, `EMPTY_ROW`, `TOO_MANY_ROWS`, `UNSUPPORTED_FILE`.
  - WARNING: `UNKNOWN_COLUMN`, `OPENING_HOURS_UNSUPPORTED`, `ELECTRODES_EXPIRED`, `BATTERY_EXPIRED`, `STALE_UPDATE` (>12 mies.), `NEAR_DUPLICATE_5M`, `UTF8_BOM`.
- Odległości: haversine w Pythonie; para <5 m wyszukiwana przez siatkę (bucket ~0,0001°), żeby 50 000 wierszy nie dawało O(n²).
- `opening_hours` (`mcod/aed/opening_hours.py`): brak biblioteki w Pipfile → własny parser podzbioru: `24/7`, dni `Mo..Su` z zakresami i listami (`Mo-Fr,Su`), zakresy godzin (także kilka: `08:00-12:00,13:00-16:00`, przez północ `22:00-06:00`), reguły po `;` (późniejsza nadpisuje), `off`/`closed`, `PH off` (święta: dzień traktowany jak nieznany → `otwarte_teraz = null` tylko w święto; lista świąt PL liczona algorytmicznie, bez zależności). Reszta → `WARNING` i `otwarte_teraz = null`.

### 2.4 Integracja z procesem walidacji portalu
- Nowe zadanie `mcod.aed.tasks.validate_aed_resource_task(resource_id)` na kolejce `resources` (wpis w `CELERY_TASK_ROUTES`).
- Wywołanie: w `entrypoint_process_resource_file_validation_task` po kroku 2 dokładamy jeden warunkowy krok `if settings.AED_ENABLED and resource.data_standard == "AED_V1": validate_aed_resource_task.apply_async_on_commit(...)`. Dla pozostałych zasobów ścieżka bez zmian. Dodatkowo komenda `manage.py validate_aed_resources` (wzorem `validate_resources`) do ponownej walidacji.
- Wynik: model `mcod.aed.models.AedValidationReport` (FK do `Resource`, `created`, `is_compliant`, `rows`, `errors_count`, `warnings_count`, `issues` JSONField, `schema_version`). Ostatni raport = aktualny status. Nie przeciążamy `TaskResult`, żeby nie zmieniać semantyki istniejących statusów walidacji.
- Panel: w `ResourceAdmin` (przy `AED_ENABLED`) readonly fieldset „Standard AED v1” – status (zgodny / N błędów), tabela pierwszych 200 problemów, link do pobrania pełnego raportu CSV (widok admina).
- API: `GET /resources/{id}` dostaje w `attributes` pola `data_standard` i `aed_validation: {is_compliant, errors, warnings, created}` (tylko gdy flaga włączona i zasób AED) + `GET /aed/reports/{resource_id}` z pełną listą problemów.

### 2.5 Zbiór krajowy
- Modele (`mcod/aed/models.py`): `AedRecord` (kolumny schematu v1 + `id_aed_krajowe` UUID, `liczba_zrodel`, `location` lat/lon, `created/modified`), `AedSourceLink` (`db_table = "aed_source_link"`: `aed_record` FK (`id_aed_krajowe`), `dysponent`, `zrodlo_danych`, `zrodlo_id`, `resource` FK, `id_aed` w pliku źródłowym).
- `mcod/aed/aggregation.py` – czyste funkcje: `normalize_row()`, `deduplicate(rows) -> clusters`, `merge(cluster) -> record`:
  1. klucz (`zrodlo_danych`, `zrodlo_id`) – ten sam AED;
  2. różne źródła < 25 m + ta sama `miejscowosc` (porównanie znormalizowane) + ta sama `ulica`, jeśli obie znane – duplikat (union-find na siatce);
  3. zwycięzca wg `WLASCICIEL > JST > APLIKACJA > INNE > OSM`, remis → nowsza `data_aktualizacji`; puste pola uzupełniane z pozostałych w tej samej kolejności.
- Stabilność `id_aed_krajowe` między przebudowami: jeśli klaster zawiera link już powiązany z istniejącym `AedRecord`, rekord jest aktualizowany, a nie tworzony od nowa (ważne dla linków i zgłoszeń).
- Zadanie `mcod.aed.tasks.build_aed_national_dataset_task` (kolejka `periodic`, beat raz na dobę – `PeriodicTask` z migracji danych, wyłączony gdy `AED_ENABLED=False`) i komenda `manage.py build_aed_national_dataset`. Źródła = zasoby `data_standard=AED_V1`, opublikowane, zbiór opublikowany, ostatni raport `is_compliant=True`.
- Publikacja **istniejącymi mechanizmami**: zbiór `Dataset` „Defibrylatory AED w Polsce – zbiór krajowy” w instytucji z `AED_NATIONAL_ORGANIZATION_ID` (settings; dla prototypu instytucja fikcyjna tworzona komendą `aed_demo_data`), kategoria zdrowie (kod `HEAL` z istniejących kategorii), tagi AED/defibrylator, licencja CC0/CC BY 4.0 (wybór z istniejących), `update_frequency = daily`. Zasoby `aed_krajowy.csv`, `aed_krajowy.geojson`, `aed_powiazania_zrodel.csv` jako `Resource` + `ResourceFile` – przy aktualizacji podmieniamy plik w ten sam sposób, co panel, co uruchamia standardowy pipeline (podgląd tabeli, mapa, openness score, ES, RDF).

### 2.6 Indeks i API
- `mcod/aed/documents.py` – `AedDocument` (indeks `aed` dopisany do `ELASTICSEARCH_INDEX_NAMES` tylko gdy `AED_ENABLED`), `location = GeoPointField`, pola słownikowe jako `keyword`, `godziny_dostepnosci` + sparsowana reprezentacja w bazie (gotowość i `otwarte_teraz` liczone przy odpowiedzi, nie w indeksie).
- Endpointy (Falcon, `JsonAPIView`, `@versioned`, JSON:API, prefiks jak reszta API, np. `https://api.dane.gov.pl/1.4/aed`):

| Metoda i ścieżka | Opis |
|---|---|
| `GET /aed` | lista: `miejscowosc`, `kod_teryt_gminy`, `status_urzadzenia`, `dostep_publiczny`, `otwarte_teraz`, `gotowosc`, `bbox=minLon,minLat,maxLon,maxLat`, `page`, `per_page`; przy `bbox` + dużej liczbie punktów `meta.aggregations.tiles` (klastry z `geotile_grid` – wzorzec `TileAggregationMixin`) |
| `GET /aed/nearest?lat=&lon=&limit=5&max_km=2` | `geo_distance` + sort po odległości, pole `odleglosc_m`; pomija `NIESPRAWNY` i domyślnie `CZASOWO_NIEDOSTEPNY` (`include_unavailable=true` zmienia) ; `limit ≤ 50`, `max_km ≤ 50` |
| `GET /aed/{id_aed_krajowe:uuid}` | szczegóły + `relationships.sources` (z `aed_source_link`, z linkiem do zasobu i zbioru źródłowego) |
| `GET /aed/schema` | schemat v1 (JSON, z `aed_v1.json`) |
| `GET /aed/template.csv`, `GET /aed/template.xlsx` | szablony generowane ze schematu |
| `POST /aed/validate` | multipart `file`; CSV/XLSX, limit `AED_VALIDATE_MAX_FILE_SIZE` (domyślnie 10 MB) i 50 000 wierszy, `python-magic` + rozszerzenie, przetwarzanie w pamięci (`BytesIO`), brak zapisu w bazie, `rate_limiter` (np. `10/minute, 200/day`) |
| `GET /aed/stats` | liczniki do strony akcji: liczba AED, liczba dysponentów, odsetek rekordów z datą ważności elektrod |
| `GET /aed/config` | `{enabled, campaign_name, campaign_slogan, campaign_logo_url}` z `AED_CAMPAIGN_*` |
| `GET /aed/reports/{resource_id:int}` | pełny raport walidacji zasobu AED |

- `gotowosc` i `otwarte_teraz` liczone w serializerze (`mcod/aed/readiness.py`, `Europe/Warsaw`, `django.utils.timezone`) w kolejności: NIEGOTOWY → NIEZNANY → WYMAGA_UWAGI → GOTOWY. Granice: „w ciągu 30 dni” = `data_waznosci - dziś ≤ 30` (włącznie); „ponad 90 dni” = `dziś - data_ostatniej_kontroli > 90`. NIEZNANY = brak którejkolwiek daty ważności **lub** kontrola starsza niż 90 dni **lub** `status_weryfikacji ≠ ZWERYFIKOWANY`. Interpretacja: brak `data_ostatniej_kontroli` (pole „jeśli znane”) traktuję jak brak kontroli od ponad 90 dni → NIEZNANY. Do potwierdzenia (pytanie 6).
- Odpowiedzi API budowane z białej listy pól schematu – pola zakazane nie mogą wyciec nawet przypadkiem (test).
- `/aed` jest publiczne, bez logowania; `kod_teryt_gminy` filtruje po prefiksie (województwo/powiat/gmina).

### 2.7 Generator pliku konkursowego
`manage.py export_aed_standard --out <katalog>` → `wzorcowy_zakres_danych_AED_v1.xlsx` (arkusze `dane`, `opis_pol`, `slowniki`, `zasady_pliku`; nagłówki pogrubione, zamrożony wiersz, walidacja danych Excela dla słowników i booleanów, szerokości kolumn), `wzorcowy_zakres_danych_AED_v1.csv`, `aed_v1.json`. `openpyxl` jest już w projekcie (patrz 1.2) – nie dodajemy zależności.

### 2.8 Frontend
- `src/app/pages/aed/`: `aed.routes.ts`, `aed-campaign` (strona akcji), `aed-map` (mapa + lista + filtry), `aed-details` (panel/strona szczegółów), `aed-share` (kreator 4 kroków), `aed-validation-report` (komponent raportu), `aed-readiness-badge`, `aed-emergency-banner` („najpierw dzwoń 112”, `role="note"`, link `tel:112`), `services/aed.service.ts`, `aed-filters.ts` (czysta logika filtrów).
- Mapa: istniejący `LeafletService` (SSR-safe), kafelki OSM z atrybucją; klastry z `meta.aggregations.tiles` (jak `MapComponent`), markery poniżej progu; lista tekstowa obok mapy (pod mapą < 992 px) jest **równoważną** alternatywą – zawiera wszystkie punkty z widoku z paginacją, mapa ma `aria-hidden` dla dekoracji i opis `aria-describedby`; markery osiągalne klawiaturą (Leaflet `keyboard: true`, markery jako przyciski z `title`).
- Geolokalizacja: `navigator.geolocation` (tylko w przeglądarce, `isPlatformBrowser`), obsługa `PERMISSION_DENIED`/`TIMEOUT`/`POSITION_UNAVAILABLE` komunikatem `aria-live="polite"` i fokusem na polu adresu; wyszukiwanie adresu – istniejący `NominatimGeocodeService`.
- „Nawiguj”: `geo:lat,lon?q=lat,lon(nazwa)` na Androidzie, `https://maps.apple.com/?daddr=` na iOS, fallback `https://www.openstreetmap.org/directions?route=;lat,lon`.
- „Zgłoś problem z tym AED”: istniejący mechanizm komentarzy do zasobu (`POST /resources/{id}/comments`, komponent `shared/feedback`) – zgłoszenie trafia do zasobu źródłowego dysponenta (z `aed_source_link`), czyli do tego, kto może dane poprawić.
- Odznaki na `dataset-resource` i `dataset-page`/`dataset-item`: „Standard AED v1” + status walidacji z linkiem do raportu (`/aed/udostepnij?raport=<resource_id>` lub sekcja na stronie zasobu).
- Wyszukiwarka: filtr tagów już istnieje – dodajemy tylko szybki link „Zbiory AED” (tag `AED`) na stronie akcji; jeśli filtr `data_standard` wejdzie do agregacji wyszukiwarki, pokażemy go jako checkbox w istniejących filtrach.
- **Flaga frontu**: Unleash frontu odpytuje zdalny `flags.dane.gov.pl` – lokalnie bezużyteczny. Proponuję `AedEnabledGuard` oparty na `GET /aed/config` (404 przy `AED_ENABLED=False` → trasy przekierowują na 404, odznaki się nie renderują) oraz dodatkowo opcjonalną flagę Unleash `aed_enabled` przez istniejący `FeatureFlagService` (gdy serwer flag ją zna – obie muszą być włączone; gdy serwer niedostępny – decyduje backend). Jedno źródło prawdy = backend.
- Teksty: sekcja `Aed.*` w `pl.json`/`en.json`; opisy pól kreatora z `/aed/schema` (`title.pl/en`, `description.pl/en`) wg bieżącego języka.

### 2.9 Bezpieczeństwo / RODO
- Pola zakazane nigdy nie są parsowane do modeli, ES, API ani logów; plik z takim nagłówkiem dostaje `ERROR FORBIDDEN_COLUMN` i nie trafia do agregacji.
- `telefon_kontaktowy` – tylko numer służbowy; walidator sprawdza wyłącznie format (nie da się automatycznie odróżnić numeru prywatnego), opis pola w schemacie wyraźnie o tym mówi, a wartości nie trafiają do komunikatów ani logów.
- `POST /aed/validate`: limit rozmiaru, typy CSV/XLSX (`.xlsm`/`.xls` odrzucane), `openpyxl` w trybie read-only (makra nie są wykonywane, XML parsowany przez `defusedxml`, który jest w lockfile), limit wierszy, brak zapisu na dysk, `rate_limiter`.
- Fixtures wyłącznie fikcyjne (Otwock, Warszawa, Kraków; nazwy typu „Przychodnia Testowa nr 1”, telefony z puli `+48 000…`).

---

## 3. Fazy pracy

| Faza | Zakres | Kryterium |
|---|---|---|
| 0 | eksploracja, ten plan | akceptacja |
| 1 | `mcod/aed` (szkielet, `AED_*` w settings), `schema/aed_v1.json` + loader, generatory CSV/XLSX, komenda `export_aed_standard`, testy schematu i generatorów | pliki w `docs/aed/`, testy zielone |
| 2 | `Resource.data_standard` (migracja, form, admin, ES, serializery), tag AED, `opening_hours.py`, `validation.py`, `AedValidationReport`, zadanie Celery + wpięcie w pipeline, zakładka w adminie, `POST /aed/validate`, `/aed/schema`, `/aed/template.*`, `/aed/reports/{id}`, `/aed/config`; fixtures po jednym na regułę | testy reguł, czytelny raport |
| 3 | `AedRecord`, `AedSourceLink`, `aggregation.py`, `readiness.py`, komenda i zadanie budowy zbioru krajowego, publikacja zasobów, `AedDocument`, `GET /aed`, `/aed/nearest`, `/aed/{id}`, `/aed/stats`, komenda `aed_demo_data` (3 fikcyjnych dostawców z duplikatami) | zbiór krajowy z fixtures 3 dostawców, `gotowosc` w API |
| 4 | frontend: `AedService`, strona akcji, mapa + lista + szczegóły, kreator dysponenta, odznaki, i18n PL/EN, a11y | 1440 px i 360 px, test klawiaturą |
| 5 | testy Jest, lint obu repo, regresja istniejących testów (`mcod/resources`, `mcod/datasets`), dokumentacja z sekcji 6 | wszystko zielone |

Po każdej fazie: testy + lint → commit → aktualizacja sekcji „Postęp” poniżej.

---

## 4. Pytania do akceptacji

1. **Klastrowanie mapy bez nowej biblioteki** – proponuję klastrowanie po stronie serwera (agregacje ES `geotile_grid`, tak jak istniejąca mapa zasobów) zamiast dodawać `leaflet.markercluster`. Leaflet + kafelki OSM już są w projekcie. Zgoda?
2. **Zrzuty ekranu** – w projekcie nie ma Playwright ani Cypress. Opcje: (a) dodać `@playwright/test` jako devDependency frontendu i skrypt `scripts/aed-screenshots.ts`, (b) tylko instrukcja ręczna w `ZRZUTY_EKRANU.md`. Rekomenduję (a) – ok?
3. **Instytucja zbioru krajowego** – w prototypie tworzę fikcyjną instytucję „Krajowy rejestr AED (prototyp)” i ustawiam `AED_NATIONAL_ORGANIZATION_ID`; docelowo np. Ministerstwo Zdrowia / KPRM. Ok?
4. **Licencja zbioru krajowego** – CC0 1.0 czy CC BY 4.0 (domyślna w portalu)? Rekomenduję CC BY 4.0 zgodnie z domyślną praktyką portalu.
5. **Wpięcie w pipeline** – jedna warunkowa linia w `entrypoint_process_resource_file_validation_task` (czytelne, testowalne) vs. `task_postrun` signal bez edycji istniejącego pliku. Rekomenduję edycję z warunkiem na `AED_ENABLED`.
6. **Brak daty ostatniej kontroli** – czy traktować jak „brak kontroli od ponad 90 dni” (→ `NIEZNANY`)? Rekomenduję tak, bo nie wiemy, czy urządzenie było sprawdzane.

---

## 5. Postęp

- [x] Faza 0 – eksploracja i plan (2026-11-21)
- [x] Faza 1 – schemat v1, loader, generatory CSV/XLSX, `export_aed_standard` (2026-11-21)
- [ ] Faza 2
- [ ] Faza 3
- [ ] Faza 4
- [ ] Faza 5

### Znane problemy / ryzyka
- Brak lokalnego Pythona – testy i komendy backendu tylko przez `docker compose -f docker-compose.local.yml`.
- Django 2.2 / Python 3.8 – bez `match`, bez `zoneinfo` w stdlib → strefa przez `django.utils.timezone` + `pytz` (jest w zależnościach Django 2.2).
- Elasticsearch 6.x (django-elasticsearch-dsl 6.4) – `geotile_grid` dostępne od ES 7.0; jeśli klaster jest 6.x, użyjemy `geohash_grid` (sprawdzę wersję w fazie 3).
- Geokodowanie adresu przez publiczny Nominatim (już używany w portalu) – limity użycia, zostaje jako znane ograniczenie.

### Decyzje po akceptacji (2026-11-21)
Przyjęte rekomendacje z sekcji 4: (1) klastrowanie po stronie serwera, bez `leaflet.markercluster`; (2) `@playwright/test` jako devDependency frontendu do zrzutów ekranu; (3) fikcyjna instytucja „Krajowy rejestr AED (prototyp)”; (4) licencja CC BY 4.0; (5) warunkowy krok w `entrypoint_process_resource_file_validation_task`; (6) brak `data_ostatniej_kontroli` → `NIEZNANY`.

### Faza 1 – co zrobiono
- `mcod/aed/` (app `AedConfig`, w `INSTALLED_APPS`), ustawienia `AED_*` na końcu `mcod/settings/base.py` (`AED_ENABLED=False` domyślnie, `True` w `mcod/settings/test.py`).
- `mcod/aed/schema/aed_v1.json` – schemat (22 pola podstawowe + 7 rozszerzonych, słowniki z etykietami PL/EN, pola zakazane, priorytet źródeł, zasady pliku, 3 fikcyjne przykłady). `mcod/aed/schema/__init__.py` – jedyny loader listy pól (+ `normalize_header`, `is_forbidden_header`, `frictionless_schema`).
- `mcod/aed/export.py` – CSV (UTF-8 bez BOM), XLSX (`dane` z listami rozwijanymi dla słowników/booleanów i komórkami tekstowymi, `opis_pol`, `slowniki`, `zasady_pliku`), JSON.
- `manage.py export_aed_standard --out <dir>`; wygenerowane pliki skopiowane do `docs/aed/`.
- Testy: `mcod/aed/tests/test_schema.py`, `test_export.py` – 57 passed. Lint (isort/black/flake8 w wersjach z pre-commit) – OK.

### Jak uruchamiać (Windows, ten checkout)
- `sh docs/aed/scripts/backend.sh test -n1 mcod/aed/tests --no-cov -p no:cacheprovider`
- `sh docs/aed/scripts/lint_backend.sh [--fix]`
- Eksport: `sh docs/aed/scripts/backend.sh run python manage.py export_aed_standard --out data/aed_export && cp backend_latest/data/aed_export/* docs/aed/`

### Znane problemy (środowisko)
- **Działający stack Dockera (`mcod-api`, `mcod-admin`, `mcod-celery`…) montuje kod z `C:\Users\mwliv\IdeaProjects\backend_latest`, nie z `hacknation/backend_latest`.** Żeby zobaczyć zmiany AED w działającym API/adminie, trzeba uruchomić stack z tego katalogu (albo przepiąć montowania). Nazwa projektu compose jest ta sama (`backend_latest`), dlatego skrypty używają `--no-deps`.
- `core.autocrlf=true` → skrypty `.sh` w repo mają CRLF; `docker compose build` obrazu testowego się wywraca (`distrust-emudhra-roots: not found`), a `tests-entrypoint.sh` nie startuje. Obejście w `docs/aed/scripts/backend.sh` (istniejący obraz `mcod-app:local-tests` + `tr -d '\r'`). Plików portalu nie zmieniałem.
- `black` nie jest zainstalowany w obrazie – `lint_backend.sh` instaluje go tymczasowo w kontenerze.

### Następny krok: Faza 2
`Resource.data_standard` (migracja + form/admin/ES/serializery), tag AED, `opening_hours.py`, `validation.py` + fixtures po jednym na regułę, `AedValidationReport`, zadanie Celery i wpięcie w pipeline, zakładka w adminie, endpointy `validate`, `schema`, `template.*`, `reports/{id}`, `config`.
