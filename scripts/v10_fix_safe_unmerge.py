from pathlib import Path

p=Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL_V10.txt')
s=p.read_text(encoding='utf-8')

repls={
    'sheet.getDataRange().breakApart();':'unmergeAllSafelyV10_(sheet);',
    'sheet.getMergedRanges().forEach(r => r.breakApart());':'unmergeAllSafelyV10_(sheet);',
    'sheet.getMergedRanges().forEach(r=>r.breakApart());':'unmergeAllSafelyV10_(sheet);',
}
for old,new in repls.items():
    s=s.replace(old,new)

helper="""

// ===== V10 SAFE UNMERGE =====
// Rozdziela wyłącznie rzeczywiście scalone zakresy; nie wywołuje breakApart() na całym arkuszu.
function unmergeAllSafelyV10_(sheet) {
  const maxRows = Math.max(1, sheet.getMaxRows());
  const maxCols = Math.max(1, sheet.getMaxColumns());
  const merged = sheet.getRange(1, 1, maxRows, maxCols).getMergedRanges();
  merged.forEach(r => r.breakApart());
}
"""
if 'function unmergeAllSafelyV10_' not in s:
    s += helper

if 'getDataRange().breakApart()' in s:
    raise SystemExit('Unsafe getDataRange().breakApart() remains')
if 'sheet.getMergedRanges()' in s:
    raise SystemExit('Invalid/suspicious sheet.getMergedRanges() remains')

p.write_text(s,encoding='utf-8')
print('Safe unmerge patch applied')
