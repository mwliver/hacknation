import { Page, Route } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Mocked AED API with FICTIONAL data (the same fictional providers as backend fixtures:
 * mcod/aed/tests/fixtures/providers). Other portal API calls get empty JSON:API responses.
 */

export const OTWOCK_STATION = { latitude: 52.105, longitude: 21.26 };

const SCHEMA = JSON.parse(fs.readFileSync(path.join(__dirname, '../../../docs/aed/aed_v1.json'), 'utf8'));

const base = {
  zrodlo_danych: 'JST',
  data_aktualizacji: '2026-10-15',
  status_weryfikacji: 'ZWERYFIKOWANY',
  kod_pocztowy: '05-400',
  wewnatrz_budynku: true,
  dostep_publiczny: true,
  wymaga_kodu_lub_klucza: false,
  status_urzadzenia: 'SPRAWNY',
  data_ostatniej_kontroli: '2026-10-01',
  data_waznosci_elektrod: '2028-06-30',
  data_waznosci_baterii: '2029-06-30',
  pietro: null,
  liczba_zrodel: 1,
  otwarte_teraz: true,
  gotowosc: 'GOTOWY',
  odleglosc_m: null,
  zrodla: [],
};

export const RECORDS = [
  {
    ...base,
    id_aed_krajowe: '11111111-1111-4111-8111-111111111111',
    dysponent: 'Urząd Miasta Testowego (fikcyjny)',
    nazwa_obiektu: 'Dworzec Testowy Otwock',
    miejscowosc: 'Otwock',
    ulica: 'ul. Kolejowa Testowa',
    nr_budynku: '1',
    szerokosc_geograficzna: 52.105,
    dlugosc_geograficzna: 21.26,
    opis_lokalizacji: 'hol główny, przy kasach',
    godziny_dostepnosci: '24/7',
    liczba_zrodel: 2,
    zrodla: [
      {
        dysponent: 'Urząd Miasta Testowego (fikcyjny)',
        zrodlo_danych: 'JST',
        zrodlo_id: '',
        id_aed: 'OTW-001',
        zasob_id: 101,
        zbior_id: 11,
        zrodlo_wygrywajace: true,
      },
      {
        dysponent: 'Fundacja Mapa AED (fikcyjna)',
        zrodlo_danych: 'OSM',
        zrodlo_id: 'node/200000001',
        id_aed: 'OSM-OTW-1',
        zasob_id: 103,
        zbior_id: 13,
        zrodlo_wygrywajace: false,
      },
    ],
  },
  {
    ...base,
    id_aed_krajowe: '22222222-2222-4222-8222-222222222222',
    dysponent: 'Urząd Miasta Testowego (fikcyjny)',
    nazwa_obiektu: 'Urząd Miasta Testowego',
    miejscowosc: 'Otwock',
    ulica: 'ul. Urzędowa Testowa',
    nr_budynku: '5',
    szerokosc_geograficzna: 52.112,
    dlugosc_geograficzna: 21.255,
    opis_lokalizacji: 'parter, przy biurze podawczym',
    godziny_dostepnosci: 'Mo-Fr 08:00-16:00; PH off',
  },
  {
    ...base,
    id_aed_krajowe: '33333333-3333-4333-8333-333333333333',
    dysponent: 'Urząd Miasta Testowego (fikcyjny)',
    nazwa_obiektu: 'Basen Miejski Testowy',
    miejscowosc: 'Otwock',
    ulica: 'ul. Sportowa Testowa',
    nr_budynku: '3',
    szerokosc_geograficzna: 52.098,
    dlugosc_geograficzna: 21.273,
    opis_lokalizacji: 'recepcja',
    godziny_dostepnosci: 'Mo-Su 06:00-22:00',
    data_waznosci_elektrod: '2026-12-10',
    gotowosc: 'WYMAGA_UWAGI',
  },
  {
    ...base,
    id_aed_krajowe: '44444444-4444-4444-8444-444444444444',
    dysponent: 'Przychodnia Testowa Sp. z o.o. (fikcyjna)',
    zrodlo_danych: 'WLASCICIEL',
    nazwa_obiektu: 'Przychodnia Testowa nr 1',
    miejscowosc: 'Warszawa',
    ulica: 'ul. Przykładowa',
    nr_budynku: '10A',
    kod_pocztowy: '00-001',
    szerokosc_geograficzna: 52.22975,
    dlugosc_geograficzna: 21.0123,
    opis_lokalizacji: 'parter, przy rejestracji',
    godziny_dostepnosci: 'Mo-Fr 08:00-18:00; Sa 09:00-13:00; PH off',
    dostep_publiczny: false,
    wymaga_kodu_lub_klucza: true,
  },
  {
    ...base,
    id_aed_krajowe: '55555555-5555-4555-8555-555555555555',
    dysponent: 'Fundacja Mapa AED (fikcyjna)',
    zrodlo_danych: 'OSM',
    nazwa_obiektu: 'Hala Sportowa Testowa',
    miejscowosc: 'Kraków',
    ulica: null,
    nr_budynku: null,
    kod_pocztowy: null,
    szerokosc_geograficzna: 50.0647,
    dlugosc_geograficzna: 19.945,
    opis_lokalizacji: 'ściana zewnętrzna przy wejściu',
    godziny_dostepnosci: '24/7',
    wewnatrz_budynku: false,
    status_weryfikacji: 'NIEZWERYFIKOWANY',
    data_ostatniej_kontroli: null,
    gotowosc: 'NIEZNANY',
  },
];

const OTWOCK_DISTANCES = [4, 790, 1120];

export const VALIDATION_ERRORS_REPORT = {
  standard: 'AED_V1',
  zgodny: false,
  liczba_wierszy: 3,
  liczba_bledow: 2,
  liczba_ostrzezen: 1,
  data_walidacji: null,
  zasob_id: null,
  problemy: [
    {
      wiersz: 1,
      kolumna: 'kod_szafki',
      kod: 'FORBIDDEN_COLUMN',
      poziom: 'ERROR',
      komunikat_pl:
        'Kolumna „kod_szafki” jest zakazana. Otwarte dane i RODO: plik nie może zawierać kodów do szafek ani danych osobowych. Kod do szafki podaje dyspozytor.',
      komunikat_en: 'Column "kod_szafki" is forbidden. The cabinet code is provided by the dispatcher.',
    },
    {
      wiersz: 3,
      kolumna: 'id_aed',
      kod: 'DUPLICATE_ID',
      poziom: 'ERROR',
      komunikat_pl: 'Identyfikator „OTW-0001” powtarza się w pliku (pierwszy raz w wierszu 2).',
      komunikat_en: 'Identifier "OTW-0001" is duplicated in the file (first seen in row 2).',
    },
    {
      wiersz: 4,
      kolumna: 'godziny_dostepnosci',
      kod: 'OPENING_HOURS_UNSUPPORTED',
      poziom: 'WARNING',
      komunikat_pl: 'Godziny „sunrise-sunset” nie są w obsługiwanej składni opening_hours.',
      komunikat_en: 'Hours "sunrise-sunset" are not in the supported opening_hours syntax.',
    },
  ],
};

export const VALIDATION_OK_REPORT = {
  ...VALIDATION_ERRORS_REPORT,
  zgodny: true,
  liczba_bledow: 0,
  liczba_ostrzezen: 0,
  problemy: [],
};

const json = (route: Route, body: unknown, status = 200) =>
  route.fulfill({ status, contentType: 'application/vnd.api+json', body: JSON.stringify(body) });

const list = (items: object[], extraMeta = {}) => ({
  data: items.map((attributes: { id_aed_krajowe: string }) => ({
    id: attributes.id_aed_krajowe,
    type: 'aed',
    attributes,
  })),
  meta: { count: items.length, ...extraMeta },
  links: {},
});

export interface MockOptions {
  /** false = backend with AED_ENABLED=False (AED routes return 404) */
  aedEnabled?: boolean;
}
// POST /aed/validate returns the error report for files whose name contains "bledy", otherwise a compliant one.

export async function mockApi(page: Page, options: MockOptions = {}) {
  const enabled = options.aedEnabled ?? true;

  // returning visitor: skip the first-visit GDPR (RODO) modal of the portal
  await page.addInitScript(() => window.localStorage.setItem('OD_isAcquintedWithRodo', 'true'));

  await page.route('https://flags.dane.gov.pl/**', (route) => route.fulfill({ json: { features: [] } }));
  await page.route('**/flags/**', (route) => route.fulfill({ json: { features: [] } }));
  await page.route('**/cms/**', (route) => route.fulfill({ status: 404, json: {} }));
  await page.route('https://nominatim.openstreetmap.org/**', (route) =>
    route.fulfill({
      json: {
        features: [
          {
            type: 'Feature',
            bbox: [21.25, 52.1, 21.27, 52.11],
            geometry: { type: 'Point', coordinates: [21.2601, 52.1052] },
            properties: { display_name: 'Kolejowa Testowa, Otwock, województwo mazowieckie, Polska' },
          },
        ],
      },
    }),
  );

  // generic portal API: empty responses
  await page.route(/\/api\/.*/, async (route) => {
    const url = new URL(route.request().url());
    const p = url.pathname.replace(/^\/api(\/1\.\d)?/, '');
    if (!p.startsWith('/aed')) {
      return json(route, { data: [], meta: { count: 0, aggregations: {} }, links: {} });
    }
    if (!enabled) {
      return json(route, { errors: [{ status: '404' }] }, 404);
    }
    if (p === '/aed/config') {
      return json(route, {
        data: {
          id: 'aed',
          type: 'aed_config',
          attributes: {
            enabled: true,
            campaign_name: 'Misja AED',
            campaign_slogan: 'Dane na ratunek',
            campaign_logo_url: '',
            standard: 'AED_V1',
          },
        },
      });
    }
    if (p === '/aed/stats') {
      return json(route, {
        data: {
          id: 'aed',
          type: 'aed_stats',
          attributes: {
            liczba_aed: 9,
            liczba_dysponentow: 3,
            liczba_zrodel_danych: 3,
            odsetek_z_data_waznosci_elektrod: 88.9,
            gotowosc: { GOTOWY: 3, WYMAGA_UWAGI: 1, NIEZNANY: 4, NIEGOTOWY: 1 },
            data_aktualizacji: '2026-11-21T03:30:00+01:00',
          },
        },
      });
    }
    if (p === '/aed/schema') {
      return route.fulfill({ json: SCHEMA });
    }
    if (p === '/aed/nearest') {
      const nearest = RECORDS.slice(0, 3).map((r, i) => ({ ...r, odleglosc_m: OTWOCK_DISTANCES[i] }));
      return json(route, list(nearest));
    }
    if (p === '/aed/validate') {
      const body = route.request().postDataBuffer()?.toString('latin1') ?? '';
      const report = body.includes('bledy') ? VALIDATION_ERRORS_REPORT : VALIDATION_OK_REPORT;
      return json(route, { data: { id: 'validation', type: 'aed_validation_report', attributes: report } });
    }
    if (p.startsWith('/aed/template')) {
      return route.fulfill({
        contentType: 'text/csv',
        body: SCHEMA.fields.map((f: { name: string }) => f.name).join(',') + '\n',
      });
    }
    const detail = RECORDS.find((r) => p === `/aed/${r.id_aed_krajowe}`);
    if (detail) {
      return json(route, { data: { id: detail.id_aed_krajowe, type: 'aed', attributes: detail } });
    }
    if (p === '/aed') {
      const zoomedOut = Number(url.searchParams.get('precyzja') ?? 9) <= 3;
      if (zoomedOut) {
        return json(route, {
          data: [],
          meta: {
            count: 250,
            aggregations: {
              klastry: [
                { geohash: 'u3q', liczba: 120, lat: 52.2, lon: 21.05 },
                { geohash: 'u2y', liczba: 80, lat: 50.06, lon: 19.94 },
                { geohash: 'u3m', liczba: 50, lat: 52.1, lon: 21.26 },
              ],
            },
          },
          links: {},
        });
      }
      const [minLon, minLat, maxLon, maxLat] = (url.searchParams.get('bbox') ?? '-180,-90,180,90')
        .split(',')
        .map(Number);
      const inView = RECORDS.filter(
        (r) =>
          r.dlugosc_geograficzna >= minLon &&
          r.dlugosc_geograficzna <= maxLon &&
          r.szerokosc_geograficzna >= minLat &&
          r.szerokosc_geograficzna <= maxLat,
      );
      return json(route, list(inView, { aggregations: { klastry: [] } }));
    }
    return json(route, { errors: [{ status: '404' }] }, 404);
  });
}
