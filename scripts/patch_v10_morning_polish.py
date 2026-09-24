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
    HOT:      {bg:'#FDE2E2', fg:'#8F2D2D'}, // GORĄCO / mocne przegrzanie
    COLD:     {bg:'#E6F0FA', fg:'#245A7A'}, // CHŁODNO
    NEUTRAL:  {bg:'#E5F5EA', fg:'#1F6B3A'}, // NEUTRALNIE
    WARN:     {bg:'#FFF3CD', fg:'#7A5B00'}, // UWAGA / RSI / MFI
    FOMO:     {bg:'#FFE9D6', fg:'#9A4D00'}, // FOMO >= 8
    MACD:     {bg:'#EDF1F5', fg:'#44546A'}, // MACD alert
    INFO:     {bg:'#EAF4FB', fg:'#245A7A'}, // informacyjne
    NORMAL:   {bg:'#F8FBFD', fg:'#243447'}
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

  // Około +5% skali całego pulpitu — zaakceptowany rozmiar.
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

  // TERAZ — KLUCZOWE LICZBY: wzorzec palety, nie zmieniamy układu.
  paintMorningRangeV10_(sheet.getRange('D5:E5'), 'HOT');
  paintMorningRangeV10_(sheet.getRange('F5:G5'), 'COLD');
  paintMorningRangeV10_(sheet.getRange('H5:I5'), 'NEUTRAL');
  paintMorningRangeV10_(sheet.getRange('D6:E6'), 'FOMO');
  paintMorningRangeV10_(sheet.getRange('F6:G6'), 'WARN');
  paintMorningRangeV10_(sheet.getRange('H6:I6'), 'WARN');
  paintMorningRangeV10_(sheet.getRange('D7:E7'), 'MACD');
  paintMorningRangeV10_(sheet.getRange('F7:G7'), 'INFO');
  paintMorningRangeV10_(sheet.getRange('H7:I7'), 'INFO');

  // PRIORYTETY — ten sam stan = ten sam kolor co w kluczowych liczbach.
  for (let r=11; r<=15; r++) {
    const sym = String(sheet.getRange(r,2).getDisplayValue() || '').trim();
    if (!sym) continue;
    const status = String(sheet.getRange(r,4).getDisplayValue() || '');
    const kind = radarKindV10_(status);
    paintMorningRangeV10_(sheet.getRange(r,1,1,6), kind, false);
    paintMorningRangeV10_(sheet.getRange(r,4), kind, true);
  }

  // DO OBSERWACJI — dokładnie ta sama mapa kolorów.
  for (let r=11; r<=15; r++) {
    const sym = String(sheet.getRange(r,8).getDisplayValue() || '').trim();
    if (!sym) continue;
    const status = String(sheet.getRange(r,10).getDisplayValue() || '');
    const kind = radarKindV10_(status);
    paintMorningRangeV10_(sheet.getRange(r,8,1,3), kind, false);
    paintMorningRangeV10_(sheet.getRange(r,10), kind, true);
  }

  // RADAR 13 ALTÓW — wspólna paleta dla RADAR / RSI / MFI / MACD / FOMO.
  for (let i=0; i<n; i++) {
    const r = 20 + i;
    const x = assets[i] || {};

    // Bazowe pasy pozostają subtelne.
    sheet.getRange(r,1,1,9).setBackground(i%2===0 ? '#FFFFFF' : '#F8FBFD').setFontColor('#243447');

    // RADAR: dokładnie jak GORĄCO / CHŁODNO / NEUTRALNIE / UWAGA u góry.
    const kind = radarKindV10_(sheet.getRange(r,8).getDisplayValue());
    paintMorningRangeV10_(sheet.getRange(r,8), kind, true);

    // RSI: ekstremum -> żółty jak RSI EKSTREMUM; normalne bez alarmowego tła.
    const rsi = Number(sheet.getRange(r,3).getValue());
    if (rsi >= 75 || rsi <= 25) paintMorningRangeV10_(sheet.getRange(r,3), 'WARN', true);

    // MFI: ekstremum -> żółty jak MFI EKSTREMUM.
    const mfi = Number(sheet.getRange(r,4).getValue());
    if (mfi >= 90 || mfi <= 10) paintMorningRangeV10_(sheet.getRange(r,4), 'WARN', true);

    // MACD: alert -> szaro-niebieski jak MACD ALERT; ekstremum mocniej, ale ta sama rodzina.
    const macd = String(sheet.getRange(r,5).getDisplayValue() || '').toUpperCase();
    if (macd.indexOf('EKSTREMUM') >= 0) paintMorningRangeV10_(sheet.getRange(r,5), 'MACD', true);
    else if (macd.indexOf('UWAGA') >= 0) paintMorningRangeV10_(sheet.getRange(r,5), 'MACD', true);

    // FOMO >= 8 -> pomarańczowy jak kafel FOMO >= 8.
    const fomo = Number(sheet.getRange(r,6).getValue());
    if (fomo >= 8) paintMorningRangeV10_(sheet.getRange(r,6), 'FOMO', true);
  }

  // Aktywny interwał dalej ma osobne mocne zaznaczenie.
  styleMorningRadarButtonsV10_(sheet, morningRadarModeV10_(sheet));
}
'''

p.write_text(s, encoding='utf-8')
print('V10 Morning Radar unified color logic patched')
