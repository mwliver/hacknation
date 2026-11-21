// Generates CSV fixtures for AED validator tests: one file per rule + manifest.json.
// Base rows = fictional examples from docs/aed/wzorcowy_zakres_danych_AED_v1.csv (generated from the schema).
// Run: node docs/aed/scripts/gen_validation_fixtures.mjs   (tests assume today = 2026-11-21)
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Z]:)/, '$1')), '../../..');
const out = path.join(root, 'backend_latest/mcod/aed/tests/fixtures/validation');
fs.mkdirSync(out, { recursive: true });

const parse = (line) => {
  const cells = []; let cur = ''; let q = false;
  for (const ch of line) {
    if (q) { if (ch === '"') q = false; else cur += ch; }
    else if (ch === '"') q = true; else if (ch === ',') { cells.push(cur); cur = ''; } else cur += ch;
  }
  cells.push(cur); return cells;
};
const esc = (v) => (/[",\n;]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v);
const lines = fs.readFileSync(path.join(root, 'docs/aed/wzorcowy_zakres_danych_AED_v1.csv'), 'utf8').trim().split('\n');
const baseHeader = parse(lines[0]);
const baseRows = lines.slice(1).map(parse);
const clone = () => ({ header: [...baseHeader], rows: baseRows.map((r) => [...r]) });
const col = (t, name) => t.header.indexOf(name);
const set = (t, row, name, value) => { t.rows[row][col(t, name)] = value; return t; };
const toCsv = (t, sep = ',') => [t.header, ...t.rows].map((r) => r.map(esc).join(sep)).join('\n') + '\n';
const addColumn = (t, name, value) => { t.header.push(name); t.rows.forEach((r) => r.push(value)); return t; };
const dropColumn = (t, name) => { const i = col(t, name); t.header.splice(i, 1); t.rows.forEach((r) => r.splice(i, 1)); return t; };

const cp1250 = { 'ą': 0xb9, 'ć': 0xe6, 'ę': 0xea, 'ł': 0xb3, 'ń': 0xf1, 'ó': 0xf3, 'ś': 0x9c, 'ź': 0x9f, 'ż': 0xbf,
  'Ą': 0xa5, 'Ć': 0xc6, 'Ę': 0xca, 'Ł': 0xa3, 'Ń': 0xd1, 'Ó': 0xd3, 'Ś': 0x8c, 'Ź': 0x8f, 'Ż': 0xaf };
const toCp1250 = (s) => Buffer.from([...s].map((ch) => cp1250[ch] ?? ch.charCodeAt(0)));

const fixtures = {
  'valid.csv': [toCsv(clone()), []],
  // ERROR
  'missing_column.csv': [toCsv(dropColumn(clone(), 'ulica')), ['MISSING_COLUMN']],
  'forbidden_column.csv': [toCsv(addColumn(clone(), 'Kod_Szafki', '1234')), ['FORBIDDEN_COLUMN']],
  'row_length.csv': [(() => { const t = clone(); t.rows[0].push('nadmiarowa'); return toCsv(t); })(), ['ROW_LENGTH']],
  'required_empty.csv': [toCsv(set(clone(), 0, 'nazwa_obiektu', '')), ['REQUIRED_EMPTY']],
  'invalid_date.csv': [toCsv(set(clone(), 0, 'data_aktualizacji', '01.10.2026')), ['INVALID_DATE']],
  'invalid_number.csv': [toCsv(set(clone(), 0, 'szerokosc_geograficzna', '52,1050')), ['INVALID_NUMBER']],
  'invalid_boolean.csv': [toCsv(set(clone(), 0, 'dostep_publiczny', 'tak')), ['INVALID_BOOLEAN']],
  'enum_value.csv': [toCsv(set(clone(), 0, 'status_urzadzenia', 'DZIALA')), ['ENUM_VALUE']],
  'out_of_poland.csv': [toCsv(set(set(clone(), 0, 'szerokosc_geograficzna', '21.2600'), 0, 'dlugosc_geograficzna', '52.1050')),
    ['OUT_OF_POLAND', 'OUT_OF_POLAND']],
  'duplicate_id.csv': [toCsv(set(clone(), 1, 'id_aed', 'OTW-0001')), ['DUPLICATE_ID']],
  'future_update_date.csv': [toCsv(set(clone(), 0, 'data_aktualizacji', '2027-01-01')), ['FUTURE_UPDATE_DATE']],
  'encoding.csv': [toCp1250(toCsv(clone())), ['ENCODING']],
  'invalid_format.csv': [toCsv(set(clone(), 0, 'kod_pocztowy', '05-4000')), ['INVALID_FORMAT']],
  'empty_row.csv': [(() => { const c = toCsv(clone()).split('\n'); c.splice(2, 0, ''); return c.join('\n'); })(), ['EMPTY_ROW']],
  'empty_column_header.csv': [toCsv(addColumn(clone(), '', '')), ['EMPTY_COLUMN_HEADER']],
  'delimiter.csv': [toCsv(clone(), ';'), ['DELIMITER', 'MISSING_COLUMN']],
  // WARNING
  'unknown_column.csv': [toCsv(addColumn(clone(), 'uwagi', 'brak')), ['UNKNOWN_COLUMN']],
  'opening_hours_unsupported.csv': [toCsv(set(clone(), 0, 'godziny_dostepnosci', 'sunrise-sunset')), ['OPENING_HOURS_UNSUPPORTED']],
  'electrodes_expired.csv': [toCsv(set(clone(), 0, 'data_waznosci_elektrod', '2026-01-31')), ['ELECTRODES_EXPIRED']],
  'battery_expired.csv': [toCsv(set(clone(), 0, 'data_waznosci_baterii', '2026-02-28')), ['BATTERY_EXPIRED']],
  'stale_update.csv': [toCsv(set(clone(), 0, 'data_aktualizacji', '2025-06-01')), ['STALE_UPDATE']],
  'near_duplicate_5m.csv': [(() => { const t = clone(); const r = [...t.rows[0]]; t.rows.push(r);
    r[col(t, 'id_aed')] = 'OTW-0002'; r[col(t, 'szerokosc_geograficzna')] = '52.10502'; r[col(t, 'dlugosc_geograficzna')] = '21.26002';
    return toCsv(t); })(), ['NEAR_DUPLICATE_5M']],
  'utf8_bom.csv': [Buffer.concat([Buffer.from([0xef, 0xbb, 0xbf]), Buffer.from(toCsv(clone()))]), ['UTF8_BOM']],
  'postal_code_format.csv': [toCsv(set(clone(), 0, 'kod_pocztowy', '05400')), ['POSTAL_CODE_FORMAT']],
};

const manifest = {};
for (const [name, [content, codes]] of Object.entries(fixtures)) {
  fs.writeFileSync(path.join(out, name), content);
  manifest[name] = codes;
}
fs.writeFileSync(path.join(out, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
console.log(`${Object.keys(fixtures).length} fixtures -> ${out}`);
