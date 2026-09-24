from pathlib import Path

p = Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL_V10.txt')
s = p.read_text(encoding='utf-8')

# Run a final visual polish after the existing Morning Radar renderer.
needle = "  styleMorningRadarBriefV10_(sheet, assets);"
replacement = "  styleMorningRadarBriefV10_(sheet, assets);\n  polishMorningRadarV10_(sheet, assets);"
if "polishMorningRadarV10_(sheet, assets);" not in s:
    if needle not in s:
        raise SystemExit('styleMorningRadarBriefV10_ call marker not found')
    s = s.replace(needle, replacement, 1)

marker = '// ===== V10 MORNING RADAR FINAL POLISH ====='
if marker in s:
    s = s.split(marker)[0].rstrip() + '\n'

s += r'''

// ===== V10 MORNING RADAR FINAL POLISH =====
function polishMorningRadarV10_(sheet, assets) {
  const n = assets.length;

  // Około +5% skali całego pulpitu.
  sheet.getRange(1,1,Math.max(32,19+n),10).setFontSize(11);
  sheet.getRange('A1:J1').setFontSize(18);
  ['A4:B4','D4:I4','A10:F10','H10:J10','A18:I18','A19:I19'].forEach(a1 => {
    sheet.getRange(a1).setFontSize(12);
  });
  sheet.getRange('B2:E2').setFontSize(12);
  sheet.setRowHeight(1,40);
  sheet.setRowHeight(2,36);
  sheet.setRowHeights(4,5,27);
  sheet.setRowHeight(10,29);
  sheet.setRowHeights(11,5,26);
  sheet.setRowHeight(18,29);
  sheet.setRowHeight(19,28);
  if (n) sheet.setRowHeights(20,n,26);
  [126,116,116,116,116,126,126,158,452,190].forEach((w,i)=>sheet.setColumnWidth(i+1,w));

  // Kluczowe liczby zostają dokładnie w dotychczasowym kolorowym stylu.

  // PRIORYTETY — przywrócenie czytelnych kolorów wg stanu radaru.
  for (let r=11; r<=15; r++) {
    const status = String(sheet.getRange(r,4).getDisplayValue() || '').toUpperCase();
    const row = sheet.getRange(r,1,1,6);
    if (!String(sheet.getRange(r,2).getDisplayValue() || '').trim()) continue;
    if (status === 'GORĄCO') row.setBackground('#FDE2E2');
    else if (status === 'CHŁODNO') row.setBackground('#E6F0FA');
    else if (status.indexOf('UWAGA') === 0) row.setBackground('#FFF3CD');
    else row.setBackground('#F6FBF8');
    sheet.getRange(r,4).setFontWeight('bold');
  }

  // DO OBSERWACJI — subtelny kolor według sygnału.
  for (let r=11; r<=15; r++) {
    const sym = String(sheet.getRange(r,8).getDisplayValue() || '').trim();
    if (!sym) continue;
    const status = String(sheet.getRange(r,10).getDisplayValue() || '').toUpperCase();
    const row = sheet.getRange(r,8,1,3);
    if (status.indexOf('GORĄCO') >= 0) row.setBackground('#FDE2E2');
    else if (status.indexOf('CHŁODNO') >= 0) row.setBackground('#E6F0FA');
    else if (status.indexOf('UWAGA') >= 0) row.setBackground('#FFF3CD');
    else row.setBackground('#F6FBF8');
  }

  // RADAR 13 ALTÓW — mocniejsze akcenty statusu i ekstremów.
  for (let i=0; i<n; i++) {
    const r = 20 + i;
    const status = String(sheet.getRange(r,8).getDisplayValue() || '').toUpperCase();
    const radarCell = sheet.getRange(r,8);
    if (status === 'GORĄCO') radarCell.setBackground('#FAD1D1').setFontColor('#8F2D2D').setFontWeight('bold');
    else if (status === 'CHŁODNO') radarCell.setBackground('#DDECF8').setFontColor('#245A7A').setFontWeight('bold');
    else if (status.indexOf('UWAGA') === 0) radarCell.setBackground('#FFF0B8').setFontColor('#7A5B00').setFontWeight('bold');
    else radarCell.setBackground('#E5F5EA').setFontColor('#1F6B3A').setFontWeight('bold');

    const fomo = Number(sheet.getRange(r,6).getValue());
    const rsi = Number(sheet.getRange(r,3).getValue());
    const mfi = Number(sheet.getRange(r,4).getValue());
    const macd = String(sheet.getRange(r,5).getDisplayValue() || '').toUpperCase();
    if (fomo >= 8) sheet.getRange(r,6).setBackground('#FAD1D1').setFontWeight('bold');
    if (rsi >= 75 || rsi <= 25) sheet.getRange(r,3).setBackground('#FFF0B8').setFontWeight('bold');
    if (mfi >= 90 || mfi <= 10) sheet.getRange(r,4).setBackground('#FFF0B8').setFontWeight('bold');
    if (macd.indexOf('EKSTREMUM') >= 0) sheet.getRange(r,5).setBackground('#FFE9D6').setFontWeight('bold');
    else if (macd.indexOf('UWAGA') >= 0) sheet.getRange(r,5).setBackground('#EAF4FB').setFontWeight('bold');
  }

  styleMorningRadarButtonsV10_(sheet, morningRadarModeV10_(sheet));
}
'''

p.write_text(s, encoding='utf-8')
print('V10 Morning Radar final polish patched')
