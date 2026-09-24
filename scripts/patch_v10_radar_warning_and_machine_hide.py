from pathlib import Path

p = Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL_V10.txt')
s = p.read_text(encoding='utf-8')

# 1) Never touch/hide legacy DANE_MASZYNOWNIA during refresh.
old = """    PropertiesService.getDocumentProperties().setProperty('V10_MACHINE_CSV_CACHE', machineCsv);\n    const machineSheet = getOrCreateSheet_(ss, 'DANE_MASZYNOWNIA');\n    machineSheet.hideSheet();"""
new = """    PropertiesService.getDocumentProperties().setProperty('V10_MACHINE_CSV_CACHE', machineCsv);\n    // V10: legacy DANE_MASZYNOWNIA is intentionally left untouched.\n    // Technical CSV lives in DocumentProperties to avoid old merge-state failures."""
if old not in s:
    raise SystemExit('Machine hide block not found')
s = s.replace(old, new, 1)

# 2) Radar row warning semantics: any non-normal MACD label is a warning row.
old = """  if (Number.isFinite(fomo) && fomo >= 8) return 'FOMO';\n  if (macd.indexOf('EKSTREMUM') >= 0 || macd.indexOf('UWAGA') >= 0) return 'WARN';\n  if (Number.isFinite(rsi) && (rsi >= 75 || rsi <= 25)) return 'WARN';\n  if (Number.isFinite(mfi) && (mfi >= 90 || mfi <= 10)) return 'WARN';"""
new = """  if (Number.isFinite(fomo) && fomo >= 8) return 'FOMO';\n  // MACD: NORMALNY is the only neutral label. DOLNE/GORNE GRANICE, OSTRZEZ.,\n  // EKSTREMUM etc. must make the whole asset row yellow.\n  if (macd && macd.indexOf('NORMAL') < 0) return 'WARN';\n  if (Number.isFinite(rsi) && (rsi >= 75 || rsi <= 25)) return 'WARN';\n  // MFI warning band starts at 80/20; 90/10 remains the stronger extreme tier in engine logic.\n  if (Number.isFinite(mfi) && (mfi >= 80 || mfi <= 20)) return 'WARN';"""
if old not in s:
    raise SystemExit('strongestMorningRowKind warning block not found')
s = s.replace(old, new, 1)

# 3) Individual cells use the same warning thresholds/semantics.
old = """    const mfi = Number(sheet.getRange(r,4).getValue());\n    if (mfi >= 90 || mfi <= 10) paintMorningRangeV10_(sheet.getRange(r,4), 'WARN', true);\n\n    const macd = String(sheet.getRange(r,5).getDisplayValue() || '').toUpperCase();\n    if (macd.indexOf('EKSTREMUM') >= 0 || macd.indexOf('UWAGA') >= 0) {\n      paintMorningRangeV10_(sheet.getRange(r,5), 'MACD', true);\n    }"""
new = """    const mfi = Number(sheet.getRange(r,4).getValue());\n    if (mfi >= 80 || mfi <= 20) paintMorningRangeV10_(sheet.getRange(r,4), 'WARN', true);\n\n    const macd = String(sheet.getRange(r,5).getDisplayValue() || '').toUpperCase();\n    if (macd && macd.indexOf('NORMAL') < 0) {\n      paintMorningRangeV10_(sheet.getRange(r,5), 'MACD', true);\n    }"""
if old not in s:
    raise SystemExit('Radar cell warning block not found')
s = s.replace(old, new, 1)

p.write_text(s, encoding='utf-8')
print('Patched V10: removed machine-sheet hide and fixed Radar 13 ALT warning colors.')
