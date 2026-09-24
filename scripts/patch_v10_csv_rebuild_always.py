from pathlib import Path

p = Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL_V10.txt')
s = p.read_text(encoding='utf-8')


def replace_function(src, name, replacement):
    marker = f'function {name}('
    start = src.find(marker)
    if start < 0:
        raise SystemExit(f'Missing function: {name}')
    brace = src.find('{', start)
    if brace < 0:
        raise SystemExit(f'Missing opening brace: {name}')
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
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    return src[:start] + replacement.rstrip() + '\n' + src[end:]
        i += 1
    raise SystemExit(f'Unclosed function: {name}')

new_write_csv = r'''function writeCsvSheet_(sheet, csvText, preserveCompactPanel) {
  const rows = Utilities.parseCsv(csvText);

  // V10 HARDENING: techniczne arkusze CSV są zawsze odbudowywane od zera.
  // Nie pytamy o scalenia i nie wywołujemy breakApart/getMergedRanges, bo w części
  // istniejących skoroszytów samo dotknięcie starych scaleń zgłasza wyjątek Apps Script.
  const ss = sheet.getParent();
  const name = sheet.getName();
  const index = sheet.getIndex();
  const wasHidden = sheet.isSheetHidden();

  ss.deleteSheet(sheet);
  sheet = ss.insertSheet(name, index);

  if (!rows.length) {
    if (wasHidden) sheet.hideSheet();
    return sheet;
  }

  sheet.getRange(1, 1, rows.length, rows[0].length).setValues(rows);
  sheet.setFrozenRows(1);
  if (preserveCompactPanel) {
    const maxCols = 7;
    if (sheet.getMaxColumns() > maxCols) sheet.hideColumns(maxCols + 1, sheet.getMaxColumns() - maxCols);
  }
  if (wasHidden) sheet.hideSheet();
  return sheet;
}'''

s = replace_function(s, 'writeCsvSheet_', new_write_csv)

old = """    const machineSheet = getOrCreateSheet_(ss, 'DANE_MASZYNOWNIA');\n    writeCsvSheet_(machineSheet, machineCsv, false);\n    machineSheet.hideSheet();"""
new = """    const machineSheet = getOrCreateSheet_(ss, 'DANE_MASZYNOWNIA');\n    const rebuiltMachineSheet = writeCsvSheet_(machineSheet, machineCsv, false);\n    rebuiltMachineSheet.hideSheet();"""
if old not in s:
    raise SystemExit('Machine-room caller pattern not found')
s = s.replace(old, new, 1)

# Guard against accidentally retaining the old merge-inspection strategy inside writeCsvSheet_.
start = s.find('function writeCsvSheet_(')
end = s.find('\nfunction ', start + 1)
block = s[start:end if end > 0 else len(s)]
for forbidden in ('getMergedRanges()', 'breakApart()', 'unmergeAllSafelyV10_'):
    if forbidden in block:
        raise SystemExit(f'Forbidden token still in writeCsvSheet_: {forbidden}')

p.write_text(s, encoding='utf-8')
print('Patched V10: writeCsvSheet_ now always rebuilds technical CSV sheets without merge inspection.')
