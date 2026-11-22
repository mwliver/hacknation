# Ograniczenia prototypu

## Dane i standard
- **Dane w prototypie są fikcyjne** (Otwock, Warszawa, Kraków; „Przychodnia Testowa”, telefony `+48000…`). Prototyp nie
  importuje rzeczywistych rejestrów AED.
- **Brak integracji z systemami CPR/PRM** (System Wspomagania Dowodzenia PRM) i z rejestrami dysponentów – zbiór
  powstaje wyłącznie z zasobów opublikowanych w dane.gov.pl. Kody do szafek pozostają w systemach dyspozytorskich.
- **Weryfikacja na miejscu nie jest automatyczna** – `status_weryfikacji` i daty kontroli deklaruje dysponent.
- **Telefon kontaktowy**: walidator sprawdza tylko format; nie da się automatycznie odróżnić numeru służbowego od prywatnego.
- **TERYT**: `kod_teryt_gminy` jest sprawdzany tylko co do formatu (7 cyfr), bez słownika TERC i bez kontroli zgodności ze współrzędnymi.
- Wersjonowanie standardu: zaimplementowano `AED_V1`; pole `data_standard` jest przygotowane na kolejne wersje/standardy.

## Walidacja
- **Podzbiór składni `opening_hours`**: `24/7`, dni i zakresy dni (`Mo-Fr`, `Fr-Mo`, listy), zakresy godzin (kilka, przez
  północ), reguły po `;`, `off`/`closed`, `PH` (święta w Polsce). Pozostała składnia (np. `sunrise-sunset`, miesiące,
  tygodnie, komentarze) daje **WARNING**, a `otwarte_teraz = null`.
- Odczyt XLSX: tylko pierwszy arkusz, bez formuł i makr (`.xlsm`/`.xls` odrzucane); limit 50 000 wierszy i 10 MB
  (`POST /aed/validate`), 100 MB dla zasobów.
- Słowniki i wartości logiczne są akceptowane bez względu na wielkość liter (normalizowane); kod pocztowy `NNNNN` daje
  ostrzeżenie i jest zapisywany jako `NN-NNN`.

## Zbiór krajowy
- **Deduplikacja jest heurystyczna**: ta sama para `zrodlo_danych` + `zrodlo_id` albo < 25 m + ta sama miejscowość
  (i ulica, jeśli obie znane). Łączenie jest przechodnie (A~B, B~C ⇒ jeden AED) – dwa urządzenia stojące obok siebie
  w różnych plikach mogą zostać połączone; dwa wpisy tego samego AED > 25 m od siebie – nie.
- Budowa zbioru jest pełna (nie przyrostowa) i synchroniczna w jednym zadaniu Celery – przy bardzo dużych danych
  trzeba ją rozbić na partie.
- Przy aktualizacji publikowany jest nowy plik zasobu (nowy `ResourceFile`, jak w mechanizmie DGA) – historia wersji
  plików jest taka jak w portalu.

## API i mapa
- `otwarte_teraz` nie jest indeksowane (zależy od chwili zapytania) – filtr działa w Pythonie na pierwszych **2000**
  wynikach zapytania ES; przy bardzo szerokich zapytaniach część otwartych AED może zostać pominięta.
- Elasticsearch 6.8 – klastry mapy z `geohash_grid` (nie `geotile_grid`); kształt klastrów zależy od siatki geohash.
- Wyszukiwanie adresu korzysta z publicznego **Nominatim** (OpenStreetMap), tak jak istniejąca mapa portalu – ma limity
  użycia i wymaga dostępu do internetu.
- Kafelki mapy z `tile.openstreetmap.org` (z atrybucją) – przy produkcyjnym ruchu potrzebny własny serwer kafelków.
- Markery na mapie nie są osobno fokusowalne; równoważną ścieżką dla klawiatury i czytników ekranu jest lista tekstowa
  „AED w widoku mapy” (WCAG 1.1.1, 2.1.1).
- Link „Nawiguj” zależy od systemu (Android `geo:`, iOS Apple Maps, komputer OpenStreetMap).

## Frontend / środowisko
- Strony AED mają stałe segmenty adresów (`/pl/aed/mapa`, `/en/aed/mapa`) – zgodnie z konwencją portalu, w którym
  segmenty z `!` nie są tłumaczone.
- Filtr „AED” w interfejsie wyszukiwarki: UI wyszukiwarki zbiorów nie ma filtra tagów – strona akcji wyszukuje frazę
  „AED”; API obsługuje `keyword[terms]=AED` i `data_standard[terms]=AED_V1`.
- Feature flag frontendu opiera się na `GET /aed/config` (backend `AED_ENABLED`), a nie na serwerze Unleash, który
  lokalnie jest niedostępny.
- Testy e2e (Playwright) używają zamockowanego API; pełny test integracyjny z działającym stosem wymaga uruchomienia
  backendu z tego repozytorium.
- Nazwa akcji, hasło i logo są placeholderami (`AED_CAMPAIGN_NAME`, `AED_CAMPAIGN_SLOGAN`, `AED_CAMPAIGN_LOGO_URL`) –
  przygotowuje je zespół.
