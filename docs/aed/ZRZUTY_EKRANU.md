# Zrzuty ekranu do prezentacji

Zrzuty robi automatycznie skrypt Playwright (`frontend_latest/e2e/aed/aed.spec.ts`), który przy okazji sprawdza
responsywność (1440 px i 360 px), obsługę klawiaturą i główne ścieżki. API AED jest zamockowane fikcyjnymi danymi
(`frontend_latest/e2e/aed/api-mocks.ts` – te same fikcyjne podmioty co w `aed_demo_data`), więc backend nie jest potrzebny.

```bash
cd frontend_latest
npx playwright install chromium   # jednorazowo
npm run e2e:aed                   # uruchamia ng serve na :4300 i zapisuje PNG do docs/aed/screenshots/
```

| # | Plik | Ekran | URL | Stan danych / kroki |
|---|---|---|---|---|
| 1 | `screenshots/01_strona_akcji_1440.png` | Strona akcji | `/pl/aed` | 1440 px; nazwa „Misja AED”, hasło „Dane na ratunek” (placeholdery z `AED_CAMPAIGN_*`), liczniki: 9 AED, 3 dysponentów, 88,9% z datą ważności elektrod |
| 2 | `screenshots/02_mapa_desktop_1440.png` | Mapa i 5 najbliższych AED – komputer | `/pl/aed/mapa` | 1440 px; zgoda na lokalizację (dworzec w Otwocku, 52.105, 21.26), kliknięte „Moja lokalizacja”; lista obok mapy: odległość, godziny, „otwarte teraz”, gotowość (Gotowy / Wymaga uwagi) |
| 3 | `screenshots/03_mapa_szczegoly_aed_1440.png` | Szczegóły AED | `/pl/aed/mapa` | jak #2 + „Szczegóły” przy „Dworzec Testowy Otwock”: adres, godziny, statusy, daty, 2 źródła (JST + OSM), „Nawiguj”, „Zgłoś problem z tym AED” |
| 4 | `screenshots/04_mapa_telefon_360.png` | Mapa – telefon | `/pl/aed/mapa` | 360 px; jak #2; lista pod mapą, baner „najpierw dzwoń 112” z przyciskiem `tel:112` |
| 5 | `screenshots/05_kreator_krok1_szablon_1440.png` | Kreator dysponenta – szablon i opis pól | `/pl/aed/udostepnij` | 1440 px; krok 1: przyciski szablonów XLSX/CSV, zasady pliku, tabela 29 pól ze schematu |
| 6 | `screenshots/06_kreator_raport_bledow_1440.png` | Kreator – raport z błędami | `/pl/aed/udostepnij` | krok 2: wgrany `aed_bledy.csv` → krok 3: „Plik nie jest zgodny”, 2 błędy (kolumna zakazana `kod_szafki`, powtórzony `id_aed`) i 1 ostrzeżenie (godziny), filtr i eksport CSV |
| 7 | `screenshots/07_kreator_zgodny_1440.png` | Kreator – plik zgodny | `/pl/aed/udostepnij` | wgrany poprawiony plik → „Plik jest zgodny ze standardem AED v1”, przejście do instrukcji publikacji |

## Ekrany robione ręcznie (wymagają działającego backendu z `AED_ENABLED=True`)

Przygotowanie: `python manage.py aed_demo_data` (patrz `README_AED.md`).

| # | Ekran | URL | Stan danych |
|---|---|---|---|
| 8 | Strona zasobu z odznaką „Standard AED v1 – zgodny ze standardem” | `/pl/dataset/<id>/resource/<id>` zasobu „AED – Urząd Miasta Testowego (fikcyjny) (standard AED v1)” | po `aed_demo_data`; odznaka w liście cech zasobu z linkiem „Raport walidacji” |
| 9 | Strona zbioru krajowego „Defibrylatory AED w Polsce – zbiór krajowy” | `/pl/dataset/<id>` | 3 zasoby: `aed_krajowy.csv`, `aed_krajowy.geojson`, `aed_powiazania_zrodel.csv`; kategoria Zdrowie, CC BY 4.0, aktualizacja codzienna |
| 10 | Panel dostawcy – zasób z polem „Standard danych” i zakładką „AED v1 standard” z raportem | `https://admin.mcod.local/resources/resource/<id>/change/` | zasób dostawcy OSM (1 ostrzeżenie: godziny `sunrise-sunset`) |
| 11 | Plik konkursowy | `docs/aed/wzorcowy_zakres_danych_AED_v1.xlsx` | arkusze `dane`, `opis_pol`, `slowniki`, `zasady_pliku` (otworzyć w Excelu/LibreOffice) |
| 12 | Odpowiedź API `nearest` | `https://api.mcod.local/1.4/aed/nearest?lat=52.105&lon=21.26&limit=5&max_km=2` | JSON z `odleglosc_m`, `gotowosc`, `otwarte_teraz` |
