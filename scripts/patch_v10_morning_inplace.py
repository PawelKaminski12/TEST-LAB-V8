from pathlib import Path

p = Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL_V10.txt')
s = p.read_text(encoding='utf-8')

old = """function freshMorningSheetV10_(ss) {\n  const old = ss.getSheetByName(V10_MORNING_SHEET);\n  let index = null;\n  if (old) {\n    index = old.getIndex();\n    ss.deleteSheet(old);\n  }\n  return index ? ss.insertSheet(V10_MORNING_SHEET, index) : ss.insertSheet(V10_MORNING_SHEET);\n}\n"""
new = """function freshMorningSheetV10_(ss) {\n  // Nie kasujemy aktywnej karty PORANNY_BRIEF. Kasowanie aktywnego arkusza powoduje\n  // w interfejsie Sheets komunikat: \"Komórka, którą próbujesz edytować, mogła zostać przeniesiona lub usunięta\".\n  // Brief jest odświeżany w miejscu; setupMorningBrief_ rozłącza wyłącznie znane scalenia.\n  return ss.getSheetByName(V10_MORNING_SHEET) || ss.insertSheet(V10_MORNING_SHEET);\n}\n"""
if old not in s:
    raise SystemExit('freshMorningSheetV10_ old block not found')
s = s.replace(old, new, 1)

needle = """function setupMorningBrief_(sheet) {\n  let savedMode = String(PropertiesService.getDocumentProperties().getProperty('V10_MORNING_MODE') || '1H').trim().toUpperCase();\n  if (!['1H','2H','4H','AUTO'].includes(savedMode)) savedMode = '1H';\n  sheet.clear();\n"""
replacement = """function setupMorningBrief_(sheet) {\n  let savedMode = String(PropertiesService.getDocumentProperties().getProperty('V10_MORNING_MODE') || '1H').trim().toUpperCase();\n  if (!['1H','2H','4H','AUTO'].includes(savedMode)) savedMode = '1H';\n\n  // Bezpieczne odświeżanie w miejscu: rozłączamy tylko dokładnie te scalenia, które sam Brief tworzy.\n  // Nie skanujemy arkusza i nie używamy globalnego breakApart().\n  const morningMergesV10 = [\n    'A1:J1','F2:J2','A4:B4','D4:I4','A10:F10','H10:J10','A18:I18',\n    'L4:O4','M5:O5','M6:O6','M7:O7','M8:O8','M9:O9','M10:O10','M11:O11','L13:O13'\n  ];\n  morningMergesV10.forEach(a1 => {\n    try { sheet.getRange(a1).breakApart(); } catch (e) { /* zakres może być niescalony */ }\n  });\n  sheet.clear();\n"""
if needle not in s:
    raise SystemExit('setupMorningBrief_ anchor not found')
s = s.replace(needle, replacement, 1)

p.write_text(s, encoding='utf-8')
print('PATCH OK: Morning Radar refresh in place; no active-sheet deletion')
