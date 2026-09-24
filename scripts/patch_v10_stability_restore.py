from pathlib import Path

p = Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL_V10.txt')
s = p.read_text(encoding='utf-8')

# 1) Nie używamy globalnego kolorowania całego skoroszytu.
s = s.replace('    applyUnifiedThemeV10_(ss);\n', '')
s = s.replace('    applyUnifiedV8Theme_(ss);\n', '')
s = s.replace('  applyUnifiedThemeV10_(ss);\n', '')
s = s.replace('  applyUnifiedV8Theme_(ss);\n', '')

# 2) Bezpieczne rozpinanie scaleń.
# Zamiast breakApart() na dużym zakresie rozpinamy KAŻDY faktycznie scalony zakres osobno.
# getMergedRanges() zwraca dokładne zakresy scaleń, więc nie ma błędu
# "musisz zaznaczyć wszystkie komórki w scalanym zakresie".
safe_unmerge = "  sheet.getMergedRanges().forEach(r => r.breakApart());\n"
for fn in ['setupPortfolioLong_', 'setupPortfolioTactical_', 'setupMorningBrief_']:
    marker = f'function {fn}(sheet) {{\n'
    if marker not in s:
        continue
    start = s.index(marker) + len(marker)
    tail = s[start:start+420]
    for old in [
        '  sheet.getDataRange().breakApart();\n',
        '  sheet.getRange(1, 1, sheet.getMaxRows(), sheet.getMaxColumns()).breakApart();\n',
        '  sheet.getMergedRanges().forEach(r => r.breakApart());\n'
    ]:
        tail = tail.replace(old, '')
    s = s[:start] + safe_unmerge + tail + s[start+420:]

# 3) Tryb Porannego Radaru poza arkuszem — DocumentProperties, bez K1.
old_setup = """function setupMorningBrief_(sheet) {\n  sheet.getRange(1, 1, sheet.getMaxRows(), sheet.getMaxColumns()).breakApart();\n  let savedMode = String(sheet.getRange('K1').getDisplayValue() || '').trim().toUpperCase();\n  if (!['1H','2H','4H','AUTO'].includes(savedMode)) savedMode = '1H';\n\n  sheet.clear();\n  sheet.setHiddenGridlines(true);\n  sheet.getRange('K1').setValue(savedMode);\n  sheet.hideColumns(11);\n"""
new_setup = """function setupMorningBrief_(sheet) {\n  sheet.getMergedRanges().forEach(r => r.breakApart());\n  let savedMode = String(PropertiesService.getDocumentProperties().getProperty('V10_MORNING_MODE') || '1H').trim().toUpperCase();\n  if (!['1H','2H','4H','AUTO'].includes(savedMode)) savedMode = '1H';\n  sheet.clear();\n  sheet.setHiddenGridlines(true);\n  PropertiesService.getDocumentProperties().setProperty('V10_MORNING_MODE', savedMode);\n"""
s = s.replace(old_setup, new_setup)

# Usuń ewentualny drugi breakApart() z początku setupMorningBrief_.
needle = "function setupMorningBrief_(sheet) {\n  sheet.getMergedRanges().forEach(r => r.breakApart());\n"
if needle in s:
    start = s.index(needle) + len(needle)
    tail = s[start:start+300]
    tail = tail.replace('  sheet.getRange(1, 1, sheet.getMaxRows(), sheet.getMaxColumns()).breakApart();\n', '')
    tail = tail.replace('  sheet.getDataRange().breakApart();\n', '')
    tail = tail.replace('  sheet.getMergedRanges().forEach(r => r.breakApart());\n', '')
    s = s[:start] + tail + s[start+300:]

old_mode = """function morningRadarModeV10_(sheet) {\n  const v = String(sheet.getRange('K1').getDisplayValue() || '1H').trim().toUpperCase();\n  return ['1H','2H','4H','AUTO'].includes(v) ? v : '1H';\n}\n"""
new_mode = """function morningRadarModeV10_(sheet) {\n  const v = String(PropertiesService.getDocumentProperties().getProperty('V10_MORNING_MODE') || '1H').trim().toUpperCase();\n  return ['1H','2H','4H','AUTO'].includes(v) ? v : '1H';\n}\n"""
s = s.replace(old_mode, new_mode)

s = s.replace("    sheet.getRange('K1').setValue(mode);\n    styleMorningRadarButtonsV10_(sheet, mode);",
              "    PropertiesService.getDocumentProperties().setProperty('V10_MORNING_MODE', mode);\n    styleMorningRadarButtonsV10_(sheet, mode);")

# 4) Bezpieczne kolorowanie tylko prostych tabel danych bez scaleń.
if 'function applySafeEngineColorsV10_' not in s:
    s += r'''

// ===== V10 SAFE TABLE COLORS — BEZ GLOBALNEGO SKANOWANIA =====
function applySafeEngineColorsV10_(sheet) {
  const rows = sheet.getLastRow();
  const cols = sheet.getLastColumn();
  if (rows < 2 || cols < 1) return;
  const range = sheet.getRange(1,1,rows,cols);
  if (range.getMergedRanges().length) return;
  const vals = range.getDisplayValues();
  const headers = vals[0].map(v => String(v||'').trim().toUpperCase());

  for (let r=1; r<vals.length; r++) {
    for (let c=0; c<vals[r].length; c++) {
      const raw = String(vals[r][c]||'').trim();
      if (!raw) continue;
      const t = raw.toUpperCase();
      const cell = sheet.getRange(r+1,c+1);
      const h = headers[c] || '';

      if (t==='BLOKUJ' || t==='GORĄCO' || t==='KRYTYCZNY' || t==='NIE DOKŁADAJ' || t==='OCHRONA KAPITAŁU')
        cell.setBackground('#FAD1D1').setFontColor('#8F2D2D').setFontWeight('bold');
      else if (t==='CHŁODNO' || t==='WYPRZEDANIE' || t.indexOf('DOLNE GRANICE')>=0 || t.indexOf('DOLNE OSTRZEŻ')>=0)
        cell.setBackground('#D9EAF7').setFontColor('#245B78').setFontWeight('bold');
      else if (t==='NEUTRALNIE' || t==='ZEZWÓL' || t==='GOTOWE' || t==='AKTUALNE' || t==='KUP' || t==='KUP TRENDOWO')
        cell.setBackground('#DDF2E3').setFontColor('#1F6B3A').setFontWeight('bold');
      else if (t==='UWAGA' || t.indexOf('UWAGA ')===0 || t==='OSTROŻNIE' || t==='CZEKAJ' || t==='PODWYŻSZONE RYZYKO')
        cell.setBackground('#FFF0B8').setFontColor('#7A5B00').setFontWeight('bold');

      const n = Number(raw.replace(',','.'));
      if (!Number.isFinite(n)) continue;
      if (h.indexOf('RSI')>=0) {
        if (n>=75) cell.setBackground('#FAD1D1').setFontColor('#8F2D2D').setFontWeight('bold');
        else if (n<=25) cell.setBackground('#D9EAF7').setFontColor('#245B78').setFontWeight('bold');
      } else if (h.indexOf('MFI')>=0) {
        if (n>=80) cell.setBackground('#FAD1D1').setFontColor('#8F2D2D').setFontWeight('bold');
        else if (n<=20) cell.setBackground('#D9EAF7').setFontColor('#245B78').setFontWeight('bold');
      } else if (h.indexOf('FOMO')>=0) {
        if (n>=8) cell.setBackground('#FCE2B8').setFontColor('#8A4B08').setFontWeight('bold');
        else if (n>=6) cell.setBackground('#FFF0B8').setFontColor('#7A5B00').setFontWeight('bold');
      } else if (h.indexOf('RYZYKO')>=0) {
        if (n>=8) cell.setBackground('#FAD1D1').setFontColor('#8F2D2D').setFontWeight('bold');
        else if (n>=5) cell.setBackground('#FFF0B8').setFontColor('#7A5B00').setFontWeight('bold');
        else if (n<=2) cell.setBackground('#DDF2E3').setFontColor('#1F6B3A').setFontWeight('bold');
      }
    }
  }
}
'''

# LONG
old = "  if (assets.length) sheet.getRange(2,1,assets.length,headers.length).setValues(assets);\n  sheet.setFrozenRows(1);\n}\n\nfunction writeTacticalEngine_"
new = "  if (assets.length) sheet.getRange(2,1,assets.length,headers.length).setValues(assets);\n  sheet.setFrozenRows(1);\n  applySafeEngineColorsV10_(sheet);\n}\n\nfunction writeTacticalEngine_"
if 'applySafeEngineColorsV10_(sheet);\n}\n\nfunction writeTacticalEngine_' not in s:
    s = s.replace(old,new,1)

# TACTICAL
old = "  if (assets.length) sheet.getRange(2,1,assets.length,headers.length).setValues(assets);\n  sheet.setFrozenRows(1);\n}\n\nfunction writeFlowEngine_"
new = "  if (assets.length) sheet.getRange(2,1,assets.length,headers.length).setValues(assets);\n  sheet.setFrozenRows(1);\n  applySafeEngineColorsV10_(sheet);\n}\n\nfunction writeFlowEngine_"
if 'applySafeEngineColorsV10_(sheet);\n}\n\nfunction writeFlowEngine_' not in s:
    s = s.replace(old,new,1)

p.write_text(s, encoding='utf-8')
print('V10 stability root fix: exact merged ranges only + mode in DocumentProperties')
