#!/usr/bin/env python3
import argparse
import csv
import json
import math
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path('.')
ALTS = ['ETH','SOL','LINK','ONDO','RENDER','FLOKI','PEPE','SPX6900','XRP','XLM','HBAR']
TACTICAL = ['BTC'] + ALTS
ZONE_TFS = ['1D','2D','3D','4D','5D','1T','2T']
TACTICAL_TFS = ['1H','4H','1D']

parser = argparse.ArgumentParser()
parser.add_argument('--pass-number', type=int, required=True)
args = parser.parse_args()
PASS_NO = args.pass_number

checks = []

def check(name, ok, detail=''):
    checks.append({'check': name, 'pass': bool(ok), 'detail': str(detail)})

def load_json(path):
    p = ROOT / path
    check(f'PLIK_{path}', p.exists(), 'istnieje' if p.exists() else 'BRAK')
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception as e:
        check(f'JSON_{path}', False, e)
        return {}

def read_csv_rows(path):
    p = ROOT / path
    check(f'PLIK_{path}', p.exists(), 'istnieje' if p.exists() else 'BRAK')
    if not p.exists():
        return []
    try:
        with p.open(encoding='utf-8', newline='') as f:
            return list(csv.DictReader(f))
    except Exception as e:
        check(f'CSV_{path}', False, e)
        return []

def finite(x):
    try:
        return math.isfinite(float(x))
    except Exception:
        return False

# 1. Uniwersum
universe = read_csv_rows('config/alt_universe.csv')
by_symbol = {r.get('symbol','').upper(): r for r in universe}
active = [r.get('symbol','').upper() for r in universe if str(r.get('enabled','')).lower() == 'true']
check('UNIWERSUM_BTC_PLUS_11', active == TACTICAL, active)
check('BTC_JAKO_REZIM_RYNKU', by_symbol.get('BTC',{}).get('role') == 'MARKET_REGIME', by_symbol.get('BTC'))
check('AAVE_ARCHIWUM', str(by_symbol.get('AAVE',{}).get('enabled','')).lower() == 'false' and by_symbol.get('AAVE',{}).get('target_scope') == 'ARCHIVE', by_symbol.get('AAVE'))

# 2. Strefy 77/77
zones = read_csv_rows('config/alt_zones.csv')
coverage = {s:set() for s in ALTS}
bad_zone_rows = []
for r in zones:
    s = r.get('symbol','').upper()
    tf = r.get('timeframe','').upper()
    if s not in ALTS or tf not in ZONE_TFS:
        continue
    try:
        lo = float(r.get('from'))
        hi = float(r.get('to'))
        valid = math.isfinite(lo) and math.isfinite(hi) and lo > 0 and hi > lo
    except Exception:
        valid = False
    if valid and str(r.get('source_status','')).upper() == 'CONFIRMED':
        coverage[s].add(tf)
    else:
        bad_zone_rows.append((s,tf,r.get('from'),r.get('to'),r.get('source_status')))
missing_zone = {s:[tf for tf in ZONE_TFS if tf not in coverage[s]] for s in ALTS}
missing_zone = {s:v for s,v in missing_zone.items() if v}
check('STREFY_77_Z_77', not missing_zone, missing_zone)
check('STREFY_ZAKRESY_POPRAWNE', not bad_zone_rows, bad_zone_rows[:20])
zone_audit = load_json('audit/V8_ZONE_FINAL_77_OF_77.json')
check('AUDYT_STREF_77_Z_77', zone_audit.get('ready_points') == 77 and zone_audit.get('total_points') == 77 and zone_audit.get('assets_complete') == 11, zone_audit.get('percent'))

# 3. LONG
long = load_json('crypto_data_hub/ALT_DECISION_ENGINE.json')
check('LONG_WERSJA_V1', long.get('engine') == 'ALT_DECISION_ENGINE_v1.0', long.get('engine'))
check('LONG_11_ALTOW', long.get('asset_count') == 11 and long.get('universe') == ALTS, long.get('universe'))
check('LONG_BEZ_AUTOMATYCZNYCH_TRANSAKCJI', (long.get('rules') or {}).get('execution_connected') is False, (long.get('rules') or {}).get('execution_connected'))
check('LONG_NIE_ZGADUJE_STREF', (long.get('rules') or {}).get('no_zone_guessing') is True, (long.get('rules') or {}).get('no_zone_guessing'))
long_map = {a.get('symbol'):a for a in long.get('assets',[])}
for s in ALTS:
    a = long_map.get(s,{})
    z = a.get('zones') or {}
    check(f'LONG_{s}_TECHNIKA', a.get('technical_ready') is True, a.get('technical_ready'))
    check(f'LONG_{s}_STREFY_7_7', z.get('complete_7_of_7') is True and not z.get('missing_timeframes'), (z.get('complete_7_of_7'),z.get('missing_timeframes')))
    if str(a.get('decision','')).startswith('KUP'):
        check(f'LONG_{s}_KUP_BEZ_BLOKAD', not a.get('blockers') and not a.get('entry_blockers'), (a.get('blockers'),a.get('entry_blockers')))

# 4. TACTICAL
tact = load_json('tactical_engine/TACTICAL_ENGINE.json')
check('TACTICAL_WERSJA_V1', tact.get('engine') == 'V8_TACTICAL_ENGINE_v1.0', tact.get('engine'))
check('TACTICAL_BTC_PLUS_11', tact.get('asset_count') == 12 and tact.get('universe') == TACTICAL, tact.get('universe'))
check('TACTICAL_BEZ_SPOLEK', tact.get('stocks_included') is False, tact.get('stocks_included'))
check('TACTICAL_BEZ_AUTOMATYCZNYCH_TRANSAKCJI', tact.get('not_execution_connected') is True, tact.get('not_execution_connected'))
tact_map = {a.get('symbol'):a for a in tact.get('assets',[])}
for s in TACTICAL:
    a = tact_map.get(s,{})
    check(f'TACT_{s}_QA', a.get('qa') == 'PASS', a.get('qa'))
    tfs = a.get('timeframes') or {}
    check(f'TACT_{s}_TF_1H_4H_1D', all(tf in tfs for tf in TACTICAL_TFS), list(tfs))
    for tf in TACTICAL_TFS:
        x = tfs.get(tf,{})
        check(f'TACT_{s}_{tf}_ZAMKNIETA_SWIECA', x.get('closed_bar_only') is True, x.get('closed_bar_only'))
        check(f'TACT_{s}_{tf}_NIE_PRZETERMINOWANE', x.get('stale') is False, x.get('stale'))
        check(f'TACT_{s}_{tf}_RSI', finite(x.get('rsi14')) and 0 <= float(x.get('rsi14')) <= 100, x.get('rsi14'))
        check(f'TACT_{s}_{tf}_MFI', finite(x.get('mfi14')) and 0 <= float(x.get('mfi14')) <= 100, x.get('mfi14'))
        check(f'TACT_{s}_{tf}_FOMO', finite(x.get('fomo_score_0_10')) and 0 <= float(x.get('fomo_score_0_10')) <= 10, x.get('fomo_score_0_10'))

tr = load_json('tactical_engine/TACTICAL_READINESS.json')
check('TACTICAL_GOTOWOSC_12_Z_12', tr.get('asset_count') == 12 and tr.get('all_assets_ready') is True, (tr.get('asset_count'),tr.get('all_assets_ready')))
check('TACTICAL_GOTOWOSC_TF', tr.get('timeframes') == TACTICAL_TFS, tr.get('timeframes'))
check('TACTICAL_TRADINGVIEW_ODLOZONE', tr.get('tradingview_connected') is False, tr.get('tradingview_connected'))
check('TACTICAL_EXECUTION_OFF', tr.get('execution_connected') is False, tr.get('execution_connected'))

# 5. Warstwy pochodne LONG/master — muszą być zgodne z finalnym stanem, nie mogą być stare
ready = load_json('crypto_data_hub/ALT_ENGINE_READINESS.json')
ready_assets = {a.get('symbol'):a for a in ready.get('assets',[])}
check('READINESS_11_ALTOW', set(ready_assets) == set(ALTS), sorted(ready_assets))
check('READINESS_11_GOTOWYCH', all((ready_assets.get(s,{}) or {}).get('readiness_status') == 'PRODUCTION_DATA_READY' for s in ALTS), {s:(ready_assets.get(s,{}) or {}).get('readiness_status') for s in ALTS})
check('READINESS_STREFY_11_GOTOWE', all((ready_assets.get(s,{}) or {}).get('zones_full_ready') is True for s in ALTS), {s:(ready_assets.get(s,{}) or {}).get('zones_full_ready') for s in ALTS})

master = load_json('crypto_data_hub/ALT_ENGINE_MASTER_CHECKPOINT.json')
check('MASTER_NIE_JEST_NIEKOMPLETNY', master.get('status') != 'CORE_ALT_ENGINE_INCOMPLETE', master.get('status'))
check('MASTER_11_ALTOW_GOTOWYCH', master.get('production_assets_ready') == 11, master.get('production_assets_ready'))

# 6. ETF / instytucje
etf = load_json('institutional_data_hub/ETF_BTC_ETH_STATUS.json')
assets_etf = etf.get('assets') or {}
check('ETF_BTC_ETH', set(assets_etf) == {'BTC','ETH'}, sorted(assets_etf))
for s in ['BTC','ETH']:
    rules = (assets_etf.get(s,{}) or {}).get('rules') or {}
    check(f'ETF_{s}_DZIS_NIE_FINAL', rules.get('today_never_treated_as_final_same_day') is True, rules)
    check(f'ETF_{s}_TREND_BEZ_DZIS', rules.get('closed_trend_excludes_today') is True, rules)
    check(f'ETF_{s}_ZERO_NIE_FINALNE_ZERO', rules.get('zero_today_does_not_mean_final_zero') is True, rules)
conf = load_json('institutional_data_hub/ETF_BTC_ETH_CONFIRMATION.json')
check('ETF_POTWIERDZENIE_BTC_ETH', set((conf.get('assets') or {}).keys()) == {'BTC','ETH'}, sorted((conf.get('assets') or {}).keys()))

# 7. LAB
lab = load_json('lab/LAB_STATUS.json')
check('LAB_SZYBKA_ANALIZA', lab.get('fast_mode_ready') is True and lab.get('fast_multitimeframe_enabled') is True, lab.get('fast_mode_ready'))
check('LAB_GLEBOKA_OBSERWACJA', lab.get('deep_mode_ready') is True and lab.get('deep_comparison_enabled') is True, lab.get('deep_mode_ready'))
check('LAB_PO_POLSKU', lab.get('polish_user_language') is True, lab.get('polish_user_language'))
check('LAB_BEZ_EXECUTION', lab.get('execution_connection') is False and lab.get('portfolio_connection') is False, (lab.get('execution_connection'),lab.get('portfolio_connection')))
check('LAB_CHECKPOINTY_KRYPTO', lab.get('crypto_checkpoints') == ['D0','D1','D3','D7','D30'], lab.get('crypto_checkpoints'))
check('LAB_CHECKPOINTY_SPOLKI', lab.get('stock_checkpoints') == ['D0','D7','D30'], lab.get('stock_checkpoints'))

# 8. On-chain / flow
onchain = load_json('crypto_data_hub/ONCHAIN_ACTIVITY.json')
check('ONCHAIN_SILNIK', str(onchain.get('engine','')).startswith('ONCHAIN_ACTIVITY_'), onchain.get('engine'))
check('ONCHAIN_MA_AKTYWA', isinstance(onchain.get('assets'),list) and len(onchain.get('assets')) > 0, len(onchain.get('assets') or []))

# 9. Walidacja i pliki poboczne
required_files = [
    'tactical_validation/TACTICAL_THRESHOLD_LAB.json',
    'tactical_validation/TACTICAL_VALIDATION.json',
    'tactical_validation/TACTICAL_VALIDATION_SUMMARY.csv',
    'tactical_engine/TACTICAL_MACD_EXTREMES.csv',
    'tactical_engine/TACTICAL_EXTREME_CONFLUENCE.csv',
    'market_reader/TACTICAL_CONFLUENCE.csv',
    'google_sheets/DUAL_PANEL.csv',
    'google_sheets/DUAL_ENGINE_MACHINE_ROOM.csv',
    'google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL.txt',
    'lab/LAB_REPORT.json',
    'lab/LAB_DEEP_REPORT.json',
    'lab/LAB_CHECKPOINTS.csv',
    'institutional_data_hub/ETF_BTC_ETH_HISTORY.csv',
    'institutional_data_hub/ETF_PRICE_DIVERGENCE_LATEST.md',
]
for p in required_files:
    check(f'PLIK_POBoczny_{p}', (ROOT/p).exists(), 'OK' if (ROOT/p).exists() else 'BRAK')

bridge_path = ROOT/'google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL.txt'
bridge = bridge_path.read_text(encoding='utf-8') if bridge_path.exists() else ''
check('SHEETS_MOST_LONG', 'ALT_ENGINE_MASTER_CHECKPOINT.json' in bridge, 'ALT_ENGINE_MASTER_CHECKPOINT.json')
check('SHEETS_MOST_TACTICAL', 'TACTICAL_ENGINE.json' in bridge and 'TACTICAL_READINESS.json' in bridge, 'TACTICAL')
check('SHEETS_MOST_ETF', 'ETF_BTC_ETH_STATUS.json' in bridge and 'ETF_BTC_ETH_HISTORY.csv' in bridge, 'ETF')
check('SHEETS_BEZ_BROKERA', 'No broker execution' in bridge or 'no broker execution' in bridge.lower(), 'kontrola tekstu bezpieczeństwa')

# 10. Końcowy status
final_md_path = ROOT/'audit/V8_FINAL_READINESS_LATEST.md'
final_md = final_md_path.read_text(encoding='utf-8') if final_md_path.exists() else ''
check('STATUS_KONCOWY_100', 'Gotowość całego projektu: 100%' in final_md, final_md[:120])
check('STATUS_TRADINGVIEW_ODLOZONE', 'TradingView' in final_md and 'później' in final_md, 'TradingView później')

failed = [c for c in checks if not c['pass']]
result = {
    'generated_at_utc': datetime.now(timezone.utc).isoformat(),
    'pass_number': PASS_NO,
    'checks_total': len(checks),
    'checks_passed': len(checks)-len(failed),
    'checks_failed': len(failed),
    'status_pl': 'ZAKOŃCZONE POPRAWNIE' if not failed else 'WYKRYTO ELEMENTY DO POPRAWY',
    'failed_checks': failed,
    'checks': checks,
}
Path('audit').mkdir(exist_ok=True)
json_path = ROOT/f'audit/V8_FULL_AUDIT_PASS_{PASS_NO}.json'
md_path = ROOT/f'audit/V8_FULL_AUDIT_PASS_{PASS_NO}.md'
json_path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
lines = [
    f'# V8 — PEŁNY TEST {PASS_NO}/2',
    '',
    f"**Status: {result['status_pl']}**",
    f"**Kontrole: {result['checks_passed']}/{result['checks_total']} poprawne.**",
    '',
]
if failed:
    lines += ['## Wykryte problemy'] + [f"- {x['check']}: {x['detail']}" for x in failed]
else:
    lines += ['Wszystkie sprawdzane obszary przeszły kontrolę poprawnie.']
md_path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
if failed:
    raise SystemExit(1)
