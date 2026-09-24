from pathlib import Path

p = Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL_V10.txt')
s = p.read_text(encoding='utf-8')

# Add Morning Radar endpoint next to the accepted Morning Brief constants.
const_old = "const V10_MORNING_SHEET = 'PORANNY_BRIEF';"
const_new = "const V10_MORNING_SHEET = 'PORANNY_BRIEF';\nconst V10_MORNING_RADAR_URL = V8_REPO_RAW + 'morning_radar/MORNING_RADAR.json';"
if 'const V10_MORNING_RADAR_URL' not in s:
    if const_old not in s:
        raise SystemExit('V10 morning sheet constant not found')
    s = s.replace(const_old, const_new, 1)

# Full refresh: fetch radar once and feed the dedicated Brief writer.
needle = "    const metaCsv = fetchText_(V10_META_GATE_URL);"
replacement = "    const metaCsv = fetchText_(V10_META_GATE_URL);\n    const morningRadarJson = JSON.parse(fetchText_(V10_MORNING_RADAR_URL));"
if 'const morningRadarJson = JSON.parse(fetchText_(V10_MORNING_RADAR_URL));' not in s:
    if needle not in s:
        raise SystemExit('ODSWIEZ_WSZYSTKO meta fetch marker not found')
    s = s.replace(needle, replacement, 1)

old_call = "    writeMorningBrief_(ss.getSheetByName(V10_MORNING_SHEET), longJson, tacticalJson, metaCsv);"
new_call = "    writeMorningRadarBrief_(ss.getSheetByName(V10_MORNING_SHEET), morningRadarJson);"
if old_call not in s:
    raise SystemExit('Full refresh Morning Brief call marker not found')
s = s.replace(old_call, new_call, 1)

# Replace only the standalone Morning Brief refresh function.
start = s.find('function ODSWIEZ_PORANNY_BRIEF() {')
end = s.find('\nfunction setupPortfolioLong_', start)
if start < 0 or end < 0:
    raise SystemExit('ODSWIEZ_PORANNY_BRIEF boundaries not found')
new_refresh = r'''function ODSWIEZ_PORANNY_BRIEF() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = getOrCreateSheet_(ss, V10_MORNING_SHEET);
  const radarJson = JSON.parse(fetchText_(V10_MORNING_RADAR_URL));
  writeMorningRadarBrief_(sheet, radarJson);
  ss.toast('Poranny Radar odświeżony — ' + morningRadarModeV10_(sheet), 'V8', 4);
}
'''
s = s[:start] + new_refresh + s[end:]

# Replace setupMorningBrief_ so the selected mode survives every refresh.
start = s.find('function setupMorningBrief_(sheet) {')
end = s.find('\nfunction writeMorningBrief_', start)
if start < 0 or end < 0:
    raise SystemExit('setupMorningBrief_ boundaries not found')
new_setup = r'''function setupMorningBrief_(sheet) {
  let savedMode = String(sheet.getRange('B2').getDisplayValue() || '').trim().toUpperCase();
  if (!['AUTO','1H','2H','4H'].includes(savedMode)) savedMode = 'AUTO';

  sheet.clear();
  sheet.setHiddenGridlines(true);
  sheet.getRange('A1:J1').merge().setValue('V8 / PORANNY RADAR — 1H / 2H / 4H');
  sheet.getRange('A1:J1')
    .setBackground('#DCEEF8').setFontColor('#17324D').setFontWeight('bold')
    .setFontFamily('Roboto').setFontSize(18).setHorizontalAlignment('center').setVerticalAlignment('middle');

  sheet.getRange('A2').setValue('TRYB RADARU');
  sheet.getRange('B2').setValue(savedMode);
  const rule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['AUTO','1H','2H','4H'], true)
    .setAllowInvalid(false)
    .setHelpText('Wybierz interwał Porannego Radaru i uruchom ODŚWIEŻ PORANNY BRIEF.')
    .build();
  sheet.getRange('B2').setDataValidation(rule);
  sheet.getRange('A2:B2').setBackground('#EAF4FB').setFontWeight('bold').setHorizontalAlignment('center');
  sheet.getRange('C2:J2').merge().setValue('AUTO = dla każdego aktywa wybiera najsilniejszy sygnał z 1H / 2H / 4H')
    .setBackground('#F8FBFD').setFontColor('#456276').setHorizontalAlignment('left');

  sheet.getRange('A4:B4').merge().setValue('STAN RADARU');
  sheet.getRange('D4:I4').merge().setValue('TERAZ — KLUCZOWE LICZBY');
  sheet.getRange('A10:F10').merge().setValue('PRIORYTETY — NAJSILNIEJSZE SYGNAŁY');
  sheet.getRange('H10:J10').merge().setValue('DO OBSERWACJI — SYGNAŁY UMIARKOWANE');
  sheet.getRange('A18:I18').merge().setValue('RADAR 13 ALTÓW');
  ['A4:B4','D4:I4','A10:F10','H10:J10','A18:I18'].forEach(a1 => {
    sheet.getRange(a1).setBackground('#CFE8F6').setFontColor('#17324D').setFontWeight('bold')
      .setFontFamily('Roboto').setFontSize(12).setHorizontalAlignment('center').setVerticalAlignment('middle');
  });

  [135,225,150,110,110,110,110,160,480,190].forEach((w,i)=>sheet.setColumnWidth(i+1,w));
  sheet.setFrozenRows(2);
}
'''
s = s[:start] + new_setup + s[end:]

# Append the real 1H / 2H / 4H / AUTO radar renderer. Old writeMorningBrief_ stays as dormant compatibility code.
marker = '// ===== V10 MORNING RADAR 1H 2H 4H AUTO ====='
if marker in s:
    s = s.split(marker)[0].rstrip() + '\n'

radar_js = r'''

// ===== V10 MORNING RADAR 1H 2H 4H AUTO =====
function morningRadarModeV10_(sheet) {
  const v = String(sheet.getRange('B2').getDisplayValue() || 'AUTO').trim().toUpperCase();
  return ['AUTO','1H','2H','4H'].includes(v) ? v : 'AUTO';
}

function morningRadarTfV10_(asset, mode) {
  if (!asset) return {};
  if (mode === 'AUTO') return asset.auto || {};
  return ((asset.timeframes || {})[mode]) || {};
}

function round1V10_(v) {
  const n = Number(v);
  return Number.isFinite(n) ? Math.round(n * 10) / 10 : '';
}

function macdBriefV10_(v) {
  const s = String(v || '').toUpperCase();
  if (s === 'EXTREME_POSITIVE') return 'EKSTREMUM +';
  if (s === 'EXTREME_NEGATIVE') return 'EKSTREMUM −';
  if (s === 'WARNING_POSITIVE') return 'UWAGA +';
  if (s === 'WARNING_NEGATIVE') return 'UWAGA −';
  if (s === 'NO_DATA') return 'BRAK';
  return 'NORMALNY';
}

function writeMorningRadarBrief_(sheet, radarJson) {
  setupMorningBrief_(sheet);
  const mode = morningRadarModeV10_(sheet);
  const assets = (radarJson.assets || []).map(a => {
    const x = morningRadarTfV10_(a, mode);
    return {
      sym: String(a.symbol || ''),
      tf: String(x.timeframe || (mode === 'AUTO' ? (a.auto || {}).timeframe : mode) || ''),
      rsi: round1V10_(x.rsi14),
      mfi: round1V10_(x.mfi14),
      macd: macdBriefV10_(x.macd_extreme_label),
      fomo: Number(x.fomo_score_0_10 || 0),
      trend: Number(x.trend_score_0_4 || 0),
      radar: String(x.radar_status || 'BRAK'),
      intensity: Number(x.radar_intensity_0_10 || 0),
      dir: String(x.radar_direction || 'NEUTRAL'),
      reason: String(x.reason_pl || 'brak skrajności'),
      rsiExtreme: Boolean(x.rsi_extreme),
      mfiExtreme: Boolean(x.mfi_extreme),
      macdAlert: Boolean(x.macd_alert),
      fomoHard: Boolean(x.fomo_hard),
      stale: Boolean(x.stale)
    };
  }).filter(x => x.sym);

  const hot = assets.filter(x => x.dir === 'HOT').length;
  const cold = assets.filter(x => x.dir === 'COLD').length;
  const neutral = assets.filter(x => x.dir === 'NEUTRAL').length;
  const fomoHard = assets.filter(x => x.fomoHard).length;
  const rsiExtreme = assets.filter(x => x.rsiExtreme).length;
  const mfiExtreme = assets.filter(x => x.mfiExtreme).length;
  const macdAlert = assets.filter(x => x.macdAlert).length;
  const stale = assets.filter(x => x.stale).length;
  const avgIntensity = assets.length ? assets.reduce((s,x)=>s+x.intensity,0)/assets.length : 0;

  sheet.getRange('A5:B8').setValues([
    ['Tryb', mode],
    ['Aktywa', assets.length + '/13'],
    ['Dane', stale ? ('STARE: ' + stale) : 'AKTUALNE'],
    ['Transakcje', 'WYŁĄCZONE']
  ]);

  sheet.getRange('D5:I7').setValues([
    ['GORĄCO', hot, 'CHŁODNO', cold, 'NEUTRALNIE', neutral],
    ['FOMO ≥ 8', fomoHard, 'RSI EKSTREMUM', rsiExtreme, 'MFI EKSTREMUM', mfiExtreme],
    ['MACD ALERT', macdAlert, 'ŚR. INTENS.', round1V10_(avgIntensity), 'TRYB', mode]
  ]);

  const priority = assets.slice().sort((a,b)=>(b.intensity-a.intensity)||(b.fomo-a.fomo)).slice(0,5);
  const pRows = priority.map((x,i)=>[i+1,x.sym,x.tf,x.radar,'siła '+x.intensity,'FOMO '+x.fomo]);
  if (pRows.length) sheet.getRange(11,1,pRows.length,6).setValues(pRows);

  const watch = assets.filter(x => x.intensity > 0 && x.intensity < 5)
    .sort((a,b)=>(b.intensity-a.intensity)||(b.fomo-a.fomo)).slice(0,5);
  const wRows = watch.map(x=>[x.sym,x.tf,x.radar+' | siła '+x.intensity]);
  if (wRows.length) sheet.getRange(11,8,wRows.length,3).setValues(wRows);

  sheet.getRange('A19:I19').setValues([['AKTYWO','TF','RSI','MFI','MACD','FOMO','TREND','RADAR','POWÓD']]);
  const detail = assets.map(x=>[x.sym,x.tf,x.rsi,x.mfi,x.macd,x.fomo,x.trend,x.radar,x.reason]);
  if (detail.length) sheet.getRange(20,1,detail.length,9).setValues(detail);

  styleMorningRadarBriefV10_(sheet, assets);
}

function styleMorningRadarBriefV10_(sheet, assets) {
  const n = assets.length;
  const last = Math.max(32, 19+n);
  sheet.setHiddenGridlines(true);
  sheet.getRange(1,1,last,10).setFontFamily('Roboto').setFontSize(10).setFontColor('#243447').setVerticalAlignment('middle');
  sheet.getRange('A1:J1').setFontSize(17).setBackground('#DCEEF8').setFontColor('#17324D').setFontWeight('bold').setHorizontalAlignment('center');
  sheet.setRowHeight(1,34);

  ['A4:B4','D4:I4','A10:F10','H10:J10','A18:I18','A19:I19'].forEach(a1 => {
    sheet.getRange(a1).setBackground('#CFE8F6').setFontColor('#17324D').setFontWeight('bold').setHorizontalAlignment('center');
  });

  sheet.getRange('A5:A8').setBackground('#EAF4FB').setFontWeight('bold').setHorizontalAlignment('center');
  sheet.getRange('B5:B8').setBackground('#F8FBFD').setFontWeight('bold').setHorizontalAlignment('center');
  styleBriefCardV10_(sheet.getRange('D5:E5'), '#FDE2E2', '#8F2D2D');
  styleBriefCardV10_(sheet.getRange('F5:G5'), '#E6F0FA', '#245A7A');
  styleBriefCardV10_(sheet.getRange('H5:I5'), '#E5F5EA', '#1F6B3A');
  styleBriefCardV10_(sheet.getRange('D6:E6'), '#FFE9D6', '#9A4D00');
  styleBriefCardV10_(sheet.getRange('F6:G6'), '#FFF3CD', '#7A5B00');
  styleBriefCardV10_(sheet.getRange('H6:I6'), '#FFF3CD', '#7A5B00');
  styleBriefCardV10_(sheet.getRange('D7:E7'), '#EDF1F5', '#44546A');
  styleBriefCardV10_(sheet.getRange('F7:G7'), '#EAF4FB', '#245A7A');
  styleBriefCardV10_(sheet.getRange('H7:I7'), '#EAF4FB', '#245A7A');

  sheet.getRange('A11:F15').setBackground('#FFFFFF').setHorizontalAlignment('center');
  sheet.getRange('H11:J15').setBackground('#F8FBFD').setHorizontalAlignment('center');
  if (n) {
    sheet.getRange(20,1,n,8).setHorizontalAlignment('center');
    sheet.getRange(20,9,n,1).setHorizontalAlignment('left').setWrap(false);
    for (let i=0; i<n; i++) {
      const r = 20+i;
      const x = assets[i];
      sheet.getRange(r,1,1,9).setBackground(i%2===0 ? '#FFFFFF' : '#F8FBFD');
      const rc = sheet.getRange(r,8);
      if (x.radar === 'GORĄCO') rc.setBackground('#FAD1D1').setFontColor('#8F2D2D').setFontWeight('bold');
      else if (x.radar === 'CHŁODNO') rc.setBackground('#DDECF8').setFontColor('#245A7A').setFontWeight('bold');
      else if (x.radar.indexOf('UWAGA') === 0) rc.setBackground('#FFF0B8').setFontColor('#7A5B00').setFontWeight('bold');
      else rc.setBackground('#E5F5EA').setFontColor('#1F6B3A');
      if (x.fomo >= 8) sheet.getRange(r,6).setBackground('#FAD1D1').setFontWeight('bold');
      if (Number(x.rsi) >= 75 || Number(x.rsi) <= 25) sheet.getRange(r,3).setBackground('#FFF0B8').setFontWeight('bold');
      if (Number(x.mfi) >= 90 || Number(x.mfi) <= 10) sheet.getRange(r,4).setBackground('#FFF0B8').setFontWeight('bold');
    }
  }

  ['A4:B8','D4:I7','A10:F15','H10:J15','A18:I19'].forEach(a1 => {
    sheet.getRange(a1).setBorder(true,true,true,true,true,true,'#B9D4E5',SpreadsheetApp.BorderStyle.SOLID);
  });
  if (n) sheet.getRange(19,1,n+1,9).setBorder(true,true,true,true,true,true,'#D5E3EC',SpreadsheetApp.BorderStyle.SOLID);

  // Compact vertical layout: all 13 alts should fit on a normal desktop view.
  for (let r=4; r<=8; r++) sheet.setRowHeight(r,24);
  sheet.setRowHeight(10,26);
  for (let r=11; r<=15; r++) sheet.setRowHeight(r,23);
  sheet.setRowHeight(18,26);
  sheet.setRowHeight(19,25);
  for (let r=20; r<=19+n; r++) sheet.setRowHeight(r,21);
}
'''

s = s.rstrip() + radar_js + '\n'
p.write_text(s, encoding='utf-8')
print('Patched V10 Poranny Brief -> Morning Radar 1H/2H/4H/AUTO')
