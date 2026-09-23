from pathlib import Path

SRC = Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL_V9.txt')
DST = Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL_V10.txt')

base = SRC.read_text(encoding='utf-8')
marker = '// ===== V10 ACCEPTED PANELS PACK — TACTICAL + PORANNY BRIEF + PORTFEL LONG ====='
if marker in base:
    base = base.split(marker)[0].rstrip() + '\n\n'

append = r'''
// ===== V10 ACCEPTED PANELS PACK — TACTICAL + PORANNY BRIEF + PORTFEL LONG =====
// Fizyczne trzy zaakceptowane widoki użytkownika.
// V7 pozostaje nietknięty. Brak automatycznego wykonywania transakcji.

const V10_META_GATE_URL = V8_REPO_RAW + 'tactical_validation/TACTICAL_META_GATE_CURRENT.csv';
const V10_MORNING_SHEET = 'PORANNY_BRIEF';

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('V8 DUAL ENGINE')
    .addItem('ODŚWIEŻ_WSZYSTKO', 'ODSWIEZ_WSZYSTKO')
    .addItem('ODŚWIEŻ PORANNY BRIEF', 'ODSWIEZ_PORANNY_BRIEF')
    .addItem('ODŚWIEŻ ETF BTC / ETH', 'ODSWIEZ_ETF_BTC_ETH')
    .addItem('ODŚWIEŻ LAB — ANALIZA AKTYWA', 'ODSWIEZ_LAB')
    .addItem('SPRAWDŹ EKSTREMA', 'SPRAWDZ_EKSTREMA')
    .addSeparator()
    .addItem('UTWÓRZ / NAPRAW UKŁAD', 'V8_SETUP')
    .addToUi();
}

function V8_SETUP() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  Object.values(V8_SHEETS).forEach(name => getOrCreateSheet_(ss, name));
  getOrCreateSheet_(ss, V10_MORNING_SHEET);
  setupPortfolioLong_(ss.getSheetByName(V8_SHEETS.portfolioLong));
  setupPortfolioTactical_(ss.getSheetByName(V8_SHEETS.portfolioTactical));
  setupMorningBrief_(ss.getSheetByName(V10_MORNING_SHEET));
  setupSettings_(ss.getSheetByName(V8_SHEETS.settings));
  setupExtremes_(ss.getSheetByName(V8_SHEETS.extremes));
  formatPanel_(ss.getSheetByName(V8_SHEETS.panel));
  ss.toast('Układ V8 gotowy — Tactical + Poranny Brief + Portfel LONG', 'V8', 4);
}

function ODSWIEZ_WSZYSTKO() {
  const lock = LockService.getDocumentLock();
  if (!lock.tryLock(1000)) throw new Error('Odświeżanie już trwa.');
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    V8_SETUP();

    const oldPanel = readPanelState_(ss.getSheetByName(V8_SHEETS.panel));
    const oldAlarms = readActiveExtremeKeys_(ss.getSheetByName(V8_SHEETS.extremes));

    const panelCsv = fetchText_(V8_FILES.panel);
    const machineCsv = fetchText_(V8_FILES.machine);
    const longJson = JSON.parse(fetchText_(V8_FILES.long));
    const tacticalJson = JSON.parse(fetchText_(V8_FILES.tactical));
    const readinessJson = JSON.parse(fetchText_(V8_FILES.tacticalReadiness));
    const phaseJson = JSON.parse(fetchText_(V8_FILES.marketPhase));
    const snapshotJson = JSON.parse(fetchText_(V8_FILES.snapshot));
    const labJson = JSON.parse(fetchText_(V8_FILES.labReport));
    const etfStatusJson = JSON.parse(fetchText_(V8_FILES.etfStatus));
    const etfHistoryCsv = fetchText_(V8_FILES.etfHistoryCsv);
    const etfConfirmationJson = JSON.parse(fetchText_(V8_FILES.etfConfirmation));
    const mrCsv = fetchText_(V8_FILES.marketReader);
    const metaCsv = fetchText_(V10_META_GATE_URL);

    writePolishPanel_(ss.getSheetByName(V8_SHEETS.panel), panelCsv);
    writeLongEngine_(ss.getSheetByName(V8_SHEETS.long), longJson);
    writeTacticalEngine_(ss.getSheetByName(V8_SHEETS.tactical), tacticalJson, readinessJson, phaseJson);
    writeFlowEngine_(ss.getSheetByName(V8_SHEETS.flow), phaseJson, snapshotJson);
    writeEtfPanel_(ss.getSheetByName(V8_SHEETS.etf), etfStatusJson, etfConfirmationJson);
    writeEtfHistory_(ss.getSheetByName(V8_SHEETS.etfHistory), etfHistoryCsv);
    writeLabPanel_(ss.getSheetByName(V8_SHEETS.lab), labJson);
    writeCsvSheet_(ss.getSheetByName(V8_SHEETS.marketReader), mrCsv, false);

    writeLongDashboard_(ss.getSheetByName(V8_SHEETS.portfolioLong), longJson);
    writeTacticalDashboard_(ss.getSheetByName(V8_SHEETS.portfolioTactical), tacticalJson, metaCsv);
    writeMorningBrief_(ss.getSheetByName(V10_MORNING_SHEET), longJson, tacticalJson, metaCsv);

    const machineSheet = getOrCreateSheet_(ss, 'DANE_MASZYNOWNIA');
    writeCsvSheet_(machineSheet, machineCsv, false);
    machineSheet.hideSheet();

    const alarms = buildExtremeAlarms_(ss, tacticalJson);
    writeExtremeAlarms_(ss.getSheetByName(V8_SHEETS.extremes), alarms);
    updateMainPanelExtremeSummary_(ss.getSheetByName(V8_SHEETS.panel), alarms);
    appendExtremeHistory_(ss, oldAlarms, alarms);
    notifyNewExtremeAlarms_(ss, oldAlarms, alarms);

    formatPanel_(ss.getSheetByName(V8_SHEETS.panel));
    appendHistoryOnChanges_(ss, oldPanel, readPanelState_(ss.getSheetByName(V8_SHEETS.panel)));
    stampRefresh_(ss);

    const active = alarms.filter(a => a.aktywny).length;
    ss.toast('V8 odświeżony. 3 panele gotowe. Aktywne ekstrema: ' + active, 'V8 DUAL ENGINE', 5);
  } finally {
    lock.releaseLock();
  }
}

function ODSWIEZ_PORANNY_BRIEF() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  V8_SETUP();
  const longJson = JSON.parse(fetchText_(V8_FILES.long));
  const tacticalJson = JSON.parse(fetchText_(V8_FILES.tactical));
  const metaCsv = fetchText_(V10_META_GATE_URL);
  writeMorningBrief_(ss.getSheetByName(V10_MORNING_SHEET), longJson, tacticalJson, metaCsv);
  ss.toast('Poranny Brief odświeżony', 'V8', 4);
}

function setupPortfolioLong_(sheet) {
  sheet.clear();
  sheet.getRange('A1:J1').merge().setValue('V8 / PORTFEL LONG — DŁUGI HORYZONT + STREFY DCA');
  styleTitleV10_(sheet.getRange('A1:J1'));
  sheet.getRange('A3:J3').setValues([['AKTYWO','JAKOŚĆ','STATUS','STREFY','TREND','FOMO','DECYZJA','DCA1','DCA2','DCA3']]);
  styleHeaderV10_(sheet.getRange('A3:J3'));
  sheet.setFrozenRows(3);
  [90,80,130,220,75,75,165,105,105,105].forEach((w,i)=>sheet.setColumnWidth(i+1,w));
}

function writeLongDashboard_(sheet, data) {
  setupPortfolioLong_(sheet);
  const rows = (data.assets || []).map(a => [
    a.symbol,
    a.data_quality,
    translateReady_(a.readiness_status),
    a.zone_timeframes,
    a.trend_score_0_4,
    a.fomo_score_0_10,
    translateLong_(a.decision),
    valueOrBlank_(a.dca1),
    valueOrBlank_(a.dca2),
    valueOrBlank_(a.dca3)
  ]);
  if (rows.length) sheet.getRange(4,1,rows.length,10).setValues(rows);
  const end = Math.max(4, rows.length + 3);
  sheet.getRange(4,1,Math.max(1,rows.length),10).setWrap(true).setVerticalAlignment('middle');
  sheet.getRange(4,2,Math.max(1,rows.length),1).setNumberFormat('0');
  sheet.getRange(4,5,Math.max(1,rows.length),2).setNumberFormat('0.0');
  sheet.getRange(4,8,Math.max(1,rows.length),3).setNumberFormat('0.########');
  applyLongColorsV10_(sheet, 4, end);
}

function setupPortfolioTactical_(sheet) {
  sheet.clear();
  sheet.getRange('A1:I1').merge().setValue('V8 / PANEL TAKTYCZNY — SZYBKIE ZAGRANIA 1H / 4H / 1D');
  styleTitleV10_(sheet.getRange('A1:I1'));
  sheet.getRange('A3:I3').setValues([['AKTYWO','STATUS PRODUKCYJNY','DECYZJA META','RYZYKO','RYZYKO WYJŚCIA','FOMO','PRZEGRZANIE','KANDYDAT','POWÓD']]);
  styleHeaderV10_(sheet.getRange('A3:I3'));
  sheet.setFrozenRows(3);
  [90,170,190,85,110,75,105,90,430].forEach((w,i)=>sheet.setColumnWidth(i+1,w));
}

function writeTacticalDashboard_(sheet, tacticalJson, metaCsv) {
  setupPortfolioTactical_(sheet);
  const meta = parseMetaCsvV10_(metaCsv);
  const tacticalMap = {};
  (tacticalJson.assets || []).forEach(a => tacticalMap[String(a.symbol)] = a);
  const rows = [];
  Object.keys(meta).forEach(sym => {
    if (sym === 'BTC') return;
    const m = meta[sym];
    const t = tacticalMap[sym] || {};
    rows.push([
      sym,
      translateTactical_(m.prod_status || t.tactical_status || ''),
      translateMetaV10_(m.meta_decision || ''),
      numV10_(m.risk_score, t.exit_risk_0_10),
      numV10_(m.exit_risk, t.exit_risk_0_10),
      numV10_(m.max_fomo, maxFomoV10_(t)),
      numV10_(m.overheat_score, 0),
      yesNoV10_(m.challenger_candidate),
      translateReasonV10_(m.reason || '')
    ]);
  });
  if (rows.length) sheet.getRange(4,1,rows.length,9).setValues(rows);
  sheet.getRange(4,1,Math.max(1,rows.length),9).setWrap(true).setVerticalAlignment('middle');
  applyTacticalColorsV10_(sheet, 4, rows.length + 3);
}

function setupMorningBrief_(sheet) {
  sheet.clear();
  sheet.getRange('A1:J1').merge().setValue('V8 / PORANNY BRIEF — 30 SEKUND DO OBRAZU RYNKU');
  styleTitleV10_(sheet.getRange('A1:J1'));
  sheet.getRange('A3:B8').setValues([
    ['STAN SYSTEMU',''],
    ['Produkcja','ZAMKNIĘTY — STABILNY'],
    ['Badania','WSTRZYMANE'],
    ['Reżim rynku','—'],
    ['Automatyczne transakcje','WYŁĄCZONE'],
    ['Strefy LONG','91/91']
  ]);
  sheet.getRange('D3:I3').merge().setValue('DZISIAJ — KLUCZOWE LICZBY');
  styleHeaderV10_(sheet.getRange('D3:I3'));
  sheet.getRange('A10:F10').merge().setValue('PRIORYTETY NA DZIŚ');
  styleHeaderV10_(sheet.getRange('A10:F10'));
  sheet.getRange('H10:J10').merge().setValue('DO OBSERWACJI — BEZ BLOKADY');
  styleHeaderV10_(sheet.getRange('H10:J10'));
  sheet.getRange('A18:I18').merge().setValue('TAKTYCZNY OBRAZ 13 ALTÓW');
  styleHeaderV10_(sheet.getRange('A18:I18'));
  [95,165,180,85,105,75,100,90,410,120].forEach((w,i)=>sheet.setColumnWidth(i+1,w));
  sheet.setFrozenRows(1);
}

function writeMorningBrief_(sheet, longJson, tacticalJson, metaCsv) {
  setupMorningBrief_(sheet);
  const meta = parseMetaCsvV10_(metaCsv);
  const tacticalMap = {};
  (tacticalJson.assets || []).forEach(a => tacticalMap[String(a.symbol)] = a);
  const entries = Object.keys(meta).filter(s => s !== 'BTC').map(sym => {
    const m = meta[sym], t=tacticalMap[sym] || {};
    return {
      sym:sym,
      status:translateTactical_(m.prod_status || t.tactical_status || ''),
      meta:translateMetaV10_(m.meta_decision || ''),
      risk:numV10_(m.risk_score, t.exit_risk_0_10),
      exit:numV10_(m.exit_risk, t.exit_risk_0_10),
      fomo:numV10_(m.max_fomo, maxFomoV10_(t)),
      heat:numV10_(m.overheat_score, 0),
      cand:yesNoV10_(m.challenger_candidate),
      reason:translateReasonV10_(m.reason || '')
    };
  });
  const regime = entries.length && meta[entries[0].sym] ? translateRegimeV10_(meta[entries[0].sym].regime_gate || '') : '—';
  sheet.getRange('B6').setValue(regime);

  const counts = {ZEZWOL:0, OSTROZNIE:0, BLOKUJ:0, WSTRZYMAJ:0};
  entries.forEach(e => {
    if (e.meta === 'ZEZWÓL') counts.ZEZWOL++;
    else if (e.meta === 'OSTROŻNIE') counts.OSTROZNIE++;
    else if (e.meta === 'BLOKUJ') counts.BLOKUJ++;
    else counts.WSTRZYMAJ++;
  });
  const avgRisk = entries.length ? entries.reduce((s,e)=>s+Number(e.risk||0),0)/entries.length : 0;
  sheet.getRange('D4:I6').setValues([
    ['ZEZWÓL',counts.ZEZWOL,'OSTROŻNIE',counts.OSTROZNIE,'BLOKUJ',counts.BLOKUJ],
    ['WSTRZYMAJ',counts.WSTRZYMAJ,'ŚR. RYZYKO',Math.round(avgRisk*10)/10,'FOMO ≥ 8',entries.filter(e=>e.fomo>=8).length],
    ['PRZEGRZANIE ≥ 3',entries.filter(e=>e.heat>=3).length,'BEZ TRANSAKCJI',entries.filter(e=>e.status==='NIE GRAJ').length,'OBSERWUJ PODAŻ',entries.filter(e=>e.status==='OBSERWUJ PODAŻ').length]
  ]);

  const priorities = entries.slice().sort((a,b)=>(b.risk-a.risk)||(b.fomo-a.fomo)).slice(0,5);
  const prRows = priorities.map((e,i)=>[i+1,e.sym,e.meta,'ryzyko '+e.risk,'FOMO '+e.fomo,'przegrzanie '+e.heat]);
  if (prRows.length) sheet.getRange(11,1,prRows.length,6).setValues(prRows);

  const watch = entries.filter(e=>e.meta==='OSTROŻNIE').sort((a,b)=>a.risk-b.risk).slice(0,5);
  const watchRows = watch.map(e=>[e.sym,e.meta,'ryzyko '+e.risk+' | FOMO '+e.fomo]);
  if (watchRows.length) sheet.getRange(11,8,watchRows.length,3).setValues(watchRows);

  sheet.getRange('A19:I19').setValues([['AKTYWO','STATUS','META','RYZYKO','WYJŚCIE','FOMO','PRZEGRZ.','KANDYDAT','POWÓD']]);
  styleHeaderV10_(sheet.getRange('A19:I19'));
  const detail = entries.map(e=>[e.sym,e.status,e.meta,e.risk,e.exit,e.fomo,e.heat,e.cand,e.reason]);
  if (detail.length) sheet.getRange(20,1,detail.length,9).setValues(detail);
  sheet.getRange(3,1,Math.max(1,detail.length+17),10).setWrap(true).setVerticalAlignment('middle');
  applyTacticalColorsV10_(sheet, 20, detail.length + 19);
}

function parseMetaCsvV10_(csvText) {
  const rows = Utilities.parseCsv(csvText || '');
  if (!rows.length) return {};
  const head = rows[0].map(x=>String(x).trim());
  const out = {};
  rows.slice(1).forEach(r => {
    const obj = {}; head.forEach((h,i)=>obj[h]=r[i]);
    const sym = String(obj.symbol || obj.AKTYWO || '').trim();
    if (sym) out[sym] = obj;
  });
  return out;
}

function translateMetaV10_(v) {
  const m = {'ALLOW':'ZEZWÓL','CAUTION':'OSTROŻNIE','BLOCK':'BLOKUJ','HOLD_CHALLENGER':'WSTRZYMAJ KANDYDATA'};
  return m[String(v||'').toUpperCase()] || String(v||'').replaceAll('_',' ');
}
function translateRegimeV10_(v) {
  const m={'ACTIVE':'AKTYWNY','CAUTION':'OSTROŻNY','BLOCK':'BLOKADA'};
  return m[String(v||'').toUpperCase()] || String(v||'').replaceAll('_',' ');
}
function translateReasonV10_(v) {
  return String(v||'')
    .replaceAll('exit risk>=6','ryzyko wyjścia ≥ 6')
    .replaceAll('exit risk>=4','ryzyko wyjścia ≥ 4')
    .replaceAll('status SUPPLY','status: podaż')
    .replaceAll('status NO_TRADE','status: bez transakcji')
    .replaceAll('FOMO>=8','FOMO ≥ 8')
    .replaceAll('FOMO>=6','FOMO ≥ 6');
}
function maxFomoV10_(a) {
  const t=(a||{}).timeframes||{};
  return Math.max(0, Number((t['1H']||{}).fomo_score_0_10||0), Number((t['4H']||{}).fomo_score_0_10||0), Number((t['1D']||{}).fomo_score_0_10||0));
}
function numV10_(a,b) { const n=Number(a); if (Number.isFinite(n)) return n; const m=Number(b); return Number.isFinite(m)?m:0; }
function yesNoV10_(v) { const s=String(v||'').toLowerCase(); return ['true','1','yes','tak'].includes(s) ? 'TAK' : 'NIE'; }

function styleTitleV10_(range) {
  range.setBackground('#0f172a').setFontColor('#ffffff').setFontWeight('bold').setFontSize(16).setHorizontalAlignment('center').setVerticalAlignment('middle');
}
function styleHeaderV10_(range) {
  range.setBackground('#1e293b').setFontColor('#ffffff').setFontWeight('bold').setHorizontalAlignment('center').setVerticalAlignment('middle');
}
function applyLongColorsV10_(sheet,startRow,endRow) {
  if (endRow < startRow) return;
  for (let r=startRow;r<=endRow;r++) {
    const f=Number(sheet.getRange(r,6).getValue()||0);
    const d=String(sheet.getRange(r,7).getValue()||'');
    sheet.getRange(r,1,1,10).setBackground(r%2===0?'#ffffff':'#f8fafc');
    if (f>=8) sheet.getRange(r,6).setBackground('#fee2e2').setFontColor('#991b1b').setFontWeight('bold');
    else if (f>=6) sheet.getRange(r,6).setBackground('#fef3c7').setFontColor('#92400e').setFontWeight('bold');
    else sheet.getRange(r,6).setBackground('#dcfce7').setFontColor('#166534');
    if (d.indexOf('FOMO')>=0) sheet.getRange(r,7).setBackground('#fee2e2').setFontColor('#991b1b').setFontWeight('bold');
    sheet.getRange(r,8,1,3).setBackground('#eff6ff');
  }
}
function applyTacticalColorsV10_(sheet,startRow,endRow) {
  if (endRow < startRow) return;
  for (let r=startRow;r<=endRow;r++) {
    const meta=String(sheet.getRange(r,3).getValue()||'');
    const risk=Number(sheet.getRange(r,4).getValue()||0);
    sheet.getRange(r,1,1,Math.min(9,sheet.getLastColumn())).setBackground(r%2===0?'#ffffff':'#f8fafc');
    if (meta==='BLOKUJ') sheet.getRange(r,3).setBackground('#fecaca').setFontColor('#991b1b').setFontWeight('bold');
    else if (meta==='OSTROŻNIE') sheet.getRange(r,3).setBackground('#fef3c7').setFontColor('#92400e').setFontWeight('bold');
    else if (meta.indexOf('WSTRZYMAJ')>=0) sheet.getRange(r,3).setBackground('#e5e7eb').setFontColor('#374151').setFontWeight('bold');
    else if (meta==='ZEZWÓL') sheet.getRange(r,3).setBackground('#dcfce7').setFontColor('#166534').setFontWeight('bold');
    if (risk>=7) sheet.getRange(r,4).setBackground('#fecaca').setFontWeight('bold');
    else if (risk>=4) sheet.getRange(r,4).setBackground('#fef3c7');
    else sheet.getRange(r,4).setBackground('#dcfce7');
  }
}
'''

DST.write_text(base.rstrip() + '\n\n' + append.strip() + '\n', encoding='utf-8')
print(f'Wrote {DST} ({DST.stat().st_size} bytes)')
