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
// Jeden standard kolorów dla całego Porannego Radaru.
// Wzorzec: blok "TERAZ — KLUCZOWE LICZBY".
function morningPaletteV10_(kind) {
  const p = {
    HOT:      {bg:'#F9D6D6', fg:'#8F2D2D'},
    COLD:     {bg:'#D9EAF7', fg:'#245A7A'},
    NEUTRAL:  {bg:'#DDF1E4', fg:'#1F6B3A'},
    WARN:     {bg:'#FFF0BF', fg:'#7A5B00'},
    FOMO:     {bg:'#FFE4CF', fg:'#9A4D00'},
    MACD:     {bg:'#E5EBF1', fg:'#44546A'},
    INFO:     {bg:'#E2F0F8', fg:'#245A7A'},
    NORMAL:   {bg:'#F2F5F7', fg:'#243447'}
  };
  return p[kind] || p.NORMAL;
}

function paintMorningRangeV10_(range, kind, bold) {
  const c = morningPaletteV10_(kind);
  range.setBackground(c.bg).setFontColor(c.fg);
  if (bold !== false) range.setFontWeight('bold');
  return range;
}

function radarKindV10_(status) {
  const s = String(status || '').toUpperCase();
  if (s.indexOf('GORĄCO') >= 0) return 'HOT';
  if (s.indexOf('CHŁODNO') >= 0) return 'COLD';
  if (s.indexOf('UWAGA') >= 0) return 'WARN';
  if (s.indexOf('NEUTRAL') >= 0) return 'NEUTRAL';
  return 'NORMAL';
}

function polishMorningRadarV10_(sheet, assets) {
  const n = assets.length;

  // Stonowane tło całego widocznego pulpitu zamiast ostrej bieli.
  sheet.getRange(1,1,60,18).setBackground('#EEF3F6').setFontColor('#243447');

  // Około +5% skali całego pulpitu — zaakceptowany rozmiar.
  sheet.getRange(1,1,Math.max(32,19+n),10).setFontSize(11);
  sheet.getRange('A1:J1').setFontSize(18).setBackground('#DCEEF8').setFontColor('#17324D').setFontWeight('bold');
  ['A4:B4','D4:I4','A10:F10','H10:J10','A18:I18','A19:I19'].forEach(a1 => {
    sheet.getRange(a1).setFontSize(12).setBackground('#CFE8F6').setFontColor('#17324D').setFontWeight('bold');
  });
  sheet.getRange('A5:A8').setBackground('#EAF4FB').setFontColor('#243447').setFontWeight('bold');
  sheet.getRange('B5:B8').setBackground('#F7FAFC').setFontColor('#243447').setFontWeight('bold');
  sheet.getRange('A2').setBackground('#EAF4FB').setFontWeight('bold');
  sheet.getRange('F2:J2').setBackground('#F4F7F9').setFontColor('#456276');

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

  // TERAZ — KLUCZOWE LICZBY: wzorzec palety.
  paintMorningRangeV10_(sheet.getRange('D5:E5'), 'HOT');
  paintMorningRangeV10_(sheet.getRange('F5:G5'), 'COLD');
  paintMorningRangeV10_(sheet.getRange('H5:I5'), 'NEUTRAL');
  paintMorningRangeV10_(sheet.getRange('D6:E6'), 'FOMO');
  paintMorningRangeV10_(sheet.getRange('F6:G6'), 'WARN');
  paintMorningRangeV10_(sheet.getRange('H6:I6'), 'WARN');
  paintMorningRangeV10_(sheet.getRange('D7:E7'), 'MACD');
  paintMorningRangeV10_(sheet.getRange('F7:G7'), 'INFO');
  paintMorningRangeV10_(sheet.getRange('H7:I7'), 'INFO');

  // PRIORYTETY — cały wiersz bierze kolor statusu.
  for (let r=11; r<=15; r++) {
    const sym = String(sheet.getRange(r,2).getDisplayValue() || '').trim();
    if (!sym) continue;
    const status = String(sheet.getRange(r,4).getDisplayValue() || '');
    const kind = radarKindV10_(status);
    paintMorningRangeV10_(sheet.getRange(r,1,1,6), kind, false);
    paintMorningRangeV10_(sheet.getRange(r,4), kind, true);
  }

  // DO OBSERWACJI — cały wiersz bierze kolor statusu.
  for (let r=11; r<=15; r++) {
    const sym = String(sheet.getRange(r,8).getDisplayValue() || '').trim();
    if (!sym) continue;
    const status = String(sheet.getRange(r,10).getDisplayValue() || '');
    const kind = radarKindV10_(status);
    paintMorningRangeV10_(sheet.getRange(r,8,1,3), kind, false);
    paintMorningRangeV10_(sheet.getRange(r,10), kind, true);
  }

  // RADAR 13 ALTÓW — cały wiersz dziedziczy kolor statusu RADAR.
  // Potem pojedyncze alarmowe komórki RSI/MFI/MACD/FOMO nadpisują tło.
  for (let i=0; i<n; i++) {
    const r = 20 + i;
    const status = String(sheet.getRange(r,8).getDisplayValue() || '');
    const kind = radarKindV10_(status);

    // Mocniej widoczny kolor całego wiersza A:I.
    paintMorningRangeV10_(sheet.getRange(r,1,1,9), kind, false);
    paintMorningRangeV10_(sheet.getRange(r,8), kind, true);

    const rsi = Number(sheet.getRange(r,3).getValue());
    if (rsi >= 75 || rsi <= 25) paintMorningRangeV10_(sheet.getRange(r,3), 'WARN', true);

    const mfi = Number(sheet.getRange(r,4).getValue());
    if (mfi >= 90 || mfi <= 10) paintMorningRangeV10_(sheet.getRange(r,4), 'WARN', true);

    const macd = String(sheet.getRange(r,5).getDisplayValue() || '').toUpperCase();
    if (macd.indexOf('EKSTREMUM') >= 0 || macd.indexOf('UWAGA') >= 0) {
      paintMorningRangeV10_(sheet.getRange(r,5), 'MACD', true);
    }

    const fomo = Number(sheet.getRange(r,6).getValue());
    if (fomo >= 8) paintMorningRangeV10_(sheet.getRange(r,6), 'FOMO', true);
  }

  styleMorningRadarButtonsV10_(sheet, morningRadarModeV10_(sheet));
}
'''

p.write_text(s, encoding='utf-8')
print('V10 Morning Radar toned canvas and stronger row colors patched')
