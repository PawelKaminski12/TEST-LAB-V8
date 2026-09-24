from pathlib import Path
import re

p = Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL_V10.txt')
s = p.read_text(encoding='utf-8')

# Remove duplicated inline legend block from polishMorningRadarV10_.
# Keep only the dedicated drawMorningRadarLegendV10_ renderer.
pattern = re.compile(
    r"\n\s*// LEGENDA po prawej — ten sam kod kolorów co w tabelach\.[\s\S]*?\n\s*styleMorningRadarButtonsV10_\(sheet, morningRadarModeV10_\(sheet\)\);\n\s*drawMorningRadarLegendV10_\(sheet\);",
    re.M,
)
replacement = "\n\n  // Przyciski + jedna, dedykowana legenda. Bez nakładających się scaleń.\n  styleMorningRadarButtonsV10_(sheet, morningRadarModeV10_(sheet));\n  drawMorningRadarLegendV10_(sheet);"

ns, n = pattern.subn(replacement, s, count=1)
if n != 1:
    raise SystemExit(f'Expected exactly one duplicated legend block, found {n}')

# Normalize dedicated legend title width to L:O for consistency with accepted layout.
ns = ns.replace("const title = sheet.getRange('L4:N4');", "const title = sheet.getRange('L4:O4');")
ns = ns.replace("sheet.getRange(5,12,rows.length,3).clearContent().clearFormat();", "sheet.getRange(5,12,rows.length,4).clearContent().clearFormat();")
ns = ns.replace("sheet.getRange(r,13,1,2).merge().setValue(x[1])", "sheet.getRange(r,13,1,3).merge().setValue(x[1])")
ns = ns.replace("sheet.getRange(r,12,1,3).setBorder", "sheet.getRange(r,12,1,4).setBorder")
ns = ns.replace("sheet.getRange('L13:N13').merge()", "sheet.getRange('L13:O13').merge()")
ns = ns.replace("sheet.getRange('L14:N14').merge()", "sheet.getRange('L14:O14').merge()")

p.write_text(ns, encoding='utf-8')
print('Patched V10: single Morning Radar legend renderer, no overlapping merges.')
