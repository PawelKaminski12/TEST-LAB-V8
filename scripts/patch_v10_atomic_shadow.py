from pathlib import Path

p = Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL_V10.txt')
s = p.read_text(encoding='utf-8')


def replace_function(src, name, replacement):
    marker = f'function {name}('
    start = src.find(marker)
    if start < 0:
        raise SystemExit(f'Missing function: {name}')
    brace = src.find('{', start)
    depth = 0
    in_s = in_d = in_t = False
    esc = False
    i = brace
    while i < len(src):
        ch = src[i]
        if esc:
            esc = False
        elif ch == '\\' and (in_s or in_d or in_t):
            esc = True
        elif not in_d and not in_t and ch == "'":
            in_s = not in_s
        elif not in_s and not in_t and ch == '"':
            in_d = not in_d
        elif not in_s and not in_d and ch == '`':
            in_t = not in_t
        elif not (in_s or in_d or in_t):
            if ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return src[:start] + replacement.rstrip() + '\n' + src[i+1:]
        i += 1
    raise SystemExit(f'Unclosed function: {name}')

new_fn = r'''function writeCsvSheet_(sheet, csvText, preserveCompactPanel) {
  const rows = Utilities.parseCsv(csvText);
  const ss = sheet.getParent();
  const baseName = sheet.getName();
  const finalName = baseName + '_V10_DATA';
  const tmpName = baseName + '_V10_TMP_' + Date.now();

  // V10 ATOMIC SHADOW: zawsze zapisujemy do NOWEGO arkusza.
  // Nie czyścimy, nie rozpinamy i nie zapisujemy do żadnego istniejącego arkusza technicznego.
  let out = ss.insertSheet(tmpName);

  if (rows.length) {
    out.getRange(1, 1, rows.length, rows[0].length).setValues(rows);
    out.setFrozenRows(1);
    if (preserveCompactPanel) {
      const maxCols = 7;
      if (out.getMaxColumns() > maxCols) out.hideColumns(maxCols + 1, out.getMaxColumns() - maxCols);
    }
  }

  // Dopiero po udanym zapisie próbujemy wymienić poprzedni shadow.
  const old = ss.getSheetByName(finalName);
  if (old) {
    try {
      ss.deleteSheet(old);
      out.setName(finalName);
    } catch (e) {
      // Jeśli stary arkusz jest uszkodzony po wcześniejszych scaleniach, nie dotykamy go więcej.
      // Nowy pozostaje pod unikalną nazwą i cały przebieg może iść dalej.
      out.setName(baseName + '_V10_DATA_' + Date.now());
    }
  } else {
    out.setName(finalName);
  }

  return out;
}'''

s = replace_function(s, 'writeCsvSheet_', new_fn)

start=s.index('function writeCsvSheet_(')
end=s.find('\nfunction ', start+1)
block=s[start:end if end>0 else len(s)]
for forbidden in ('clearContents()', 'getMergedRanges()', 'breakApart()', 'unmergeAllSafelyV10_'):
    if forbidden in block:
        raise SystemExit(f'Forbidden token in writeCsvSheet_: {forbidden}')
for required in ('ss.insertSheet(tmpName)', 'ss.deleteSheet(old)', 'out.setName(finalName)'):
    if required not in block:
        raise SystemExit(f'Missing required atomic-shadow token: {required}')

p.write_text(s, encoding='utf-8')
print('Patched V10: atomic fresh shadow sheets; no writes/clears on existing technical sheets.')
