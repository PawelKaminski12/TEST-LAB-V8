from pathlib import Path

p = Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL_V10.txt')
s = p.read_text(encoding='utf-8')

const_old = "const V10_MORNING_SHEET = 'PORANNY_BRIEF';"
const_new = "const V10_MORNING_SHEET = 'PORANNY_BRIEF';\nconst V10_MORNING_RADAR_URL = V8_REPO_RAW + 'morning_radar/MORNING_RADAR.json';"
if 'const V10_MORNING_RADAR_URL' not in s:
    s = s.replace(const_old, const_new, 1)

needle = "    const metaCsv = fetchText_(V10_META_GATE_URL);"
replacement = "    const metaCsv = fetchText_(V10_META_GATE_URL);\n    const morningRadarJson = JSON.parse(fetchText_(V10_MORNING_RADAR_URL));"
if 'const morningRadarJson = JSON.parse(fetchText_(V10_MORNING_RADAR_URL));' not in s:
    s = s.replace(needle, replacement, 1)

old_call = "    writeMorningBrief_(ss.getSheetByName(V10_MORNING_SHEET), longJson, tacticalJson, metaCsv);"
new_call = "    writeMorningRadarBrief_(ss.getSheetByName(V10_MORNING_SHEET), morningRadarJson);"
if old_call in s:
    s = s.replace(old_call, new_call, 1)

start = s.find('function ODSWIEZ_PORANNY_BRIEF() {')
end = s.find('\nfunction setupPortfolioLong_', start)
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

start = s.find('function setupMorningBrief_(sheet) {')
end = s.find('\nfunction writeMorningBrief_', start)
new_setup = r'''function setupMorningBrief_(sheet) {
  let savedMode = String(sheet.getRange('K1').getDisplayValue() || '').trim().toUpperCase();
  if (!['1H','2H','4H','AUTO'].includes(savedMode)) savedMode = '1H';

  sheet.getRange(1,1,sheet.getMaxRows(),sheet.getMaxColumns()).breakApart();
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

marker = '// ===== V10 MORNING RADAR 1H 2H 4H AUTO ====='
if marker in s:
    s = s.split(marker)[0].rstrip() + '\n'

radar_js = r'''

// ===== V10 MORNING RADAR 1H 2H 4H AUTO =====
function morningRadarModeV10_(sheet) {
  const v = String(sheet.getRange('K1').getDisplayValue() || '1H').trim().toUpperCase();
  return ['1H','2H','4H','AUTO'].includes(v) ? v : '1H';
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
  const sourceAssets = (radarJson && radarJson.assets) || [];
  if (sourceAssets.length !== 13) throw new Error('Poranny Radar: niepełne dane ' + sourceAssets.length + '/13. Arkusz pozostawiono bez zmian.');
  const mode = morningRadarModeV10_(sheet);
  const assets = sourceAssets.map(a => {
    const x = morningRadarTfV10_(a, mode);
    return {
      sym:String(a.symbol || ''), tf:String(x.timeframe || (mode === 'AUTO' ? (a.auto || {}).timeframe : mode) || ''),
      rsi:round1V10_(x.rsi14), mfi:round1V10_(x.mfi14), macd:macdBriefV10_(x.macd_extreme_label),
      fomo:Number(x.fomo_score_0_10 || 0), trend:Number(x.trend_score_0_4 || 0), radar:String(x.radar_status || 'BRAK'),
      intensity:Number(x.radar_intensity_0_10 || 0), dir:String(x.radar_direction || 'NEUTRAL'), reason:String(x.reason_pl || 'brak skrajności'),
      rsiExtreme:Boolean(x.rsi_extreme), mfiExtreme:Boolean(x.mfi_extreme), macdAlert:Boolean(x.macd_alert), fomoHard:Boolean(x.fomo_hard), stale:Boolean(x.stale)
    };
  }).filter(x => x.sym);
  if (assets.length !== 13) throw new Error('Poranny Radar: po walidacji ' + assets.length + '/13. Arkusz pozostawiono bez zmian.');

  setupMorningBrief_(sheet);

  const hot=assets.filter(x=>x.dir==='HOT').length, cold=assets.filter(x=>x.dir==='COLD').length, neutral=assets.filter(x=>x.dir==='NEUTRAL').length;
  const fomoHard=assets.filter(x=>x.fomoHard).length, rsiExtreme=assets.filter(x=>x.rsiExtreme).length, mfiExtreme=assets.filter(x=>x.mfiExtreme).length;
  const macdAlert=assets.filter(x=>x.macdAlert).length, stale=assets.filter(x=>x.stale).length;
  const avgIntensity=assets.reduce((s,x)=>s+x.intensity,0)/assets.length;

  sheet.getRange('A5:B8').setValues([['Tryb',mode],['Aktywa','13/13'],['Dane',stale?('STARE: '+stale):'AKTUALNE'],['Transakcje','WYŁĄCZONE']]);
  sheet.getRange('D5:I7').setValues([
    ['GORĄCO',hot,'CHŁODNO',cold,'NEUTRALNIE',neutral],
    ['FOMO ≥ 8',fomoHard,'RSI EKSTREMUM',rsiExtreme,'MFI EKSTREMUM',mfiExtreme],
    ['MACD ALERT',macdAlert,'ŚR. INTENS.',round1V10_(avgIntensity),'TRYB',mode]
  ]);

  const priority=assets.slice().sort((a,b)=>(b.intensity-a.intensity)||(b.fomo-a.fomo)).slice(0,5);
  sheet.getRange(11,1,priority.length,6).setValues(priority.map((x,i)=>[i+1,x.sym,x.tf,x.radar,'siła '+x.intensity,'FOMO '+x.fomo]));
  const watch=assets.filter(x=>x.intensity>0&&x.intensity<5).sort((a,b)=>(b.intensity-a.intensity)||(b.fomo-a.fomo)).slice(0,5);
  if (watch.length) sheet.getRange(11,8,watch.length,3).setValues(watch.map(x=>[x.sym,x.tf,x.radar+' | siła '+x.intensity]));
  sheet.getRange('A19:I19').setValues([['AKTYWO','TF','RSI','MFI','MACD','FOMO','TREND','RADAR','POWÓD']]);
  sheet.getRange(20,1,assets.length,9).setValues(assets.map(x=>[x.sym,x.tf,x.rsi,x.mfi,x.macd,x.fomo,x.trend,x.radar,x.reason]));
  SpreadsheetApp.flush();
  styleMorningRadarBriefV10_(sheet, assets);
}

function styleMorningRadarBriefV10_(sheet, assets) {
  const n=assets.length, last=Math.max(32,19+n);
  sheet.setHiddenGridlines(true);
  sheet.getRange(1,1,last,10).setFontFamily('Roboto').setFontSize(10).setFontColor('#243447').setVerticalAlignment('middle');
  sheet.getRange('A1:J1').setFontSize(17).setBackground('#DCEEF8').setFontColor('#17324D').setFontWeight('bold').setHorizontalAlignment('center');
  ['A4:B4','D4:I4','A10:F10','H10:J10','A18:I18','A19:I19'].forEach(a1=>sheet.getRange(a1).setBackground('#CFE8F6').setFontColor('#17324D').setFontWeight('bold').setHorizontalAlignment('center'));
  sheet.getRange('A5:A8').setBackground('#EAF4FB').setFontWeight('bold').setHorizontalAlignment('center');
  sheet.getRange('B5:B8').setBackground('#F8FBFD').setFontWeight('bold').setHorizontalAlignment('center');
  styleBriefCardV10_(sheet.getRange('D5:E5'),'#FDE2E2','#8F2D2D');
  styleBriefCardV10_(sheet.getRange('F5:G5'),'#E6F0FA','#245A7A');
  styleBriefCardV10_(sheet.getRange('H5:I5'),'#E5F5EA','#1F6B3A');
  styleBriefCardV10_(sheet.getRange('D6:E6'),'#FFE9D6','#9A4D00');
  styleBriefCardV10_(sheet.getRange('F6:G6'),'#FFF3CD','#7A5B00');
  styleBriefCardV10_(sheet.getRange('H6:I6'),'#FFF3CD','#7A5B00');
  styleBriefCardV10_(sheet.getRange('D7:E7'),'#EDF1F5','#44546A');
  styleBriefCardV10_(sheet.getRange('F7:G7'),'#EAF4FB','#245A7A');
  styleBriefCardV10_(sheet.getRange('H7:I7'),'#EAF4FB','#245A7A');
  styleMorningRadarBriefV10_(sheet, assets);
}
'''

# Fix accidental recursion by replacing the final recursive call with the original styling body marker consumed by later polish patch.
radar_js = radar_js.replace("  styleMorningRadarBriefV10_(sheet, assets);\n}\n'''.strip() if False else '___NEVER___', '')
# Replace the trailing recursive call directly in the JS string.
radar_js = radar_js.replace("  styleMorningRadarBriefV10_(sheet, assets);\n}\n", "  sheet.getRange('A11:F15').setHorizontalAlignment('center');\n  sheet.getRange('H11:J15').setHorizontalAlignment('center');\n  if (n) { sheet.getRange(20,1,n,8).setHorizontalAlignment('center'); sheet.getRange(20,9,n,1).setHorizontalAlignment('left').setWrap(false); }\n  ['A4:B8','D4:I7','A10:F15','H10:J15','A18:I19'].forEach(a1=>sheet.getRange(a1).setBorder(true,true,true,true,true,true,'#B9D4E5',SpreadsheetApp.BorderStyle.SOLID));\n  if (n) sheet.getRange(19,1,n+1,9).setBorder(true,true,true,true,true,true,'#D5E3EC',SpreadsheetApp.BorderStyle.SOLID);\n}\n")

s += radar_js
p.write_text(s, encoding='utf-8')
print('V10 Morning Radar fail-safe renderer applied')
