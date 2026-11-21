// Inserts docs/aed/scripts/aed-i18n.json into frontend_latest/src/assets/i18n/{pl,en}.json as text, so the rest of
// the files stays byte-identical: "Aed" block after the "Action" block, ROUTES.aed* after "ROUTES.404".
// Idempotent (previously inserted AED parts are removed first). Keeps CRLF.
const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '../../..');
const aed = JSON.parse(fs.readFileSync(path.join(__dirname, 'aed-i18n.json'), 'utf8'));
for (const lang of ['pl', 'en']) {
  const file = path.join(root, 'frontend_latest/src/assets/i18n', `${lang}.json`);
  const raw = fs.readFileSync(file, 'utf8');
  const eol = raw.includes('\r\n') ? '\r\n' : '\n';
  let lines = raw.split(eol);
  // remove previous insertion
  lines = lines.filter((l) => !/^  "ROUTES\.aed/.test(l));
  const start = lines.findIndex((l) => l === '  "Aed": {');
  if (start >= 0) {
    const end = lines.findIndex((l, i) => i > start && l === '  },');
    lines.splice(start, end - start + 1);
  }
  const routesIdx = lines.findIndex((l) => l.startsWith('  "ROUTES.404"'));
  const routeLines = Object.entries(aed[lang]).filter(([k]) => k.startsWith('ROUTES.')).map(([k, v]) => `  ${JSON.stringify(k)}: ${JSON.stringify(v)},`);
  lines.splice(routesIdx + 1, 0, ...routeLines);
  const actionIdx = lines.findIndex((l) => l === '  "Action": {');
  const actionEnd = lines.findIndex((l, i) => i > actionIdx && l === '  },');
  const block = ('  "Aed": ' + JSON.stringify(aed[lang].Aed, null, 2).split('\n').join('\n  ') + ',').split('\n');
  lines.splice(actionEnd + 1, 0, ...block);
  const text = lines.join(eol);
  JSON.parse(text); // must stay valid
  fs.writeFileSync(file, text);
  console.log(`${lang}.json updated`);
}
