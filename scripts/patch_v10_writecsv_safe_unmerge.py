from pathlib import Path

p = Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL_V10.txt')
s = p.read_text(encoding='utf-8')
old = """function writeCsvSheet_(sheet, csvText, preserveCompactPanel) {\n  const rows = Utilities.parseCsv(csvText);\n  sheet.clearContents();"""
new = """function writeCsvSheet_(sheet, csvText, preserveCompactPanel) {\n  const rows = Utilities.parseCsv(csvText);\n  // CSV-y są tabelami prostymi; przed zapisem rozpinamy wyłącznie realne stare scalenia.\n  // Zapobiega błędowi Apps Script: 'musisz zaznaczyć wszystkie komórki w scalanym zakresie'.\n  unmergeAllSafelyV10_(sheet);\n  sheet.clearContents();"""
if old not in s:
    raise SystemExit('writeCsvSheet_ target not found')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
print('Patched writeCsvSheet_ with safe exact merged-range unmerge')
