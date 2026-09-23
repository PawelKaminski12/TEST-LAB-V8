from pathlib import Path
import re

p = Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL.txt')
s = p.read_text(encoding='utf-8')

# Źródła danych ETF
old = "  labReport: V8_REPO_RAW + 'lab/LAB_REPORT.json'\n};"
new = "  labReport: V8_REPO_RAW + 'lab/LAB_REPORT.json',\n  etfStatus: V8_REPO_RAW + 'institutional_data_hub/ETF_BTC_ETH_STATUS.json',\n  etfHistoryCsv: V8_REPO_RAW + 'institutional_data_hub/ETF_BTC_ETH_HISTORY.csv'\n};"
if old in s:
    s = s.replace(old, new, 1)
elif 'etfStatus:' not in s:
    raise SystemExit('Nie znaleziono miejsca na źródła ETF')

# Zakładka historii ETF
old = "  etf: 'ETF_BTC_ETH',\n  lab: 'LAB_ANALIZA_AKTYWA',"
new = "  etf: 'ETF_BTC_ETH',\n  etfHistory: 'ETF_HISTORIA',\n  lab: 'LAB_ANALIZA_AKTYWA',"
if old in s:
    s = s.replace(old, new, 1)
elif 'etfHistory:' not in s:
    raise SystemExit('Nie znaleziono miejsca na ETF_HISTORIA')

# Pełne odświeżanie pobiera monitor i historię ETF
old = "    const labJson = JSON.parse(fetchText_(V8_FILES.labReport));\n    const mrCsv = fetchText_(V8_FILES.marketReader);"
new = "    const labJson = JSON.parse(fetchText_(V8_FILES.labReport));\n    const etfStatusJson = JSON.parse(fetchText_(V8_FILES.etfStatus));\n    const etfHistoryCsv = fetchText_(V8_FILES.etfHistoryCsv);\n    const mrCsv = fetchText_(V8_FILES.marketReader);"
if old in s:
    s = s.replace(old, new, 1)
elif 'const etfStatusJson' not in s:
    raise SystemExit('Nie znaleziono sekcji pobierania danych ETF')

old = "    writeEtfPanel_(ss.getSheetByName(V8_SHEETS.etf), phaseJson, snapshotJson);\n    writeLabPanel_(ss.getSheetByName(V8_SHEETS.lab), labJson);"
new = "    writeEtfPanel_(ss.getSheetByName(V8_SHEETS.etf), etfStatusJson);\n    writeEtfHistory_(ss.getSheetByName(V8_SHEETS.etfHistory), etfHistoryCsv);\n    writeLabPanel_(ss.getSheetByName(V8_SHEETS.lab), labJson);"
if old in s:
    s = s.replace(old, new, 1)
elif 'writeEtfHistory_(ss.getSheetByName(V8_SHEETS.etfHistory)' not in s:
    raise SystemExit('Nie znaleziono wywołania panelu ETF')

# Ręczne odświeżanie ETF
pattern = r"function ODSWIEZ_ETF_BTC_ETH\(\) \{.*?\n\}\n\nfunction ODSWIEZ_LAB"
replacement = """function ODSWIEZ_ETF_BTC_ETH() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  V8_SETUP();
  const etfStatusJson = JSON.parse(fetchText_(V8_FILES.etfStatus));
  const etfHistoryCsv = fetchText_(V8_FILES.etfHistoryCsv);
  writeEtfPanel_(ss.getSheetByName(V8_SHEETS.etf), etfStatusJson);
  writeEtfHistory_(ss.getSheetByName(V8_SHEETS.etfHistory), etfHistoryCsv);
  ss.toast('ETF BTC / ETH oraz historia odświeżone', 'V8', 4);
}

function ODSWIEZ_LAB"""
s2, n = re.subn(pattern, replacement, s, count=1, flags=re.S)
if n == 1:
    s = s2
elif 'ETF BTC / ETH oraz historia odświeżone' not in s:
    raise SystemExit('Nie udało się podmienić ręcznego odświeżania ETF')

# Panel ETF i historia
pattern = r"function writeEtfPanel_\(.*?\n\}\n\nfunction writeLabPanel_"
replacement = """function writeEtfPanel_(sheet, status) {
  const assets = (status || {}).assets || {};
  const globalCtx = (status || {}).global_institutional_interest || {};
  const rows = [
    ['ETF BTC / ETH — KAPITAŁ INSTYTUCJONALNY','','','','','','',''],
    ['AKTYWO','OSTATNI ZAKOŃCZONY DZIEŃ','PRZEPŁYW mln USD','5 DNI mln USD','20 DNI mln USD','30 DNI mln USD','DZISIAJ','OCENA']
  ];
  ['BTC','ETH'].forEach(sym => {
    const x = assets[sym] || {};
    const preview = x.today_flow_preview_usdm;
    const complete = Number(x.today_fund_completeness_pct || 0);
    let todayText = x.today_status_pl || 'BRAK DANYCH';
    if (preview !== null && preview !== undefined && complete > 0) {
      todayText += ' | podgląd ' + fmtCell_(preview) + ' mln USD | kompletność ' + fmtCell_(complete) + '%';
    } else {
      todayText += ' | nie traktuj 0 jako wyniku końcowego';
    }
    rows.push([
      sym,
      x.last_closed_date || 'brak danych',
      valueOrBlank_(x.last_closed_flow_usdm),
      valueOrBlank_(x.closed_5d_usdm),
      valueOrBlank_(x.closed_20d_usdm),
      valueOrBlank_(x.closed_30d_usdm),
      todayText,
      ((x.closed_trend || {}).label_pl || 'BRAK OCENY')
    ]);
  });
  rows.push(['','','','','','','','']);
  rows.push(['WSPÓLNY OBRAZ','','','','','','', (globalCtx.label_pl || 'BRAK OCENY') + ' | ' + fmtCell_(globalCtx.score_0_10) + '/10']);
  rows.push(['ZASADA','','','','','','','Dzisiejsze dane są wstępne. Trend liczymy wyłącznie z zakończonych dni ETF.']);

  sheet.clearContents();
  sheet.getRange(1,1,rows.length,8).setValues(rows);
  sheet.getRange(1,1,1,8).merge().setFontWeight('bold').setHorizontalAlignment('center');
  sheet.getRange(2,1,1,8).setFontWeight('bold');
  sheet.setFrozenRows(2);
  sheet.getRange(3,3,2,4).setNumberFormat('0.00');
  sheet.getRange(1,1,rows.length,8).setWrap(true).setVerticalAlignment('middle');
  [90,145,125,120,120,120,360,330].forEach((w,idx)=>sheet.setColumnWidth(idx+1,w));
}

function writeEtfHistory_(sheet, csvText) {
  const rows = Utilities.parseCsv(csvText);
  sheet.clearContents();
  if (!rows.length) return;
  const keep = rows.length > 121 ? [rows[0]].concat(rows.slice(-120)) : rows;
  sheet.getRange(1,1,keep.length,keep[0].length).setValues(keep);
  sheet.setFrozenRows(1);
  sheet.getRange(1,1,1,keep[0].length).setFontWeight('bold');
  if (keep.length > 1) sheet.getRange(2,2,keep.length-1,3).setNumberFormat('0.00');
  sheet.getRange(1,1,keep.length,keep[0].length).setWrap(true);
  sheet.autoResizeColumns(1,keep[0].length);
}

function writeLabPanel_"""
s2, n = re.subn(pattern, replacement, s, count=1, flags=re.S)
if n != 1:
    raise SystemExit('Nie udało się wymienić panelu ETF')
s = s2

p.write_text(s, encoding='utf-8')
print('Pełny skrypt panelu zaktualizowany')
