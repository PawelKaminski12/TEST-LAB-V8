from pathlib import Path
p=Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL_V10.txt')
s=p.read_text(encoding='utf-8')
old="""function writeCsvSheet_(sheet, csvText, preserveCompactPanel) {
  const rows = Utilities.parseCsv(csvText);
  // CSV-y są tabelami prostymi; przed zapisem rozpinamy wyłącznie realne stare scalenia.
  // Zapobiega błędowi Apps Script: 'musisz zaznaczyć wszystkie komórki w scalanym zakresie'.
  unmergeAllSafelyV10_(sheet);
  sheet.clearContents();
  if (!rows.length) return;
  sheet.getRange(1, 1, rows.length, rows[0].length).setValues(rows);
  sheet.setFrozenRows(1);
  if (preserveCompactPanel) {
    const maxCols = 7;
    if (sheet.getMaxColumns() > maxCols) sheet.hideColumns(maxCols + 1, sheet.getMaxColumns() - maxCols);
  }
}
"""
new="""function writeCsvSheet_(sheet, csvText, preserveCompactPanel) {
  const rows = Utilities.parseCsv(csvText);
  // Te arkusze są czystymi tabelami technicznymi. Jeżeli po starszej wersji zostały
  // jakiekolwiek scalenia, nie próbujemy ich rozdzielać (Google Sheets bywa tu niestabilny).
  // Zamiast tego odbudowujemy tylko ten techniczny arkusz od zera.
  const ss = sheet.getParent();
  const name = sheet.getName();
  const index = sheet.getIndex();
  const wasHidden = sheet.isSheetHidden();
  const merged = sheet.getRange(1, 1, Math.max(1, sheet.getMaxRows()), Math.max(1, sheet.getMaxColumns())).getMergedRanges();
  if (merged.length) {
    ss.deleteSheet(sheet);
    sheet = ss.insertSheet(name, index);
  } else {
    sheet.clearContents();
  }
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
}
"""
if old not in s:
    raise SystemExit('writeCsvSheet_ block not found')
s=s.replace(old,new,1)
s=s.replace("    const machineSheet = getOrCreateSheet_(ss, 'DANE_MASZYNOWNIA');\n    writeCsvSheet_(machineSheet, machineCsv, false);\n    machineSheet.hideSheet();",
            "    let machineSheet = getOrCreateSheet_(ss, 'DANE_MASZYNOWNIA');\n    machineSheet = writeCsvSheet_(machineSheet, machineCsv, false);\n    machineSheet.hideSheet();",1)
p.write_text(s,encoding='utf-8')
print('patched robust CSV rebuild')
