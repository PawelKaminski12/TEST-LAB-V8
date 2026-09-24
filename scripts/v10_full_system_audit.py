from pathlib import Path
import csv, json, re, hashlib, sys
from collections import Counter

ROOT = Path('.')
APP = ROOT/'google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL_V10.txt'
EXPECTED_LONG = {'ETH','SOL','LINK','ONDO','RENDER','FLOKI','PEPE','SPX6900','XRP','XLM','HBAR','AVAX','AWE'}
EXPECTED_TACTICAL = {'BTC'} | EXPECTED_LONG
EXPECTED_TFS_LONG = {'1D','2D','3D','4D','5D','1T','2T'}
EXPECTED_TFS_RADAR = {'1H','2H','4H'}

checks=[]
warns=[]
def check(name, ok, detail=''):
    checks.append({'check':name,'pass':bool(ok),'detail':str(detail)})
def warn(name, detail=''):
    warns.append({'warning':name,'detail':str(detail)})

def read_csv(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def enabled_prod(rows):
    out=set()
    for r in rows:
        if str(r.get('enabled','')).lower()=='true' and r.get('target_scope')=='PRODUCTION':
            out.add(r.get('symbol'))
    return out

# ---- Apps Script static structure ----
check('APP_SCRIPT_EXISTS', APP.exists(), APP)
app = APP.read_text(encoding='utf-8') if APP.exists() else ''
lines = app.splitlines()
sha256 = hashlib.sha256(app.encode('utf-8')).hexdigest() if app else ''
check('APP_SCRIPT_NONEMPTY', len(app) > 100000, f'bytes={len(app)} lines={len(lines)} sha256={sha256}')

required_functions = [
    'onOpen','V8_SETUP','ODSWIEZ_WSZYSTKO','ODSWIEZ_PORANNY_BRIEF','ODSWIEZ_ETF_BTC_ETH','ODSWIEZ_LAB',
    'SPRAWDZ_EKSTREMA','writePolishPanel_','writeLongEngine_','writeTacticalEngine_','writeFlowEngine_',
    'writeMorningRadarBrief_','setupMorningBrief_','morningRadarModeV10_','onSelectionChange',
    'classifyAlarmDirection_','alarmDirection_'
]
funcs = re.findall(r'(?m)^\s*function\s+([A-Za-z_$][\w$]*)\s*\(', app)
fc=Counter(funcs)
for fn in required_functions:
    check('FUNCTION_'+fn, fc.get(fn,0)==1, f'count={fc.get(fn,0)}')

dups={k:v for k,v in fc.items() if v>1}
check('NO_DUPLICATE_FUNCTIONS', not dups, dups)

# Bare identifiers often cause ReferenceError after accidental paste, e.g. line containing only "a".
keywords={'else','try','finally','break','continue','return','throw','debugger'}
susp=[]
for i,line in enumerate(lines,1):
    m=re.match(r'^\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*;?\s*$', line)
    if m and m.group(1) not in keywords:
        susp.append((i,m.group(1)))
check('NO_SUSPICIOUS_BARE_IDENTIFIERS', not susp, susp[:20])

check('NO_K1_MODE_DEPENDENCY', "getRange('K1')" not in app and 'getRange("K1")' not in app, 'K1 must not store radar mode')
check('MODE_IN_DOCUMENT_PROPERTIES', "V10_MORNING_MODE" in app and 'PropertiesService.getDocumentProperties()' in app, '')
check('NO_WIDE_BREAKAPART', 'getMaxRows(), sheet.getMaxColumns()).breakApart()' not in app and 'getDataRange().breakApart()' not in app, '')
check('HAS_EXACT_MERGED_RANGE_UNMERGE', 'getMergedRanges()' in app and '.breakApart()' in app, '')
check('EXECUTION_OFF_TEXT', ('WYŁĄCZONE' in app or 'execution' in app.lower()), 'visual/support layer only')

# ---- Universe ----
alt_rows=read_csv('config/alt_universe.csv')
tact_rows=read_csv('config/tactical_universe.csv')
alt_prod=enabled_prod(alt_rows)
tact_prod=enabled_prod(tact_rows)
long_prod=alt_prod-{'BTC'}
check('LONG_UNIVERSE_13', long_prod==EXPECTED_LONG, sorted(long_prod))
check('TACTICAL_UNIVERSE_14', tact_prod==EXPECTED_TACTICAL, sorted(tact_prod))
check('AAVE_ARCHIVED', any(r.get('symbol')=='AAVE' and str(r.get('enabled','')).lower()=='false' and r.get('target_scope')=='ARCHIVE' for r in alt_rows), '')
check('NO_SUI_IN_SCOPE', 'SUI' not in alt_prod and 'SUI' not in tact_prod, '')

# ---- Zones 91/91 ----
zone_rows=read_csv('config/alt_zones.csv')
pairs={(r.get('symbol'),r.get('timeframe')) for r in zone_rows if r.get('symbol') in EXPECTED_LONG}
expected_pairs={(s,tf) for s in EXPECTED_LONG for tf in EXPECTED_TFS_LONG}
check('LONG_ZONES_91_OF_91', pairs==expected_pairs, f'actual={len(pairs)} expected={len(expected_pairs)} missing={sorted(expected_pairs-pairs)[:20]} extra={sorted(pairs-expected_pairs)[:20]}')
confirmed_bad=[r for r in zone_rows if r.get('symbol') in EXPECTED_LONG and r.get('timeframe') in EXPECTED_TFS_LONG and r.get('source_status')!='CONFIRMED']
check('LONG_ZONES_CONFIRMED', not confirmed_bad, confirmed_bad[:10])

# ---- LONG engine data ----
long=json.loads(Path('crypto_data_hub/ALT_ENGINE_MASTER_CHECKPOINT.json').read_text(encoding='utf-8'))
long_assets=long.get('assets',[])
long_syms={a.get('symbol') for a in long_assets if a.get('symbol') in EXPECTED_LONG}
check('LONG_CHECKPOINT_13', long_syms==EXPECTED_LONG, sorted(long_syms))

# ---- Tactical engine data ----
tact=json.loads(Path('tactical_engine/TACTICAL_ENGINE.json').read_text(encoding='utf-8'))
tact_assets=tact.get('assets',[])
tact_scope={a.get('symbol') for a in tact_assets if a.get('target_scope')=='PRODUCTION'}
check('TACTICAL_ENGINE_PRODUCTION_14', tact_scope==EXPECTED_TACTICAL, sorted(tact_scope))
for a in tact_assets:
    if a.get('target_scope')!='PRODUCTION':
        continue
    sym=a.get('symbol')
    tfs=set((a.get('timeframes') or {}).keys())
    check(f'TACTICAL_{sym}_TF_1H4H1D', {'1H','4H','1D'}.issubset(tfs), sorted(tfs))
    for tf in ['1H','4H','1D']:
        x=(a.get('timeframes') or {}).get(tf,{})
        check(f'TACTICAL_{sym}_{tf}_CLOSED_BAR', x.get('closed_bar_only') is True, x.get('closed_bar_only'))

# ---- Morning radar ----
rad=json.loads(Path('morning_radar/MORNING_RADAR.json').read_text(encoding='utf-8'))
rad_assets=rad.get('assets',[])
rad_syms={a.get('symbol') for a in rad_assets}
check('MORNING_RADAR_13', rad_syms==EXPECTED_LONG, sorted(rad_syms))
for a in rad_assets:
    sym=a.get('symbol')
    tfs=a.get('timeframes') or {}
    check(f'RADAR_{sym}_TF_1H2H4H', EXPECTED_TFS_RADAR.issubset(set(tfs)), sorted(tfs))
    for tf in EXPECTED_TFS_RADAR:
        x=tfs.get(tf,{})
        check(f'RADAR_{sym}_{tf}_CLOSED_BAR', x.get('closed_bar_only') is True, x.get('closed_bar_only'))
        side=x.get('macd_level_side')
        macd=x.get('macd')
        if isinstance(macd,(int,float)):
            expected_side='UPPER' if macd>=0 else 'LOWER'
            check(f'RADAR_{sym}_{tf}_MACD_SIDE', side==expected_side, f'macd={macd} side={side} expected={expected_side}')
        disp=str(x.get('macd_display_pl') or '')
        reason=str(x.get('macd_reason_pl') or '')
        if 'GÓRNE' in disp or 'górne' in reason:
            check(f'RADAR_{sym}_{tf}_MACD_TEXT_UPPER', side=='UPPER', f'{disp} | {reason} | side={side}')
        if 'DOLNE' in disp or 'dolne' in reason:
            check(f'RADAR_{sym}_{tf}_MACD_TEXT_LOWER', side=='LOWER', f'{disp} | {reason} | side={side}')

# ---- Main panel invariant ----
panel_spec=Path('google_sheets/DUAL_ENGINE_PANEL_SPEC.md').read_text(encoding='utf-8')
for h in ['AKTYWO','CENA','LONG','TACTICAL','RYZYKO 0–10','ZGODNOŚĆ','ALERT']:
    check('PANEL_HEADER_'+h, h in panel_spec, '')

# ---- External reader stays optional ----
mr=json.loads(Path('market_reader/MARKET_READER_ADAPTER.json').read_text(encoding='utf-8'))
status=str(mr.get('status') or mr.get('adapter_status') or '')
if status and status not in {'WAITING_FOR_SOURCE','WAITING'}:
    warn('MARKET_READER_STATUS', status)

failed=[x for x in checks if not x['pass']]
summary={
    'engine':'V10_FULL_SYSTEM_AUDIT_v1',
    'app_script_sha256':sha256,
    'app_script_lines':len(lines),
    'checks_total':len(checks),
    'checks_passed':len(checks)-len(failed),
    'checks_failed':len(failed),
    'status':'PASS' if not failed else 'FAIL',
    'failures':failed,
    'warnings':warns,
    'checks':checks,
}
out=Path('audit'); out.mkdir(exist_ok=True)
(out/'V10_FULL_SYSTEM_AUDIT.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
md=[
    '# V10 FULL SYSTEM AUDIT',
    '',
    f"- Status: **{summary['status']}**",
    f"- Checks: **{summary['checks_passed']}/{summary['checks_total']}**",
    f"- App Script lines: **{summary['app_script_lines']}**",
    f"- SHA-256: `{summary['app_script_sha256']}`",
    '',
    '## Failures',
]
if failed:
    md += [f"- {x['check']}: {x['detail']}" for x in failed]
else:
    md += ['- None']
md += ['', '## Warnings']
md += [f"- {x['warning']}: {x['detail']}" for x in warns] or ['- None']
(out/'V10_FULL_SYSTEM_AUDIT.md').write_text('\n'.join(md)+'\n',encoding='utf-8')

print(json.dumps({k:summary[k] for k in ['status','checks_total','checks_passed','checks_failed','app_script_lines','app_script_sha256']},indent=2))
if failed:
    print('FAILED CHECKS:')
    for x in failed:
        print('-',x['check'],x['detail'])
    sys.exit(1)
