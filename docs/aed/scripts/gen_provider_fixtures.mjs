// Generates 3 fictional AED v1 provider files with deliberate duplicates (Otwock, Warszawa, Kraków).
// Used by tests of the national dataset and by `manage.py aed_demo_data`. All data is fictional.
// Run: node docs/aed/scripts/gen_provider_fixtures.mjs
//
// Expected aggregation result: 13 rows -> 10 national records
//   OTW-001 (JST)        ~ OSM-OTW-1 (OSM, 14 m, Otwock, no street in OSM)   -> 1 record, JST wins
//   WAW-JST-1 (JST)      ~ PRZ-001 (WLASCICIEL, 9 m, same street)            -> 1 record, WLASCICIEL wins
//   PRZ-OSM (OSM node/200000002) ~ OSM-WAW-2 (OSM node/200000002, 40 m)      -> 1 record (same source id)
//   OSM-KRK-1 / OSM-KRK-2 are 40 m apart in one file                        -> 2 records (not duplicates)
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Z]:)/, '$1')), '../../..');
const out = path.join(root, 'backend_latest/mcod/aed/tests/fixtures/providers');
fs.mkdirSync(out, { recursive: true });
const header = fs.readFileSync(path.join(root, 'docs/aed/wzorcowy_zakres_danych_AED_v1.csv'), 'utf8').split('\n')[0].split(',');
const esc = (v) => (/[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v);

const base = {
  data_aktualizacji: '2026-10-15', status_weryfikacji: 'ZWERYFIKOWANY', wewnatrz_budynku: 'true',
  godziny_dostepnosci: '24/7', dostep_publiczny: 'true', wymaga_kodu_lub_klucza: 'false', status_urzadzenia: 'SPRAWNY',
  data_ostatniej_kontroli: '2026-10-01', data_waznosci_elektrod: '2028-06-30', data_waznosci_baterii: '2029-06-30',
};

const files = {
  'dostawca_jst_otwock.csv': [
    { id_aed: 'OTW-001', nazwa_obiektu: 'Dworzec Testowy Otwock', miejscowosc: 'Otwock', ulica: 'ul. Kolejowa Testowa', nr_budynku: '1',
      kod_pocztowy: '05-400', szerokosc_geograficzna: '52.10500', dlugosc_geograficzna: '21.26000', opis_lokalizacji: 'hol główny, przy kasach',
      kod_teryt_gminy: '1417011' },
    { id_aed: 'OTW-002', nazwa_obiektu: 'Urząd Miasta Testowego', miejscowosc: 'Otwock', ulica: 'ul. Urzędowa Testowa', nr_budynku: '5',
      kod_pocztowy: '05-400', szerokosc_geograficzna: '52.11200', dlugosc_geograficzna: '21.25500', opis_lokalizacji: 'parter, przy biurze podawczym',
      godziny_dostepnosci: 'Mo-Fr 08:00-16:00; PH off', kod_teryt_gminy: '1417011' },
    { id_aed: 'OTW-003', nazwa_obiektu: 'Basen Miejski Testowy', miejscowosc: 'Otwock', ulica: 'ul. Sportowa Testowa', nr_budynku: '3',
      kod_pocztowy: '05-400', szerokosc_geograficzna: '52.09800', dlugosc_geograficzna: '21.27300', opis_lokalizacji: 'recepcja',
      godziny_dostepnosci: 'Mo-Su 06:00-22:00', data_waznosci_elektrod: '2026-12-10', kod_teryt_gminy: '1417011' },
    { id_aed: 'WAW-JST-1', nazwa_obiektu: 'Przychodnia Testowa nr 1', miejscowosc: 'Warszawa', ulica: 'ul. Przykładowa', nr_budynku: '10A',
      kod_pocztowy: '00-001', szerokosc_geograficzna: '52.22970', dlugosc_geograficzna: '21.01220', opis_lokalizacji: 'wejście główne',
      data_aktualizacji: '2026-11-01' },
  ].map((r) => ({ ...base, dysponent: 'Urząd Miasta Testowego (fikcyjny)', zrodlo_danych: 'JST', zrodlo_id: '', ...r })),
  'dostawca_wlasciciel_warszawa.csv': [
    { id_aed: 'PRZ-001', nazwa_obiektu: 'Przychodnia Testowa nr 1', miejscowosc: 'Warszawa', ulica: 'Przykładowa', nr_budynku: '10A',
      kod_pocztowy: '00001', szerokosc_geograficzna: '52.22975', dlugosc_geograficzna: '21.01230', opis_lokalizacji: 'parter, przy rejestracji',
      godziny_dostepnosci: 'Mo-Fr 08:00-18:00; Sa 09:00-13:00; PH off', dostep_publiczny: 'false', wymaga_kodu_lub_klucza: 'true',
      data_aktualizacji: '2026-09-20', telefon_kontaktowy: '+48000000001' },
    { id_aed: 'PRZ-002', nazwa_obiektu: 'Przychodnia Testowa nr 2', miejscowosc: 'Warszawa', ulica: 'ul. Wzorcowa', nr_budynku: '2',
      kod_pocztowy: '00-002', szerokosc_geograficzna: '52.24000', dlugosc_geograficzna: '21.00000', opis_lokalizacji: 'I piętro, poczekalnia',
      status_urzadzenia: 'CZASOWO_NIEDOSTEPNY', pietro: '1' },
    { id_aed: 'PRZ-003', nazwa_obiektu: 'Biurowiec Testowy', miejscowosc: 'Warszawa', ulica: 'ul. Biurowa Testowa', nr_budynku: '7',
      kod_pocztowy: '00-003', szerokosc_geograficzna: '52.23200', dlugosc_geograficzna: '21.02000', opis_lokalizacji: 'recepcja w lobby',
      status_urzadzenia: 'NIESPRAWNY' },
    { id_aed: 'PRZ-OSM', nazwa_obiektu: 'Park Testowy – pawilon', miejscowosc: 'Warszawa', ulica: '', nr_budynku: '',
      kod_pocztowy: '', szerokosc_geograficzna: '52.21000', dlugosc_geograficzna: '21.03000', opis_lokalizacji: 'ściana pawilonu przy wejściu',
      zrodlo_danych: 'OSM', zrodlo_id: 'node/200000002', wewnatrz_budynku: 'false', data_ostatniej_kontroli: '' },
  ].map((r) => ({ ...base, dysponent: 'Przychodnia Testowa Sp. z o.o. (fikcyjna)', zrodlo_danych: 'WLASCICIEL', zrodlo_id: '', ...r })),
  'dostawca_osm_mapa.csv': [
    { id_aed: 'OSM-OTW-1', nazwa_obiektu: 'Dworzec PKP Otwock', miejscowosc: 'Otwock', ulica: '', nr_budynku: '',
      kod_pocztowy: '', szerokosc_geograficzna: '52.10510', dlugosc_geograficzna: '21.26010', opis_lokalizacji: 'hala dworca',
      zrodlo_id: 'node/200000001', data_waznosci_elektrod: '', data_waznosci_baterii: '', producent: 'Producent Testowy' },
    { id_aed: 'OSM-WAW-2', nazwa_obiektu: 'Pawilon w parku', miejscowosc: 'Warszawa', ulica: '', nr_budynku: '',
      kod_pocztowy: '', szerokosc_geograficzna: '52.21036', dlugosc_geograficzna: '21.03000', opis_lokalizacji: 'przy wejściu do pawilonu',
      zrodlo_id: 'node/200000002', wewnatrz_budynku: 'false', data_aktualizacji: '2026-11-10' },
    { id_aed: 'OSM-KRK-1', nazwa_obiektu: 'Hala Sportowa Testowa', miejscowosc: 'Kraków', ulica: '', nr_budynku: '',
      kod_pocztowy: '', szerokosc_geograficzna: '50.06470', dlugosc_geograficzna: '19.94500', opis_lokalizacji: 'ściana zewnętrzna przy wejściu',
      zrodlo_id: 'node/200000003', wewnatrz_budynku: 'false' },
    { id_aed: 'OSM-KRK-2', nazwa_obiektu: 'Sklep Testowy', miejscowosc: 'Kraków', ulica: '', nr_budynku: '',
      kod_pocztowy: '', szerokosc_geograficzna: '50.06506', dlugosc_geograficzna: '19.94500', opis_lokalizacji: 'przy kasach',
      zrodlo_id: 'node/200000004', godziny_dostepnosci: 'Mo-Sa 07:00-21:00' },
    { id_aed: 'OSM-KRK-3', nazwa_obiektu: 'Rynek Testowy – punkt informacji', miejscowosc: 'Kraków', ulica: '', nr_budynku: '',
      kod_pocztowy: '', szerokosc_geograficzna: '50.06170', dlugosc_geograficzna: '19.93730', opis_lokalizacji: 'okienko informacji turystycznej',
      zrodlo_id: 'node/200000005', godziny_dostepnosci: 'sunrise-sunset' },
  ].map((r) => ({ ...base, dysponent: 'Fundacja Mapa AED (fikcyjna)', zrodlo_danych: 'OSM', status_weryfikacji: 'NIEZWERYFIKOWANY',
    data_ostatniej_kontroli: '', ...r })),
};

for (const [name, rows] of Object.entries(files)) {
  const lines = [header.join(','), ...rows.map((r) => header.map((h) => esc(r[h] ?? '')).join(','))];
  fs.writeFileSync(path.join(out, name), lines.join('\n') + '\n');
}
console.log(`${Object.keys(files).length} provider files -> ${out}`);
