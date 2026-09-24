from pathlib import Path

p = Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL_V10.txt')
s = p.read_text(encoding='utf-8')
marker = '// ===== V10 UNIFIED DASHBOARD THEME ====='
if marker in s:
    s = s.split(marker)[0].rstrip() + '\n'

# Apply the shared theme after a full refresh. This keeps all production calculations intact.
needle = '    stampRefresh_(ss);'
if needle in s and 'applyUnifiedV8Theme_(ss);' not in s:
    s = s.replace(needle, needle + '\n    applyUnifiedV8Theme_(ss);', 1)

patch = r'''

// ===== V10 UNIFIED DASHBOARD THEME =====
// Jeden tor wizualny dla całego V8. Nie zmienia obliczeń ani progów produkcyjnych.
const V8_UI = {
  canvas:'#eef4f7', header:'#cfe8f6', border:'#c3d9e8', text:'#17324d',
  hot:'#f8d7da', hotText:'#9f2f2f', cold:'#dbeaf7', coldText:'#225d85',
  neutral:'#dff1e5', neutralText:'#246b3a', warn:'#fff1bf', warnText:'#8a6500',
  fomo:'#fde2c4', fomoText:'#a55300', info:'#e6edf3', infoText:'#40566f',
  strong:'#fce5cd', strongText:'#92400e'
};

function applyUnifiedV8Theme_(ss) {
  const names = [
    'PANEL','PORTFEL_LONG','PORTFEL_TACTICAL','SILNIK_LONG','SILNIK_TACTICAL',
    'PRZEPLYWY','ETF_BTC_ETH','ETF_HISTORIA','LAB_ANALIZA_AKTYWA','MARKET_READER',
    'ALARMY_EKSTREMOW','HISTORIA','USTAWIENIA','PORANNY_BRIEF'
  ];
  names.forEach(name => {
    const sh = ss.getSheetByName(name);
    if (!sh) return;
    sh.setHiddenGridlines(true);
    const rows = Math.max(1, sh.getLastRow());
    const cols = Math.max(1, sh.getLastColumn());
    const range = sh.getRange(1,1,rows,cols);
    range.setFontFamily('Roboto').setFontColor(V8_UI.text).setVerticalAlignment('middle');
    if (name !== 'PORANNY_BRIEF') {
      range.setBackground(V8_UI.canvas);
      const h = sh.getRange(1,1,1,cols);
      h.setBackground(V8_UI.header).setFontWeight('bold').setHorizontalAlignment('center');
      styleUnifiedV8Cells_(sh, rows, cols);
    }
  });
}

function styleUnifiedV8Cells_(sh, rows, cols) {
  if (rows < 1 || cols < 1) return;
  const vals = sh.getRange(1,1,rows,cols).getDisplayValues();
  const head = vals[0].map(x => String(x||'').toUpperCase());
  const bg = Array.from({length:rows}, () => Array(cols).fill(V8_UI.canvas));
  const fg = Array.from({length:rows}, () => Array(cols).fill(V8_UI.text));
  const fw = Array.from({length:rows}, () => Array(cols).fill('normal'));
  for (let c=0;c<cols;c++) { bg[0][c]=V8_UI.header; fw[0][c]='bold'; }

  for (let r=1;r<rows;r++) {
    for (let c=0;c<cols;c++) {
      const raw = String(vals[r][c]||'').trim();
      const t = raw.toUpperCase();
      const h = head[c] || '';
      let style = unifiedSemanticStyleV10_(t, raw, h);
      if (style) {
        bg[r][c] = style.bg; fg[r][c] = style.fg; fw[r][c] = 'bold';
      }
    }
  }
  sh.getRange(1,1,rows,cols).setBackgrounds(bg).setFontColors(fg).setFontWeights(fw);
}

function unifiedSemanticStyleV10_(t, raw, header) {
  const num = Number(String(raw).replace(',','.'));

  // Najpierw konkretna semantyka górnych/dolnych zakresów.
  if (t.includes('GÓRNE GRANICE') || t.includes('EKSTREMUM +') || t.includes('SKRAJNIE +'))
    return {bg:V8_UI.hot,fg:V8_UI.hotText};
  if (t.includes('DOLNE GRANICE') || t.includes('EKSTREMUM −') || t.includes('EKSTREMUM -') || t.includes('SKRAJNIE -'))
    return {bg:V8_UI.cold,fg:V8_UI.coldText};
  if (t.includes('GÓRNA STREFA') || t.includes('UWAGA +'))
    return {bg:V8_UI.warn,fg:V8_UI.warnText};
  if (t.includes('DOLNA STREFA') || t.includes('UWAGA -'))
    return {bg:V8_UI.cold,fg:V8_UI.coldText};

  // Wspólny język statusów.
  if (t === 'GORĄCO' || t.includes('BLOKUJ') || t.includes('KRYTYCZNY') || t.includes('NIE DOKŁADAJ'))
    return {bg:V8_UI.hot,fg:V8_UI.hotText};
  if (t === 'CHŁODNO' || t.includes('WYPRZEDANIE'))
    return {bg:V8_UI.cold,fg:V8_UI.coldText};
  if (t.includes('NEUTRALNIE') || t === 'KUP' || t.includes('KUP TRENDOWO') || t === 'ZEZWÓL')
    return {bg:V8_UI.neutral,fg:V8_UI.neutralText};
  if (t.includes('OSTROŻNIE') || t.includes('OSTRZEŻENIE') || t === 'CZEKAJ' || t.includes('SŁABNIE'))
    return {bg:V8_UI.warn,fg:V8_UI.warnText};
  if (t.includes('FOMO') && !t.includes('FOMO 0'))
    return {bg:V8_UI.fomo,fg:V8_UI.fomoText};
  if (t.includes('MOCNY') || t.includes('SPRAWDŹ') || t.includes('NASILA SIĘ'))
    return {bg:V8_UI.strong,fg:V8_UI.strongText};
  if (t.includes('MACD ALERT') || t.includes('INFO') || t.includes('BEZ ZMIAN'))
    return {bg:V8_UI.info,fg:V8_UI.infoText};

  // Liczbowe progi RSI/MFI/FOMO w silnikach — dokładnie te same progi, bez zmiany logiki.
  if (Number.isFinite(num)) {
    if (header.includes('RSI')) {
      if (num >= 80) return {bg:V8_UI.hot,fg:V8_UI.hotText};
      if (num >= 75) return {bg:V8_UI.warn,fg:V8_UI.warnText};
      if (num <= 20) return {bg:V8_UI.cold,fg:V8_UI.coldText};
      if (num <= 25) return {bg:V8_UI.cold,fg:V8_UI.coldText};
    }
    if (header.includes('MFI')) {
      if (num >= 90) return {bg:V8_UI.hot,fg:V8_UI.hotText};
      if (num >= 80) return {bg:V8_UI.warn,fg:V8_UI.warnText};
      if (num <= 10) return {bg:V8_UI.cold,fg:V8_UI.coldText};
      if (num <= 20) return {bg:V8_UI.cold,fg:V8_UI.coldText};
    }
    if (header.includes('FOMO')) {
      if (num >= 8) return {bg:V8_UI.fomo,fg:V8_UI.fomoText};
    }
    if (header.includes('RYZYKO')) {
      if (num >= 8) return {bg:V8_UI.hot,fg:V8_UI.hotText};
      if (num >= 5) return {bg:V8_UI.warn,fg:V8_UI.warnText};
      if (num <= 2) return {bg:V8_UI.neutral,fg:V8_UI.neutralText};
    }
  }
  return null;
}
'''

p.write_text(s.rstrip() + patch + '\n', encoding='utf-8')
print('Applied unified V8 dashboard theme and semantic color map')
