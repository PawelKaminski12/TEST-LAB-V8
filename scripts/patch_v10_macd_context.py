from pathlib import Path

p = Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL_V10.txt')
s = p.read_text(encoding='utf-8')

old = "      macd: macdBriefV10_(x.macd_extreme_label),"
new = "      macd: String(x.macd_display_pl || macdBriefV10_(x.macd_extreme_label)),"

if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    raise SystemExit('Morning Radar MACD display marker not found')

p.write_text(s, encoding='utf-8')
print('Applied Morning Radar MACD level/momentum display patch')
