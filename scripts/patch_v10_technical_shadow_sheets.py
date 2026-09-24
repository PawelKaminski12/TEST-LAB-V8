from pathlib import Path

p = Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL_V10.txt')
s = p.read_text(encoding='utf-8')

# Replace technical CSV writer with a version that NEVER touches the contaminated legacy sheet.
start = s.index('function writeCsvSheet_(')
brace = s.index('{', start)
depth = 0
end = None
in_s = in_d = in_t = False
esc = False
for i in range(brace, len(s)):
    ch = s[i]
    if esc:
        esc = False
        continue
    if ch == '\\' and (in_s or in_d or in_t):
        esc = True
        continue
    if not in_d and not in_t and ch == "'": in_s = not in_s
    elif not in_s and not in_t and ch == '"': in_d = not in_d
    elif not in_s and not in_d and ch == '`': in_t = not in_t
    elif not (in_s or in_d or in_t):
        if ch == '{': depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break
if end is None:
    raise SystemExit('writeCsvSheet_ not closed')

replacement = r'''function writeCsvSheet_(sheet, csvText, preserveCompactPanel) {
  const rows = Utilities.parseCsv(csvText);
  // V10 SHADOW TECH: nigdy nie dotykamy starego arkusza z potencjalnie uszkodzonymi scaleniami.
  // Dane techniczne trafiają do świeżego arkusza _V10_DATA.
  const ss = sheet.getParent();
  const baseName = sheet.getName();
  const dataName = baseName + '_V10_DATA';
  let out = ss.getSheetByName(dataName);
  if (!out) out = ss.insertSheet(dataName);
  out.clearContents();
  if (!rows.length) return out;
  out.getRange(1, 1, rows.length, rows[0].length).setValues(rows);
  out.setFrozenRows(1);
  if (preserveCompactPanel) {
    const maxCols = 7;
    if (out.getMaxColumns() > maxCols) out.hideColumns(maxCols + 1, out.getMaxColumns() - maxCols);
  }
  return out;
}'''
s = s[:start] + replacement + s[end:]

# Ensure machine-room uses returned clean sheet and hides it.
s = s.replace("let machineSheet = getOrCreateSheet_(ss, 'DANE_MASZYNOWNIA');\n    machineSheet = writeCsvSheet_(machineSheet, machineCsv, false);\n    machineSheet.hideSheet();",
              "let machineSheet = getOrCreateSheet_(ss, 'DANE_MASZYNOWNIA');\n    machineSheet = writeCsvSheet_(machineSheet, machineCsv, false);\n    machineSheet.hideSheet();")

p.write_text(s, encoding='utf-8')
print('Patched V10: technical CSVs now write only to clean *_V10_DATA shadow sheets; legacy merged sheets untouched.')
