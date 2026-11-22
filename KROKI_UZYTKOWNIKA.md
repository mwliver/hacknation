# Kroki użytkownika

> W nagłym zatrzymaniu krążenia **najpierw dzwoń 112**. Ten komunikat jest stale widoczny na wszystkich stronach AED.

## 1. Obywatel – „znajdź najbliższy AED” (telefon)

1. Wchodzi na `dane.gov.pl/pl/aed` i wybiera **„Znajdź najbliższy AED”** (lub od razu `/pl/aed/mapa`).
2. Naciska **„Moja lokalizacja”** i zgadza się na udostępnienie położenia.
   - Jeśli odmówi albo telefon nie poda położenia, zobaczy komunikat i kursor przejdzie do pola
     **„Adres lub miejscowość”** – wpisuje np. „Otwock, Kolejowa” i naciska „Szukaj”.
3. Pod mapą widzi **5 najbliższych AED** (do 5 km): odległość, nazwę obiektu, opis miejsca („hol główny, przy kasach”),
   godziny, informację **„Otwarte teraz / Teraz zamknięte / Godziny nieznane”** i **gotowość** (tekst + ikona + kolor:
   Gotowy, Wymaga uwagi, Gotowość nieznana, Niegotowy).
4. Opcjonalnie zawęża listę filtrami: **tylko otwarte teraz**, **tylko dostęp publiczny**, **gotowość**.
5. Naciska **„Szczegóły”** przy wybranym AED: pełny adres, piętro, wewnątrz/na zewnątrz, dostęp (np. „Szafka zamknięta –
   kod poda dyspozytor 112”), status urządzenia, daty kontroli i ważności, źródła danych.
6. Naciska **„Nawiguj”** – otwiera się aplikacja z mapą w telefonie (Android: `geo:`, iOS: Apple Maps, komputer: OpenStreetMap).
7. Jeśli na miejscu coś się nie zgadza (brak urządzenia, inna lokalizacja), wybiera **„Zgłoś problem z tym AED”** –
   istniejący formularz uwag portalu kieruje zgłoszenie do zasobu dysponenta, który opublikował dane.

Bez mapy: wszystkie AED z widoku mapy są też na liście tekstowej „AED w widoku mapy” – cała ścieżka działa z klawiatury
i czytnika ekranu.

## 2. Dyspozytor medyczny / służby ratunkowe

1. Korzysta z API: `GET https://api.dane.gov.pl/1.4/aed/nearest?lat=52.105&lon=21.26&limit=5&max_km=2`
   (lub z mapy `/pl/aed/mapa`).
2. Odpowiedź zawiera odległość, opis lokalizacji zrozumiały dla dyspozytora, godziny, `otwarte_teraz`, `gotowosc`,
   `dostep_publiczny` i `wymaga_kodu_lub_klucza` (**tylko informacja** – kody do szafek nie są publikowane;
   dyspozytor ma je w swoich systemach).
3. Domyślnie pomijane są AED `CZASOWO_NIEDOSTEPNY` (`include_unavailable=true` pokaże je), a `NIESPRAWNY` nie są pokazywane nigdy.
4. Szczegóły i pochodzenie rekordu: `GET /aed/{id_aed_krajowe}` (lista źródeł i dysponentów).
5. Cały zbiór do własnych systemów: zasoby `aed_krajowy.csv` / `aed_krajowy.geojson` zbioru
   „Defibrylatory AED w Polsce – zbiór krajowy” (aktualizowany codziennie).

## 3. Dysponent danych (właściciel AED, samorząd, operator aplikacji)

1. Wchodzi na `/pl/aed/udostepnij` (**krok 1**), pobiera **szablon XLSX lub CSV** i czyta opis pól
   (generowany ze schematu AED v1: wymagalność, format, słowniki, przykłady, kolumny zakazane).
2. Uzupełnia plik: jeden wiersz = jeden AED; daty `RRRR-MM-DD`, `true`/`false`, kropka dziesiętna, współrzędne WGS84;
   **nie wpisuje kodów do szafek ani danych osobowych**.
3. **Krok 2**: wgrywa plik i naciska „Sprawdź plik”. Plik jest tylko sprawdzany – nic nie jest publikowane ani zapisywane.
4. **Krok 3**: widzi raport – liczbę wierszy, błędów i ostrzeżeń oraz tabelę problemów (wiersz, kolumna, opis);
   może filtrować błędy/ostrzeżenia i pobrać raport jako CSV. Poprawia plik i sprawdza ponownie, aż zobaczy
   **„Plik jest zgodny ze standardem AED v1”**.
5. **Krok 4**: w panelu dostawcy dane.gov.pl dodaje zbiór i zasób z plikiem, w polu **„Standard danych”** wybiera
   **„AED v1”** i zapisuje.
6. Portal automatycznie sprawdza plik w kolejce walidacji zasobów. W panelu (zakładka **„AED v1 standard”**) i na stronie
   zasobu widać odznakę **„Standard AED v1 – zgodny / N błędów”** z linkiem do raportu. Zbiór dostaje tag „AED”.
7. Zgodny zasób trafia do **zbioru krajowego** przy najbliższej aktualizacji (codziennie 03:30). Duplikaty z innymi
   źródłami są łączone (priorytet: właściciel > JST > aplikacja > inne > OSM), a powiązanie rekordu krajowego
   z zasobem dysponenta jest widoczne w zasobie `aed_powiazania_zrodel.csv` i w API.
8. Aktualizuje dane, wgrywając nową wersję pliku do tego samego zasobu – identyfikatory krajowe rekordów zostają.
