from pathlib import Path

p = Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL_V10.txt')
s = p.read_text(encoding='utf-8')

old_widths = "[95,165,180,85,105,75,100,90,410,120].forEach((w,i)=>sheet.setColumnWidth(i+1,w));"
new_widths = "[135,225,235,130,130,115,115,160,450,190].forEach((w,i)=>sheet.setColumnWidth(i+1,w));"
if old_widths not in s:
    raise SystemExit('Morning Brief width marker not found')
s = s.replace(old_widths, new_widths, 1)

# Meta CSV uses the plural header `reasons`; keep `reason` as backward-compatible fallback.
s = s.replace("translateReasonV10_(m.reason || '')", "translateReasonV10_(m.reasons || m.reason || '')")

needle = "  applyTacticalColorsV10_(sheet, 20, detail.length + 19);\n}"
replacement = "  applyTacticalColorsV10_(sheet, 20, detail.length + 19);\n  styleMorningBriefV10_(sheet, detail.length);\n}"
if needle not in s:
    raise SystemExit('Morning Brief writer marker not found')
s = s.replace(needle, replacement, 1)

marker = '// ===== V10 MORNING BRIEF LIGHT DASHBOARD UI ====='
if marker in s:
    s = s.split(marker)[0].rstrip() + '\n'

style = r'''

// ===== V10 MORNING BRIEF LIGHT DASHBOARD UI =====
function styleMorningBriefV10_(sheet, detailCount) {
  const lastDetailRow = Math.max(32, 19 + Number(detailCount || 0));

  sheet.setHiddenGridlines(true);
  sheet.getRange(1,1,lastDetailRow,10)
    .setFontFamily('Roboto')
    .setFontSize(11)
    .setFontColor('#243447')
    .setVerticalAlignment('middle');

  sheet.getRange('A1:J1')
    .setBackground('#DCEEF8')
    .setFontColor('#17324D')
    .setFontWeight('bold')
    .setFontSize(18)
    .setHorizontalAlignment('center');
  sheet.setRowHeight(1, 42);

  ['A3:B3','D3:I3','A10:F10','H10:J10','A18:I18','A19:I19'].forEach(a1 => {
    sheet.getRange(a1)
      .setBackground('#CFE8F6')
      .setFontColor('#17324D')
      .setFontWeight('bold')
      .setFontSize(12)
      .setHorizontalAlignment('center');
  });

  sheet.getRange('A4:A8')
    .setBackground('#EAF4FB')
    .setFontWeight('bold')
    .setHorizontalAlignment('center');
  sheet.getRange('B4:B8')
    .setBackground('#F8FBFD')
    .setFontWeight('bold')
    .setHorizontalAlignment('center');

  styleBriefCardV10_(sheet.getRange('D4:E4'), '#E5F5EA', '#1F6B3A');
  styleBriefCardV10_(sheet.getRange('F4:G4'), '#FFF3CD', '#7A5B00');
  styleBriefCardV10_(sheet.getRange('H4:I4'), '#FDE2E2', '#8F2D2D');
  styleBriefCardV10_(sheet.getRange('D5:E5'), '#EDF1F5', '#44546A');
  styleBriefCardV10_(sheet.getRange('F5:G5'), '#FFF7E6', '#8A5A00');
  styleBriefCardV10_(sheet.getRange('H5:I5'), '#FFE9D6', '#9A4D00');
  styleBriefCardV10_(sheet.getRange('D6:E6'), '#FFE4D6', '#9A3D00');
  styleBriefCardV10_(sheet.getRange('F6:G6'), '#EEF2F6', '#455A64');
  styleBriefCardV10_(sheet.getRange('H6:I6'), '#E4F1FB', '#245A7A');

  sheet.getRange('A11:F15')
    .setBackground('#FFFFFF')
    .setHorizontalAlignment('center')
    .setFontSize(11);
  sheet.getRange('H11:J15')
    .setBackground('#F8FBFD')
    .setHorizontalAlignment('center')
    .setFontSize(11);

  for (let r=11; r<=15; r++) {
    const v = String(sheet.getRange(r,3).getValue() || '');
    const c = sheet.getRange(r,3);
    if (v === 'BLOKUJ') c.setBackground('#FAD1D1').setFontColor('#8F2D2D').setFontWeight('bold');
    else if (v === 'OSTROŻNIE') c.setBackground('#FFF0B8').setFontColor('#7A5B00').setFontWeight('bold');
    else if (v.indexOf('WSTRZYMAJ') >= 0) c.setBackground('#E8EDF2').setFontColor('#44546A').setFontWeight('bold');
    else if (v === 'ZEZWÓL') c.setBackground('#DDF2E3').setFontColor('#1F6B3A').setFontWeight('bold');
  }

  if (detailCount > 0) {
    const body = sheet.getRange(20,1,detailCount,9);
    body.setFontSize(11).setVerticalAlignment('middle');
    sheet.getRange(20,1,detailCount,8).setHorizontalAlignment('center');
    sheet.getRange(20,9,detailCount,1).setHorizontalAlignment('left').setWrap(true);
  }

  ['A3:B8','D3:I6','A10:F15','H10:J15','A18:I19'].forEach(a1 => {
    sheet.getRange(a1).setBorder(true,true,true,true,true,true,'#B9D4E5',SpreadsheetApp.BorderStyle.SOLID);
  });
  if (detailCount > 0) {
    sheet.getRange(19,1,detailCount+1,9)
      .setBorder(true,true,true,true,true,true,'#D5E3EC',SpreadsheetApp.BorderStyle.SOLID);
  }

  for (let r=3; r<=8; r++) sheet.setRowHeight(r, 30);
  sheet.setRowHeight(10, 32);
  for (let r=11; r<=15; r++) sheet.setRowHeight(r, 30);
  sheet.setRowHeight(18, 32);
  sheet.setRowHeight(19, 32);
  for (let r=20; r<=lastDetailRow; r++) sheet.setRowHeight(r, 28);

  // Większa szerokość całego dashboardu przesuwa jego wizualny środek w prawo
  // i wykorzystuje wolne miejsce po prawej stronie arkusza.
  [135,225,235,130,130,115,115,160,450,190].forEach((w,i)=>sheet.setColumnWidth(i+1,w));
}

function styleBriefCardV10_(range, bg, fg) {
  range
    .setBackground(bg)
    .setFontColor(fg)
    .setFontWeight('bold')
    .setFontSize(11)
    .setHorizontalAlignment('center')
    .setVerticalAlignment('middle');
}
'''

s = s.rstrip() + style + '\n'
p.write_text(s, encoding='utf-8')
print('Patched Morning Brief light dashboard UI + reason column')
