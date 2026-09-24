from pathlib import Path

p = Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL_V10.txt')
s = p.read_text(encoding='utf-8')

# Cache radar data during full refresh so interval buttons can redraw instantly.
needle = "    const morningRadarJson = JSON.parse(fetchText_(V10_MORNING_RADAR_URL));"
replacement = needle + "\n    PropertiesService.getDocumentProperties().setProperty('V10_MORNING_RADAR_CACHE', JSON.stringify(morningRadarJson));"
if "V10_MORNING_RADAR_CACHE" not in s:
    if needle not in s:
        raise SystemExit('morningRadarJson fetch marker not found')
    s = s.replace(needle, replacement, 1)

# Replace standalone refresh so it also updates the local cache.
start = s.find('function ODSWIEZ_PORANNY_BRIEF() {')
end = s.find('\nfunction setupPortfolioLong_', start)
if start < 0 or end < 0:
    raise SystemExit('ODSWIEZ_PORANNY_BRIEF boundaries not found')
new_refresh = r'''function ODSWIEZ_PORANNY_BRIEF() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = getOrCreateSheet_(ss, V10_MORNING_SHEET);
  const radarJson = JSON.parse(fetchText_(V10_MORNING_RADAR_URL));
  PropertiesService.getDocumentProperties().setProperty('V10_MORNING_RADAR_CACHE', JSON.stringify(radarJson));
  writeMorningRadarBrief_(sheet, radarJson);
  ss.toast('Poranny Radar odświeżony — ' + morningRadarModeV10_(sheet), 'V8', 4);
}
'''
s = s[:start] + new_refresh + s[end:]

# Replace setup with large, visible interval selectors.
start = s.find('function setupMorningBrief_(sheet) {')
end = s.find('\nfunction writeMorningBrief_', start)
if start < 0 or end < 0:
    raise SystemExit('setupMorningBrief_ boundaries not found')
new_setup = r'''function setupMorningBrief_(sheet) {
  let savedMode = String(sheet.getRange('K1').getDisplayValue() || '').trim().toUpperCase();
  if (!['1H','2H','4H','AUTO'].includes(savedMode)) savedMode = '1H';

  sheet.clear();
  sheet.setHiddenGridlines(true);
  sheet.getRange('K1').setValue(savedMode);
  sheet.hideColumns(11);

  sheet.getRange('A1:J1').merge().setValue('V8 / PORANNY RADAR — RĘCZNY WYBÓR INTERWAŁU');
  sheet.getRange('A1:J1')
    .setBackground('#DCEEF8').setFontColor('#17324D').setFontWeight('bold')
    .setFontFamily('Roboto').setFontSize(18).setHorizontalAlignment('center').setVerticalAlignment('middle');

  sheet.getRange('A2').setValue('INTERWAŁ');
  sheet.getRange('B2:E2').setValues([['1H','2H','4H','AUTO']]);
  sheet.getRange('F2:J2').merge().setValue('Kliknij 1H / 2H / 4H. AUTO nie jest średnią — wybiera najsilniejszy sygnał osobno dla każdego aktywa.');
  sheet.getRange('A2:J2').setFontWeight('bold').setHorizontalAlignment('center').setVerticalAlignment('middle');
  sheet.getRange('A2').setBackground('#EAF4FB');
  sheet.getRange('F2:J2').setBackground('#F8FBFD').setFontColor('#456276').setHorizontalAlignment('left').setFontWeight('normal');
  styleMorningRadarButtonsV10_(sheet, savedMode);

  sheet.getRange('A4:B4').merge().setValue('STAN RADARU');
  sheet.getRange('D4:I4').merge().setValue('TERAZ — KLUCZOWE LICZBY');
  sheet.getRange('A10:F10').merge().setValue('PRIORYTETY — NAJSILNIEJSZE SYGNAŁY');
  sheet.getRange('H10:J10').merge().setValue('DO OBSERWACJI — SYGNAŁY UMIARKOWANE');
  sheet.getRange('A18:I18').merge().setValue('RADAR 13 ALTÓW');
  ['A4:B4','D4:I4','A10:F10','H10:J10','A18:I18'].forEach(a1 => {
    sheet.getRange(a1).setBackground('#CFE8F6').setFontColor('#17324D').setFontWeight('bold')
      .setFontFamily('Roboto').setFontSize(12).setHorizontalAlignment('center').setVerticalAlignment('middle');
  });

  [120,110,110,110,110,120,120,150,430,180].forEach((w,i)=>sheet.setColumnWidth(i+1,w));
  sheet.setFrozenRows(2);
}
'''
s = s[:start] + new_setup + s[end:]

# Mode now lives in hidden K1, not in the selector cell itself.
old_mode = "function morningRadarModeV10_(sheet) {\n  const v = String(sheet.getRange('B2').getDisplayValue() || 'AUTO').trim().toUpperCase();\n  return ['AUTO','1H','2H','4H'].includes(v) ? v : 'AUTO';\n}"
new_mode = "function morningRadarModeV10_(sheet) {\n  const v = String(sheet.getRange('K1').getDisplayValue() || '1H').trim().toUpperCase();\n  return ['1H','2H','4H','AUTO'].includes(v) ? v : '1H';\n}"
if old_mode not in s:
    raise SystemExit('morningRadarModeV10_ marker not found')
s = s.replace(old_mode, new_mode, 1)

# Add visible buttons + instant local redraw on cell selection.
marker = '// ===== V10 MORNING RADAR MANUAL BUTTONS ====='
if marker not in s:
    s += r'''

// ===== V10 MORNING RADAR MANUAL BUTTONS =====
function styleMorningRadarButtonsV10_(sheet, mode) {
  const labels = ['1H','2H','4H','AUTO'];
  labels.forEach((label, i) => {
    const cell = sheet.getRange(2, 2 + i);
    const active = label === mode;
    cell.setValue(label)
      .setBackground(active ? '#4F81BD' : '#EAF4FB')
      .setFontColor(active ? '#FFFFFF' : '#17324D')
      .setFontWeight('bold')
      .setFontSize(active ? 12 : 11)
      .setHorizontalAlignment('center')
      .setVerticalAlignment('middle')
      .setBorder(true,true,true,true,true,true,'#9DBFD5',SpreadsheetApp.BorderStyle.SOLID_MEDIUM);
  });
  sheet.setRowHeight(2, 34);
}

function onSelectionChange(e) {
  try {
    if (!e || !e.range) return;
    const sheet = e.range.getSheet();
    if (sheet.getName() !== V10_MORNING_SHEET) return;
    if (e.range.getRow() !== 2) return;
    const col = e.range.getColumn();
    const modeMap = {2:'1H',3:'2H',4:'4H',5:'AUTO'};
    const mode = modeMap[col];
    if (!mode) return;
    if (morningRadarModeV10_(sheet) === mode) {
      styleMorningRadarButtonsV10_(sheet, mode);
      return;
    }

    sheet.getRange('K1').setValue(mode);
    styleMorningRadarButtonsV10_(sheet, mode);

    const cached = PropertiesService.getDocumentProperties().getProperty('V10_MORNING_RADAR_CACHE');
    if (cached) {
      writeMorningRadarBrief_(sheet, JSON.parse(cached));
      SpreadsheetApp.getActiveSpreadsheet().toast('Radar przełączony na ' + mode, 'V8', 2);
    } else {
      SpreadsheetApp.getActiveSpreadsheet().toast('Wybrano ' + mode + '. Uruchom ODŚWIEŻ PORANNY BRIEF jeden raz.', 'V8', 4);
    }
  } catch (err) {
    console.log('onSelectionChange radar: ' + err);
  }
}
'''

# Use more vertical space, but keep the panel on one screen.
height_marker = "  sheet.setRowHeight(1,34);"
height_replacement = "  sheet.setRowHeight(1,38);\n  sheet.setRowHeights(4,5,26);\n  sheet.setRowHeight(10,28);\n  sheet.setRowHeights(11,5,25);\n  sheet.setRowHeight(18,28);\n  sheet.setRowHeight(19,27);\n  if (n) sheet.setRowHeights(20,n,25);"
if height_marker in s:
    s = s.replace(height_marker, height_replacement, 1)

p.write_text(s, encoding='utf-8')
print('V10 Morning Radar manual interval buttons patched')
