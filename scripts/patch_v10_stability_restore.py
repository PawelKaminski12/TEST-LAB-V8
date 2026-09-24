from pathlib import Path

p = Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL_V10.txt')
s = p.read_text(encoding='utf-8')

# Najważniejsze: wyłączamy globalne skanowanie/kolorowanie całego skoroszytu.
# To ono powodowało wyjątki przy istniejących scalonych zakresach.
s = s.replace('    applyUnifiedThemeV10_(ss);\n', '')
s = s.replace('    applyUnifiedV8Theme_(ss);\n', '')
s = s.replace('  applyUnifiedThemeV10_(ss);\n', '')
s = s.replace('  applyUnifiedV8Theme_(ss);\n', '')

# Bezpieczne setupy: przed ponownym tworzeniem zaakceptowanych dashboardów
# rozpinamy scalenia wyłącznie w tych konkretnych arkuszach.
for fn in ['setupPortfolioLong_', 'setupPortfolioTactical_', 'setupMorningBrief_']:
    marker = f'function {fn}(sheet) {{\n'
    if marker in s:
        block_start = s.index(marker) + len(marker)
        tail = s[block_start:block_start+120]
        if 'sheet.getDataRange().breakApart();' not in tail:
            s = s[:block_start] + '  sheet.getDataRange().breakApart();\n' + s[block_start:]

# Dodajemy tylko bezpieczne, jawne formatowanie tabel bez scaleń.
# Nie dotykamy Porannego Radaru — jego zaakceptowany styl pozostaje własny.
if 'function applySafeEngineColorsV10_' not in s:
    s += r'''

// ===== V10 SAFE TABLE COLORS — BEZ GLOBALNEGO SKANOWANIA =====
// Stosowane wyłącznie do prostych tabel danych bez scaleń.
function applySafeEngineColorsV10_(sheet) {
  const rows = sheet.getLastRow();
  const cols = sheet.getLastColumn();
  if (rows < 2 || cols < 1) return;
  const range = sheet.getRange(1,1,rows,cols);
  if (range.getMergedRanges().length) return; // fail-safe: nie dotykamy tabel ze scaleniami
  const vals = range.getDisplayValues();
  const headers = vals[0].map(v => String(v||'').trim().toUpperCase());

  for (let r=1; r<vals.length; r++) {
    for (let c=0; c<vals[r].length; c++) {
      const raw = String(vals[r][c]||'').trim();
      if (!raw) continue;
      const t = raw.toUpperCase();
      const cell = sheet.getRange(r+1,c+1);
      const h = headers[c] || '';

      if (t==='BLOKUJ' || t==='GORĄCO' || t==='KRYTYCZNY' || t==='NIE DOKŁADAJ' || t==='OCHRONA KAPITAŁU')
        cell.setBackground('#FAD1D1').setFontColor('#8F2D2D').setFontWeight('bold');
      else if (t==='CHŁODNO' || t==='WYPRZEDANIE' || t.indexOf('DOLNE GRANICE')>=0 || t.indexOf('DOLNE OSTRZEŻ')>=0)
        cell.setBackground('#D9EAF7').setFontColor('#245B78').setFontWeight('bold');
      else if (t==='NEUTRALNIE' || t==='ZEZWÓL' || t==='GOTOWE' || t==='AKTUALNE' || t==='KUP' || t==='KUP TRENDOWO')
        cell.setBackground('#DDF2E3').setFontColor('#1F6B3A').setFontWeight('bold');
      else if (t==='UWAGA' || t.indexOf('UWAGA ')===0 || t==='OSTROŻNIE' || t==='CZEKAJ' || t==='PODWYŻSZONE RYZYKO')
        cell.setBackground('#FFF0B8').setFontColor('#7A5B00').setFontWeight('bold');

      const n = Number(raw.replace(',','.'));
      if (!Number.isFinite(n)) continue;
      if (h.indexOf('RSI')>=0) {
        if (n>=75) cell.setBackground('#FAD1D1').setFontColor('#8F2D2D').setFontWeight('bold');
        else if (n<=25) cell.setBackground('#D9EAF7').setFontColor('#245B78').setFontWeight('bold');
      } else if (h.indexOf('MFI')>=0) {
        if (n>=80) cell.setBackground('#FAD1D1').setFontColor('#8F2D2D').setFontWeight('bold');
        else if (n<=20) cell.setBackground('#D9EAF7').setFontColor('#245B78').setFontWeight('bold');
      } else if (h.indexOf('FOMO')>=0) {
        if (n>=8) cell.setBackground('#FCE2B8').setFontColor('#8A4B08').setFontWeight('bold');
        else if (n>=6) cell.setBackground('#FFF0B8').setFontColor('#7A5B00').setFontWeight('bold');
      } else if (h.indexOf('RYZYKO')>=0) {
        if (n>=8) cell.setBackground('#FAD1D1').setFontColor('#8F2D2D').setFontWeight('bold');
        else if (n>=5) cell.setBackground('#FFF0B8').setFontColor('#7A5B00').setFontWeight('bold');
        else if (n<=2) cell.setBackground('#DDF2E3').setFontColor('#1F6B3A').setFontWeight('bold');
      }
    }
  }
}
'''

# Wpinamy bezpieczne formatowanie tylko do prostych tabel silników.
for needle in [
    "  sheet.setFrozenRows(1);\n}\n\nfunction writeTacticalEngine_",
    "  sheet.setFrozenRows(1);\n}\n\nfunction writeFlowEngine_"
]:
    pass

# LONG
old = "  if (assets.length) sheet.getRange(2,1,assets.length,headers.length).setValues(assets);\n  sheet.setFrozenRows(1);\n}\n\nfunction writeTacticalEngine_"
new = "  if (assets.length) sheet.getRange(2,1,assets.length,headers.length).setValues(assets);\n  sheet.setFrozenRows(1);\n  applySafeEngineColorsV10_(sheet);\n}\n\nfunction writeTacticalEngine_"
s = s.replace(old,new,1)

# TACTICAL
old = "  if (assets.length) sheet.getRange(2,1,assets.length,headers.length).setValues(assets);\n  sheet.setFrozenRows(1);\n}\n\nfunction writeFlowEngine_"
new = "  if (assets.length) sheet.getRange(2,1,assets.length,headers.length).setValues(assets);\n  sheet.setFrozenRows(1);\n  applySafeEngineColorsV10_(sheet);\n}\n\nfunction writeFlowEngine_"
s = s.replace(old,new,1)

p.write_text(s, encoding='utf-8')
print('V10 stability restored: global theme disabled, safe table colors enabled')
