import {
  activeFiltersCount,
  applyFilters,
  DEFAULT_AED_FILTERS,
  filterIssues,
  filtersToParams,
  formatDistance,
  issuesToCsv,
  navigationUrl,
  zoomToGeohashPrecision,
} from '@app/pages/aed/services/aed-filters';
import { AedIssue, AedRecord } from '@app/pages/aed/services/aed.models';

const record = (overrides: Partial<AedRecord>): AedRecord =>
  ({
    id_aed_krajowe: 'x',
    otwarte_teraz: true,
    dostep_publiczny: true,
    gotowosc: 'GOTOWY',
    szerokosc_geograficzna: 52.1,
    dlugosc_geograficzna: 21.2,
    ...overrides,
  }) as AedRecord;

describe('AED filters', () => {
  it('sends only active filters to the API', () => {
    expect(filtersToParams(DEFAULT_AED_FILTERS)).toEqual({});
    expect(filtersToParams({ openNow: true, publicAccess: true, readiness: 'NIEZNANY' })).toEqual({
      otwarte_teraz: 'true',
      dostep_publiczny: 'true',
      gotowosc: 'NIEZNANY',
    });
  });

  it('applies filters on loaded records like the API', () => {
    const records = [
      record({ id_aed_krajowe: 'open' }),
      record({ id_aed_krajowe: 'closed', otwarte_teraz: false }),
      record({ id_aed_krajowe: 'unknown-hours', otwarte_teraz: null }),
      record({ id_aed_krajowe: 'staff', dostep_publiczny: false }),
      record({ id_aed_krajowe: 'attention', gotowosc: 'WYMAGA_UWAGI' }),
    ];
    const ids = (filters) => applyFilters(records, filters).map((r) => r.id_aed_krajowe);

    expect(ids(DEFAULT_AED_FILTERS)).toHaveLength(5);
    expect(ids({ ...DEFAULT_AED_FILTERS, openNow: true })).toEqual(['open', 'staff', 'attention']);
    expect(ids({ ...DEFAULT_AED_FILTERS, publicAccess: true })).not.toContain('staff');
    expect(ids({ ...DEFAULT_AED_FILTERS, readiness: 'WYMAGA_UWAGI' })).toEqual(['attention']);
  });

  it('counts active filters', () => {
    expect(activeFiltersCount(DEFAULT_AED_FILTERS)).toBe(0);
    expect(activeFiltersCount({ openNow: true, publicAccess: false, readiness: 'GOTOWY' })).toBe(2);
  });

  it('maps zoom to geohash precision', () => {
    expect(zoomToGeohashPrecision(5)).toBe(2);
    expect(zoomToGeohashPrecision(8)).toBe(4);
    expect(zoomToGeohashPrecision(16)).toBe(7);
  });

  it('formats distances', () => {
    expect(formatDistance(12.4, 'pl')).toBe('12 m');
    expect(formatDistance(1530, 'pl')).toBe('1,5 km');
    expect(formatDistance(1530, 'en')).toBe('1.5 km');
    expect(formatDistance(null, 'pl')).toBe('');
  });

  it('filters and exports report issues', () => {
    const issues: AedIssue[] = [
      {
        wiersz: 2,
        kolumna: 'id_aed',
        kod: 'DUPLICATE_ID',
        poziom: 'ERROR',
        komunikat_pl: 'Powtórzony, "id"',
        komunikat_en: 'Duplicated',
      },
      { wiersz: 3, kolumna: null, kod: 'STALE_UPDATE', poziom: 'WARNING', komunikat_pl: 'Stare', komunikat_en: 'Old' },
    ];
    expect(filterIssues(issues, 'ERROR').map((i) => i.kod)).toEqual(['DUPLICATE_ID']);
    expect(filterIssues(issues, 'ALL')).toHaveLength(2);
    const csv = issuesToCsv(issues, 'pl');
    expect(csv.startsWith('﻿wiersz,kolumna,kod,poziom,komunikat\n')).toBe(true);
    expect(csv).toContain('2,id_aed,DUPLICATE_ID,ERROR,"Powtórzony, ""id"""');
    expect(issuesToCsv(issues, 'en')).toContain('3,,STALE_UPDATE,WARNING,Old');
  });

  it('builds navigation links for phones and desktop', () => {
    const r = record({});
    expect(navigationUrl(r, 'Mozilla/5.0 (Linux; Android 14)')).toBe('geo:52.1,21.2?q=52.1,21.2');
    expect(navigationUrl(r, 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)')).toContain('maps.apple.com');
    expect(navigationUrl(r, 'Mozilla/5.0 (Windows NT 10.0)')).toContain('openstreetmap.org/directions');
  });
});
