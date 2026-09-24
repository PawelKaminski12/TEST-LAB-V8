from pathlib import Path

PATH = Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL_V10.txt')
text = PATH.read_text(encoding='utf-8')

# 1) Bezpieczne resetowanie zaakceptowanych pulpitów: najpierw rozpinamy stare scalenia.
for fn in ['setupPortfolioLong_', 'setupPortfolioTactical_', 'setupMorningBrief_']:
    old = f"function {fn}(sheet) {{\n  sheet.clear();"
    new = f"function {fn}(sheet) {{\n  sheet.getDataRange().breakApart();\n  sheet.clear();"
    text = text.replace(old, new)

# 2) Po pełnym odświeżeniu nakładamy jedną semantykę kolorów na wszystkie widoczne pulpity.
hook_old = "    formatPanel_(ss.getSheetByName(V8_SHEETS.panel));\n    appendHistoryOnChanges_"
hook_new = "    formatPanel_(ss.getSheetByName(V8_SHEETS.panel));\n    applyUnifiedThemeV10_(ss);\n    appendHistoryOnChanges_"
if 'applyUnifiedThemeV10_(ss);' not in text:
    text = text.replace(hook_old, hook_new, 1)

# 3) Poranny Brief po ręcznym odświeżeniu też dostaje identyczną semantykę.
brief_hook_old = "  writeMorningRadarBrief_(sheet, radarJson);\n  ss.toast('Poranny Radar odświeżony"
brief_hook_new = "  writeMorningRadarBrief_(sheet, radarJson);\n  applyUnifiedThemeV10_(ss);\n  ss.toast('Poranny Radar odświeżony"
if brief_hook_old in text and brief_hook_new not in text:
    text = text.replace(brief_hook_old, brief_hook_new, 1)

marker = '// ===== V10 UI UNIFICATION PACK — WSPÓLNA SEMANTYKA KOLORÓW ====='
if marker in text:
    text = text.split(marker)[0].rstrip() + '\n\n'

append = r'''
// ===== V10 UI UNIFICATION PACK — WSPÓLNA SEMANTYKA KOLORÓW =====
// Tylko warstwa wizualna. Nie zmienia logiki LONG/TACTICAL, progów ani danych w maszynowni.

const V10_UI = {
  hot: '#FAD1D1', hotText: '#8F2D2D',
  cold: '#D9EAF7', coldText: '#245B78',
  neutral: '#DDF2E3', neutralText: '#1F6B3A',
  warn: '#FFF0B8', warnText: '#7A5B00',
  fomo: '#FCE2B8', fomoText: '#8A4B08',
  macd: '#E8EDF2', macdText: '#44546A',
  info: '#EAF5FB', infoText: '#2F5F77'
};

function applyUnifiedThemeV10_(ss) {
  const names = [
    'PANEL','PORTFEL_LONG','PORTFEL_TACTICAL','SILNIK_LONG','SILNIK_TACTICAL',
    'PRZEPLYWY','ETF_BTC_ETH','ETF_HISTORIA','LAB_ANALIZA_AKTYWA','MARKET_READER',
    'ALARMY_EKSTREMOW','HISTORIA','PORANNY_BRIEF'
  ];
  names.forEach(name => {
    const sh = ss.getSheetByName(name);
    if (!sh) return;
    applyUnifiedSheetThemeV10_(sh);
  });
}

function applyUnifiedSheetThemeV10_(sheet) {
  const range = sheet.getDataRange();
  if (!range || range.getNumRows() < 1 || range.getNumColumns() < 1) return;
  const vals = range.getDisplayValues();
  const merged = range.getMergedRanges();
  const mergeMap = {};
  merged.forEach(m => {
    const r0 = m.getRow(), c0 = m.getColumn(), rn = m.getNumRows(), cn = m.getNumColumns();
    for (let rr = r0; rr < r0 + rn; rr++) {
      for (let cc = c0; cc < c0 + cn; cc++) mergeMap[rr + ':' + cc] = true;
    }
  });

  for (let r = 0; r < vals.length; r++) {
    for (let c = 0; c < vals[r].length; c++) {
      const raw = String(vals[r][c] || '').trim();
      if (!raw) continue;
      const t = raw.toUpperCase();
      const rr = r + 1, cc = c + 1;

      // Scalone nagłówki mają własne formatowanie. Globalny motyw ich nie dotyka.
      if (mergeMap[rr + ':' + cc]) continue;

      const cell = sheet.getRange(rr, cc);

      if (isHotV10_(t)) styleBriefCardV10_(cell, V10_UI.hot, V10_UI.hotText);
      else if (isColdV10_(t)) styleBriefCardV10_(cell, V10_UI.cold, V10_UI.coldText);
      else if (isNeutralV10_(t)) styleBriefCardV10_(cell, V10_UI.neutral, V10_UI.neutralText);
      else if (isWarnV10_(t)) styleBriefCardV10_(cell, V10_UI.warn, V10_UI.warnText);
      else if (isFomoV10_(t)) styleBriefCardV10_(cell, V10_UI.fomo, V10_UI.fomoText);
      else if (isMacdV10_(t)) styleBriefCardV10_(cell, V10_UI.macd, V10_UI.macdText);
      else if (isInfoV10_(t)) styleBriefCardV10_(cell, V10_UI.info, V10_UI.infoText);

      const num = Number(String(raw).replace(',', '.'));
      if (Number.isFinite(num)) {
        const metric = nearestMetricHeaderV10_(vals, r, c);
        if (metric === 'RSI') {
          if (num >= 75) styleBriefCardV10_(cell, V10_UI.hot, V10_UI.hotText);
          else if (num <= 25) styleBriefCardV10_(cell, V10_UI.cold, V10_UI.coldText);
        } else if (metric === 'MFI') {
          if (num >= 80) styleBriefCardV10_(cell, V10_UI.hot, V10_UI.hotText);
          else if (num <= 20) styleBriefCardV10_(cell, V10_UI.cold, V10_UI.coldText);
        } else if (metric.indexOf('FOMO') >= 0) {
          if (num >= 8) styleBriefCardV10_(cell, V10_UI.fomo, V10_UI.fomoText);
          else if (num >= 6) styleBriefCardV10_(cell, V10_UI.warn, V10_UI.warnText);
        } else if (metric.indexOf('RYZYKO') >= 0) {
          if (num >= 8) styleBriefCardV10_(cell, V10_UI.hot, V10_UI.hotText);
          else if (num >= 5) styleBriefCardV10_(cell, V10_UI.warn, V10_UI.warnText);
          else if (num <= 2) styleBriefCardV10_(cell, V10_UI.neutral, V10_UI.neutralText);
        } else if (metric.indexOf('PRZEGRZ') >= 0) {
          if (num >= 7) styleBriefCardV10_(cell, V10_UI.hot, V10_UI.hotText);
          else if (num >= 3) styleBriefCardV10_(cell, V10_UI.fomo, V10_UI.fomoText);
        }
      }
    }
  }
}

function nearestMetricHeaderV10_(vals, r, c) {
  const recognized = ['RSI','MFI','FOMO','RYZYKO','RYZYKO WYJŚCIA','PRZEGRZANIE','PRZEGRZ.'];
  for (let rr = r - 1; rr >= Math.max(0, r - 6); rr--) {
    const h = String((vals[rr] || [])[c] || '').trim().toUpperCase();
    if (recognized.some(x => h === x || h.indexOf(x) >= 0)) return h;
  }
  return '';
}

function isHotV10_(t) {
  return t === 'GORĄCO' || t === 'BLOKUJ' || t === 'KRYTYCZNY' ||
         t === 'OCHRONA KAPITAŁU' || t === 'NIE DOKŁADAJ' ||
         t.indexOf('EKSTREMUM +') >= 0 || t.indexOf('GÓRNE GRANICE') >= 0;
}
function isColdV10_(t) {
  return t === 'CHŁODNO' || t === 'WYPRZEDANIE' ||
         t.indexOf('EKSTREMUM −') >= 0 || t.indexOf('EKSTREMUM -') >= 0 ||
         t.indexOf('DOLNE GRANICE') >= 0 || t.indexOf('DOLNE OSTRZEŻ') >= 0;
}
function isNeutralV10_(t) {
  return t === 'NEUTRALNIE' || t === 'ZEZWÓL' || t === 'GOTOWE' ||
         t === 'AKTUALNE' || t === 'AKTUALNY' || t === 'KUP' || t === 'KUP TRENDOWO';
}
function isWarnV10_(t) {
  return t === 'UWAGA' || t.indexOf('UWAGA ') === 0 || t === 'OSTROŻNIE' ||
         t === 'OSTROŻNY' || t === 'MOCNY' || t === 'CZEKAJ' ||
         t === 'PODWYŻSZONE RYZYKO' || t === 'NASILA SIĘ';
}
function isFomoV10_(t) {
  return t.indexOf('FOMO') >= 0 && (t.indexOf('8') >= 0 || t.indexOf('HARD') >= 0 || t.indexOf('BLOK') >= 0);
}
function isMacdV10_(t) {
  return t.indexOf('MACD') >= 0 || t === 'BEZ ZMIAN' || t.indexOf('WSTRZYMAJ') >= 0;
}
function isInfoV10_(t) {
  return t === 'INFO' || t.indexOf('STREF') >= 0 || t.indexOf('DCA') >= 0;
}
'''

PATH.write_text(text.rstrip() + '\n\n' + append.strip() + '\n', encoding='utf-8')
print(f'Patched {PATH} ({PATH.stat().st_size} bytes)')
