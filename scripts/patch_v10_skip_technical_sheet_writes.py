from pathlib import Path

p = Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL_V10.txt')
s = p.read_text(encoding='utf-8')

old1 = "    writeCsvSheet_(ss.getSheetByName(V8_SHEETS.marketReader), mrCsv, false);"
new1 = "    PropertiesService.getDocumentProperties().setProperty('V10_MARKET_READER_CSV_CACHE', mrCsv);"
if old1 not in s:
    raise SystemExit('marketReader writeCsvSheet call not found')
s = s.replace(old1, new1, 1)

old2 = """    let machineSheet = getOrCreateSheet_(ss, 'DANE_MASZYNOWNIA');\n    machineSheet = writeCsvSheet_(machineSheet, machineCsv, false);\n    machineSheet.hideSheet();"""
new2 = """    PropertiesService.getDocumentProperties().setProperty('V10_MACHINE_CSV_CACHE', machineCsv);\n    const machineSheet = getOrCreateSheet_(ss, 'DANE_MASZYNOWNIA');\n    machineSheet.hideSheet();"""
if old2 not in s:
    raise SystemExit('machine writeCsvSheet block not found')
s = s.replace(old2, new2, 1)

# No runtime call to writeCsvSheet_ should remain inside ODSWIEZ_WSZYSTKO.
start = s.index('function ODSWIEZ_WSZYSTKO()')
end = s.find('\nfunction ', start + 1)
block = s[start:end if end > 0 else len(s)]
if 'writeCsvSheet_(' in block:
    raise SystemExit('writeCsvSheet_ still called from ODSWIEZ_WSZYSTKO')

p.write_text(s, encoding='utf-8')
print('Patched V10: ODSWIEZ_WSZYSTKO no longer writes technical CSV sheets; caches them in DocumentProperties instead.')
