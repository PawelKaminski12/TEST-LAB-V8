from pathlib import Path

p = Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL_V10.txt')
s = p.read_text(encoding='utf-8')

# Ensure the legend is redrawn after every Morning Radar render.
needle = "  styleMorningRadarButtonsV10_(sheet, morningRadarModeV10_(sheet));\n}"
replacement = "  styleMorningRadarButtonsV10_(sheet, morningRadarModeV10_(sheet));\n  drawMorningRadarLegendV10_(sheet);\n}"
if "drawMorningRadarLegendV10_(sheet);" not in s:
    pos = s.rfind(needle)
    if pos < 0:
        raise SystemExit('final Morning Radar polish marker not found')
    s = s[:pos] + s[pos:].replace(needle, replacement, 1)

marker = '// ===== V10 MORNING RADAR LEGEND ====='
if marker not in s:
    s += r'''

// ===== V10 MORNING RADAR LEGEND =====
function drawMorningRadarLegendV10_(sheet) {
  // Wolna prawa część ekranu: stała legenda kolorów + wyjaśnienie AUTO.
  const title = sheet.getRange('L4:N4');
  title.merge().setValue('LEGENDA KOLORÓW')
    .setBackground('#CFE8F6').setFontColor('#17324D').setFontWeight('bold')
    .setFontFamily('Roboto').setFontSize(12)
    .setHorizontalAlignment('center').setVerticalAlignment('middle');

  const rows = [
    ['GORĄCO',      'przegrzanie / mocna górna skrajność', 'HOT'],
    ['CHŁODNO',     'wyprzedanie / dolna skrajność',       'COLD'],
    ['NEUTRALNIE',  'brak mocnej skrajności',              'NEUTRAL'],
    ['UWAGA',       'sygnał wymagający obserwacji',         'WARN'],
    ['FOMO ≥ 8',    'wysokie FOMO / ryzyko gonienia ceny',  'FOMO'],
    ['MACD ALERT',  'ostrzeżenie lub ekstremum MACD',       'MACD'],
    ['INFO',        'informacja pomocnicza',                'INFO']
  ];

  sheet.getRange(5,12,rows.length,3).clearContent().clearFormat();
  rows.forEach((x, i) => {
    const r = 5 + i;
    const c = morningPaletteV10_(x[2]);
    sheet.getRange(r,12).setValue(x[0]).setBackground(c.bg).setFontColor(c.fg)
      .setFontWeight('bold').setHorizontalAlignment('center');
    sheet.getRange(r,13,1,2).merge().setValue(x[1]).setBackground(c.bg).setFontColor(c.fg)
      .setHorizontalAlignment('left');
    sheet.getRange(r,12,1,3).setBorder(true,true,true,true,true,true,'#B8CDD9',SpreadsheetApp.BorderStyle.SOLID);
  });

  sheet.getRange('L13:N13').merge().setValue('AUTO — dla każdej monety wybiera osobno najsilniejszy sygnał z 1H / 2H / 4H. To nie jest średnia.')
    .setBackground('#EAF4FB').setFontColor('#245A7A').setFontWeight('bold')
    .setWrap(true).setHorizontalAlignment('left').setVerticalAlignment('middle')
    .setBorder(true,true,true,true,true,true,'#9DBFD5',SpreadsheetApp.BorderStyle.SOLID_MEDIUM);

  sheet.setColumnWidth(12,140);
  sheet.setColumnWidth(13,210);
  sheet.setColumnWidth(14,210);
  sheet.setRowHeight(4,29);
  sheet.setRowHeights(5,7,27);
  sheet.setRowHeight(13,54);
}
'''

p.write_text(s, encoding='utf-8')
print('V10 Morning Radar legend patched')
