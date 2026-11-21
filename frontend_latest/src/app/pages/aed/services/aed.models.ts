/**
 * Models of the AED API (backend: mcod/aed). Field names follow the AED v1 data standard (Polish names).
 */

export type AedReadiness = 'GOTOWY' | 'WYMAGA_UWAGI' | 'NIEZNANY' | 'NIEGOTOWY';
export type AedDeviceStatus = 'SPRAWNY' | 'NIESPRAWNY' | 'CZASOWO_NIEDOSTEPNY' | 'NIEZNANY';

export const AED_READINESS_VALUES: AedReadiness[] = ['GOTOWY', 'WYMAGA_UWAGI', 'NIEZNANY', 'NIEGOTOWY'];

export interface AedSource {
  dysponent: string;
  zrodlo_danych: string;
  zrodlo_id: string;
  id_aed: string;
  zasob_id: number | null;
  zbior_id: number | null;
  zrodlo_wygrywajace: boolean;
}

export interface AedRecord {
  id_aed_krajowe: string;
  dysponent: string;
  zrodlo_danych: string;
  data_aktualizacji: string;
  status_weryfikacji: string;
  nazwa_obiektu: string;
  miejscowosc: string;
  ulica: string | null;
  nr_budynku: string | null;
  kod_pocztowy: string | null;
  szerokosc_geograficzna: number;
  dlugosc_geograficzna: number;
  wewnatrz_budynku: boolean;
  opis_lokalizacji: string;
  godziny_dostepnosci: string;
  dostep_publiczny: boolean;
  wymaga_kodu_lub_klucza: boolean;
  status_urzadzenia: AedDeviceStatus;
  data_ostatniej_kontroli: string | null;
  data_waznosci_elektrod: string | null;
  data_waznosci_baterii: string | null;
  pietro?: number | null;
  liczba_zrodel: number;
  gotowosc: AedReadiness;
  otwarte_teraz: boolean | null;
  odleglosc_m: number | null;
  zrodla: AedSource[];
}

export interface AedCluster {
  geohash: string;
  liczba: number;
  lat: number;
  lon: number;
}

export interface AedListResult {
  items: AedRecord[];
  count: number;
  clusters: AedCluster[];
}

export interface AedStats {
  liczba_aed: number;
  liczba_dysponentow: number;
  liczba_zrodel_danych: number;
  odsetek_z_data_waznosci_elektrod: number;
  gotowosc: Partial<Record<AedReadiness, number>>;
  data_aktualizacji: string | null;
}

export interface AedConfig {
  enabled: boolean;
  campaign_name: string;
  campaign_slogan: string;
  campaign_logo_url: string;
  standard: string;
}

export interface AedIssue {
  wiersz: number | null;
  kolumna: string | null;
  kod: string;
  poziom: 'ERROR' | 'WARNING';
  komunikat_pl: string;
  komunikat_en: string;
}

export interface AedValidationReport {
  standard: string;
  zgodny: boolean;
  liczba_wierszy: number;
  liczba_bledow: number;
  liczba_ostrzezen: number;
  data_walidacji: string | null;
  zasob_id: number | null;
  problemy: AedIssue[];
}

export interface AedSchemaField {
  name: string;
  type: string;
  'x-aed-presence': 'required' | 'if_known' | 'extended';
  title: { pl: string; en: string };
  description: { pl: string; en: string };
  example?: string;
  constraints?: { enum?: string[]; pattern?: string; minimum?: number; maximum?: number };
}

export interface AedSchema {
  fields: AedSchemaField[];
  'x-aed-forbidden-fields': string[];
  'x-aed-file-rules': { pl: string; en: string }[];
}

/** Map/list filters chosen by the user. */
export interface AedFilters {
  openNow: boolean;
  publicAccess: boolean;
  readiness: AedReadiness | null;
}

export interface AedLocation {
  lat: number;
  lon: number;
  label?: string;
}
