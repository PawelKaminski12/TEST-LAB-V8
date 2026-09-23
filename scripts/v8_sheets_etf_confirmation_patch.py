from pathlib import Path
import re

p = Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL.txt')
s = p.read_text(encoding='utf-8')

old = "  etfHistoryCsv: V8_REPO_RAW + 'institutional_data_hub/ETF_BTC_ETH_HISTORY.csv'\n};"
new = "  etfHistoryCsv: V8_REPO_RAW + 'institutional_data_hub/ETF_BTC_ETH_HISTORY.csv',\n  etfConfirmation: V8_REPO_RAW + 'institutional_data_hub/ETF_BTC_ETH_CONFIRMATION.json'\n};"
if old in s:
    s = s.replace(old, new, 1)
elif 'etfConfirmation:' not in s:
    raise SystemExit('Nie znaleziono miejsca na źródło potwierdzenia ETF')

old = "    const etfHistoryCsv = fetchText_(V8_FILES.etfHistoryCsv);\n    const mrCsv = fetchText_(V8_FILES.marketReader);"
new = "    const etfHistoryCsv = fetchText_(V8_FILES.etfHistoryCsv);\n    const etfConfirmationJson = JSON.parse(fetchText_(V8_FILES.etfConfirmation));\n    const mrCsv = fetchText_(V8_FILES.marketReader);"
if old in s:
    s = s.replace(old, new, 1)
elif 'const etfConfirmationJson' not in s:
    raise SystemExit('Nie znaleziono miejsca pobierania potwierdzenia ETF')

old = "    writeEtfPanel_(ss.getSheetByName(V8_SHEETS.etf), etfStatusJson);"
new = "    writeEtfPanel_(ss.getSheetByName(V8_SHEETS.etf), etfStatusJson, etfConfirmationJson);"
if old in s:
    s = s.replace(old, new, 1)

old = "  const etfHistoryCsv = fetchText_(V8_FILES.etfHistoryCsv);\n  writeEtfPanel_(ss.getSheetByName(V8_SHEETS.etf), etfStatusJson);"
new = "  const etfHistoryCsv = fetchText_(V8_FILES.etfHistoryCsv);\n  const etfConfirmationJson = JSON.parse(fetchText_(V8_FILES.etfConfirmation));\n  writeEtfPanel_(ss.getSheetByName(V8_SHEETS.etf), etfStatusJson, etfConfirmationJson);"
if old in s:
    s = s.replace(old, new, 1)
elif 'ODSWIEZ_ETF_BTC_ETH' in s and s.count('const etfConfirmationJson') < 2:
    raise SystemExit('Nie znaleziono ręcznego odświeżenia ETF')

pattern = r"function writeEtfPanel_\(sheet, status\) \{.*?\n\}\n\nfunction writeEtfHistory_"
replacement = """function writeEtfPanel_(sheet, status, confirmation) {
  const assets = (status || {}).assets || {};
  const confAssets = (confirmation || {}).assets || {};
  const global = (confirmation || {}).global_institutional_interest || (status || {}).global_institutional_interest || {};
  const rows = [
    ['ETF BTC / ETH — KAPITAŁ INSTYTUCJONALNY + POTWIERDZENIE CENY','','','','','','','','','',''],
    ['AKTYWO','OSTATNI ZAKOŃCZONY DZIEŃ','PRZEPŁYW mln USD','5 DNI mln USD','20 DNI mln USD','30 DNI mln USD','DZISIAJ','JAKOŚĆ DANYCH','CENA vs ETF 5D','CENA vs ETF 20D','WNIOSKI'],
  ];
  ['BTC','ETH'].forEach(sym => {
    const x=assets[sym] || {};
    const c=confAssets[sym] || {};
    const q=c.quality || {};
    const p5=c.price_vs_etf_5d || {};
    const p20=c.price_vs_etf_20d || {};
    const preview = x.today_flow_preview_usdm;
    const complete = Number(x.today_fund_completeness_pct || 0);
    let todayText = x.today_status_pl || c.today_status_pl || 'BRAK DANYCH';
    if (preview !== null && preview !== undefined && complete > 0) {
      todayText += ' | podgląd '+fmtCell_(preview)+' mln USD | kompletność '+fmtCell_(complete)+'%';
    } else {
      todayText += ' | brak finalnych danych za dziś';
    }
    rows.push([
      sym,
      x.last_closed_date || c.last_closed_date || 'brak danych',
      valueOrBlank_(x.last_closed_flow_usdm),
      valueOrBlank_(x.closed_5d_usdm),
      valueOrBlank_(x.closed_20d_usdm),
      valueOrBlank_(x.closed_30d_usdm),
      todayText,
      (q.label_pl || 'BRAK OCENY') + (q.score_0_100 !== undefined ? ' — '+fmtCell_(q.score_0_100)+'/100' : ''),
      p5.label_pl || 'BRAK OCENY',
      p20.label_pl || 'BRAK OCENY',
      c.overall_confirmation_pl || ((x.closed_trend || {}).label_pl || 'BRAK OCENY')
    ]);
  });
  rows.push(['','','','','','','','','','','']);
  rows.push(['WSPÓLNY OBRAZ','','','','','','','','','', (global.label_pl || 'BRAK OCENY')+' | '+fmtCell_(global.score_0_10)+'/10']);
  rows.push(['ZASADA','','','','','','','','','','Dzisiejsze dane są wstępne. Filtr ceny vs ETF używa tylko zakończonych dni i nie nadpisuje twardych blokad LONG ani TACTICAL.']);

  sheet.clearContents();
  sheet.getRange(1,1,rows.length,11).setValues(rows);
  sheet.getRange(1,1,1,11).merge().setFontWeight('bold').setHorizontalAlignment('center');
  sheet.getRange(2,1,1,11).setFontWeight('bold');
  sheet.setFrozenRows(2);
  sheet.getRange(3,3,2,4).setNumberFormat('0.00');
  sheet.getRange(1,1,rows.length,11).setWrap(true).setVerticalAlignment('middle');
  [80,135,110,105,105,105,300,260,300,300,320].forEach((w,idx)=>sheet.setColumnWidth(idx+1,w));
}

function writeEtfHistory_"""

s2, n = re.subn(pattern, replacement, s, count=1, flags=re.S)
if n != 1:
    if 'function writeEtfPanel_(sheet, status, confirmation)' not in s:
        raise SystemExit('Nie udało się wymienić panelu ETF')
    s2 = s

p.write_text(s2, encoding='utf-8')
print('Potwierdzenie cena vs ETF dodane do pełnego panelu')
