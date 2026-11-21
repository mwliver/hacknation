import { AedFilters, AedIssue, AedReadiness, AedRecord } from '@app/pages/aed/services/aed.models';

export const DEFAULT_AED_FILTERS: AedFilters = { openNow: false, publicAccess: false, readiness: null };

/**
 * Converts user filters to API query params (only active filters are sent).
 */
export function filtersToParams(filters: AedFilters): Record<string, string> {
  const params: Record<string, string> = {};
  if (filters.openNow) {
    params['otwarte_teraz'] = 'true';
  }
  if (filters.publicAccess) {
    params['dostep_publiczny'] = 'true';
  }
  if (filters.readiness) {
    params['gotowosc'] = filters.readiness;
  }
  return params;
}

/**
 * The same filters applied on already loaded records, with the same semantics as the API:
 * "open now" keeps only AEDs whose opening hours say they are open (unknown hours are hidden by this filter).
 */
export function applyFilters(records: AedRecord[], filters: AedFilters): AedRecord[] {
  return records.filter(
    (r) =>
      (!filters.openNow || r.otwarte_teraz === true) &&
      (!filters.publicAccess || r.dostep_publiczny) &&
      (!filters.readiness || r.gotowosc === filters.readiness),
  );
}

export function activeFiltersCount(filters: AedFilters): number {
  return [filters.openNow, filters.publicAccess, !!filters.readiness].filter(Boolean).length;
}

/** Leaflet zoom -> geohash precision used by the backend cluster aggregation. */
export function zoomToGeohashPrecision(zoom: number): number {
  if (zoom <= 5) {
    return 2;
  }
  if (zoom <= 7) {
    return 3;
  }
  if (zoom <= 9) {
    return 4;
  }
  if (zoom <= 11) {
    return 5;
  }
  if (zoom <= 13) {
    return 6;
  }
  return 7;
}

export function formatDistance(meters: number | null, lang: string): string {
  if (meters === null || meters === undefined) {
    return '';
  }
  if (meters < 1000) {
    return `${Math.round(meters)} m`;
  }
  const km = (meters / 1000).toLocaleString(lang === 'en' ? 'en-GB' : 'pl-PL', { maximumFractionDigits: 1 });
  return `${km} km`;
}

/** Readiness -> CSS modifier and icon (readiness is always shown with text, colour is only an extra cue). */
export const READINESS_PRESENTATION: Record<AedReadiness, { css: string; icon: string }> = {
  GOTOWY: { css: 'aed-readiness--ready', icon: '✔' },
  WYMAGA_UWAGI: { css: 'aed-readiness--attention', icon: '!' },
  NIEZNANY: { css: 'aed-readiness--unknown', icon: '?' },
  NIEGOTOWY: { css: 'aed-readiness--not-ready', icon: '✖' },
};

export function filterIssues(issues: AedIssue[], level: 'ALL' | 'ERROR' | 'WARNING'): AedIssue[] {
  return level === 'ALL' ? issues : issues.filter((i) => i.poziom === level);
}

/** CSV export of a validation report (UTF-8 with BOM so that Excel opens Polish characters correctly). */
export function issuesToCsv(issues: AedIssue[], lang: string): string {
  const quote = (value: unknown) => {
    const text = value === null || value === undefined ? '' : String(value);
    return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  };
  const header = ['wiersz', 'kolumna', 'kod', 'poziom', 'komunikat'];
  const rows = issues.map((i) =>
    [i.wiersz, i.kolumna, i.kod, i.poziom, lang === 'en' ? i.komunikat_en : i.komunikat_pl].map(quote).join(','),
  );
  return '﻿' + [header.join(','), ...rows].join('\n') + '\n';
}

/** Link opening navigation in the phone's map application (geo: URI) with a web fallback. */
export function navigationUrl(
  record: Pick<AedRecord, 'szerokosc_geograficzna' | 'dlugosc_geograficzna'>,
  userAgent: string,
) {
  const lat = record.szerokosc_geograficzna;
  const lon = record.dlugosc_geograficzna;
  if (/iPhone|iPad|iPod|Macintosh/i.test(userAgent)) {
    return `https://maps.apple.com/?daddr=${lat},${lon}&dirflg=w`;
  }
  if (/Android/i.test(userAgent)) {
    return `geo:${lat},${lon}?q=${lat},${lon}`;
  }
  return `https://www.openstreetmap.org/directions?engine=fossgis_osrm_foot&route=%3B${lat}%2C${lon}#map=17/${lat}/${lon}`;
}
