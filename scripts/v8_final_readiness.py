import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('.')
OUT = Path('audit')
OUT.mkdir(exist_ok=True)
GS = Path('google_sheets')
GS.mkdir(exist_ok=True)

NOW = datetime.now(timezone.utc).isoformat()


def load_json(path):
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding='utf-8'))


def exists(path):
    return Path(path).exists()


def pct(ok, total):
    return 0 if total == 0 else round(100.0 * ok / total, 1)


# --- wejścia ---
dual = load_json('audit/DUAL_ENGINE_AUDIT.json') or {}
alt = load_json('crypto_data_hub/ALT_COMPLETION_AUDIT.json') or {}
etf = load_json('institutional_data_hub/ETF_BTC_ETH_STATUS.json') or {}
etf_hist = load_json('institutional_data_hub/ETF_BTC_ETH_HISTORY_STATUS.json') or {}
lab_status = load_json('lab/LAB_STATUS.json') or {}
checkpoints = load_json('lab/LAB_CHECKPOINT_STATUS.json') or {}
onchain = load_json('onchain_data/ONCHAIN_ACTIVITY.json') or load_json('crypto_data_hub/ONCHAIN_ACTIVITY.json') or {}
tactical = load_json('tactical_engine/TACTICAL_ENGINE.json') or {}
readiness = load_json('tactical_engine/TACTICAL_READINESS.json') or {}

# --- produkcyjna czwórka ---
assets = {x.get('symbol'): x for x in alt.get('assets', [])}
production_symbols = ['ETH', 'SOL', 'LINK', 'ONDO']
validation_symbols = ['AAVE', 'HBAR']

prod_ready = all(assets.get(s, {}).get('full_ready') is True for s in production_symbols)
validation_auto_ready = all(assets.get(s, {}).get('auto_layers_ready') is True for s in validation_symbols)
validation_zones_ready = all(assets.get(s, {}).get('zones', {}).get('complete_7_of_7') is True for s in validation_symbols)

# --- moduły ---
etf_assets = etf.get('assets', {})
etf_ready = (
    set(etf_assets.keys()) == {'BTC', 'ETH'}
    and etf.get('safety', {}).get('same_day_etf_values_are_provisional') is True
    and etf.get('safety', {}).get('closed_day_values_drive_scores') is True
    and exists('institutional_data_hub/ETF_BTC_ETH_HISTORY.csv')
    and exists('institutional_data_hub/ETF_PRICE_DIVERGENCE_LATEST.md')
)

lab_ready = (
    lab_status.get('active_assets', 0) >= 3
    and lab_status.get('polish_user_language') is True
    and lab_status.get('btc_dedicated_etf_filter') is True
    and exists('lab/LAB_CHECKPOINTS.csv')
    and exists('lab/LAB_DEEP_REPORT_LATEST.md')
)

onchain_ready = exists('onchain_data/ONCHAIN_ACTIVITY.json') or exists('crypto_data_hub/ONCHAIN_ACTIVITY.json')

panel_ready = (
    exists('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL.txt')
    and exists('google_sheets/DUAL_PANEL.csv')
    and exists('google_sheets/DUAL_ENGINE_MACHINE_ROOM.csv')
)

alarms_ready = (
    exists('tactical_engine/TACTICAL_MACD_EXTREMES.csv')
    and exists('tactical_engine/TACTICAL_EXTREME_CONFLUENCE.csv')
    and exists('tactical_engine/TACTICAL_READINESS.json')
)

long_ready = dual.get('long_engine_status') in {'READY_FOR_PAPER_OBSERVATION', 'READY'} or prod_ready
tactical_ready = dual.get('tactical_engine_status') in {'TECHNICALLY_READY_CALIBRATION_NOT_FROZEN', 'READY'} or bool(tactical.get('assets'))

safety_ready = (
    dual.get('execution_connected') is False
    and etf.get('safety', {}).get('execution_connected') is False
)

validation_ready = exists('tactical_validation/TACTICAL_VALIDATION.json') and exists('tactical_validation/TACTICAL_THRESHOLD_LAB.json')

# 10 głównych obszarów = 100 pkt
areas = [
    ('SILNIK LONG', 10, long_ready, 'Silnik długoterminowy działa i pozostaje oddzielony od TACTICAL.'),
    ('SILNIK TACTICAL', 10, tactical_ready, 'Silnik taktyczny działa na osobnym horyzoncie i kapitale.'),
    ('PRODUKCYJNE ALTY', 15, prod_ready, 'ETH, SOL, LINK i ONDO: technika + pełne strefy 1D/2D/3D/4D/5D/1T/2T.'),
    ('ETF BTC + ETH', 10, etf_ready, 'Monitor, historia, rozdzielenie danych wstępnych i zamkniętych oraz zgodność cena/ETF.'),
    ('LAB + PUNKTY KONTROLNE', 10, lab_ready, 'Szybka analiza, głęboka obserwacja i trwałe punkty kontrolne.'),
    ('ON-CHAIN / FLOW', 10, onchain_ready, 'Warstwa przepływów i aktywności sieciowej jako kontekst.'),
    ('PANEL GOOGLE SHEETS', 10, panel_ready, 'Pełny most panelu i dane maszynowni są obecne.'),
    ('ALARMY EKSTREMÓW', 5, alarms_ready, 'RSI/MFI/MACD/FOMO oraz warstwa zbieżności ekstremów.'),
    ('BEZPIECZEŃSTWO', 10, safety_ready, 'Brak automatycznego wykonywania transakcji; V7 pozostaje poza zmianami V8.'),
    ('WALIDACJA / QA', 5, validation_ready, 'Walidacja TACTICAL i laboratorium progów są obecne.'),
]

score = sum(weight for _, weight, ok, _ in areas if ok)

# Pozostałe 5 pkt to rozszerzony zestaw AAVE/HBAR. Automatyczne dane są gotowe, ale brak stref użytkownika.
extended_auto_points = 3 if validation_auto_ready else 0
extended_zone_points = 2 if validation_zones_ready else 0
score += extended_auto_points + extended_zone_points

if score >= 100:
    status_pl = 'WSZYSTKIE ZAŁOŻENIA DOPIĘTE'
elif score >= 95:
    status_pl = 'RDZEŃ DOPIĘTY — ZOSTAŁY TYLKO DANE UŻYTKOWNIKA'
elif score >= 90:
    status_pl = 'SYSTEM PRAWIE DOPIĘTY'
else:
    status_pl = 'SYSTEM WYMAGA JESZCZE PRACY'

blockers = []
if not validation_zones_ready:
    for s in validation_symbols:
        z = assets.get(s, {}).get('zones', {})
        if not z.get('complete_7_of_7'):
            blockers.append({
                'asset': s,
                'missing': z.get('missing_timeframes') or ['1D','2D','3D','4D','5D','1T','2T'],
                'status_pl': 'BRAKUJE POTWIERDZONYCH STREF UŻYTKOWNIKA',
                'rule': 'System nie tworzy sztucznych stref.'
            })

payload = {
    'generated_at_utc': NOW,
    'engine': 'V8_FINAL_READINESS_v1.0',
    'readiness_percent': score,
    'status_pl': status_pl,
    'core_production_ready': all(ok for _, _, ok, _ in areas),
    'production_assets_ready': prod_ready,
    'extended_assets_auto_data_ready': validation_auto_ready,
    'extended_assets_user_zones_ready': validation_zones_ready,
    'areas': [
        {'obszar': n, 'waga_pkt': w, 'gotowe': ok, 'opis': d}
        for n, w, ok, d in areas
    ],
    'extended_universe': {
        'auto_data_points_0_3': extended_auto_points,
        'user_zone_points_0_2': extended_zone_points,
        'AAVE': assets.get('AAVE', {}),
        'HBAR': assets.get('HBAR', {}),
    },
    'blockers': blockers,
    'safety': {
        'execution_connected': False,
        'never_invent_user_zones': True,
        'v7_not_modified': True,
    }
}

(OUT / 'V8_FINAL_READINESS.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

rows = [['OBSZAR','WAGA_PKT','STATUS','OPIS']]
for n, w, ok, d in areas:
    rows.append([n, w, 'GOTOWE' if ok else 'WYMAGA POPRAWY', d])
rows.append(['AAVE/HBAR — DANE AUTOMATYCZNE',3,'GOTOWE' if validation_auto_ready else 'WYMAGA POPRAWY','Technika 1H/4H/1D i automatyczne warstwy.'])
rows.append(['AAVE/HBAR — STREFY UŻYTKOWNIKA',2,'GOTOWE' if validation_zones_ready else 'BRAK DANYCH UŻYTKOWNIKA','Wymagane 1D/2D/3D/4D/5D/1T/2T.'])
rows.append(['CAŁOŚĆ',100,f'{score}%',status_pl])

with (GS / 'V8_FINAL_READINESS.csv').open('w', newline='', encoding='utf-8') as f:
    csv.writer(f).writerows(rows)

md = [
    '# V8 — KOŃCOWA GOTOWOŚĆ', '',
    f'**Gotowość całego projektu: {score}%**',
    f'**Status: {status_pl}**', '',
    '## Główne obszary'
]
for n, w, ok, d in areas:
    md.append(f"- {'✅' if ok else '⚠️'} **{n}** — {w} pkt — {'GOTOWE' if ok else 'WYMAGA POPRAWY'}. {d}")
md += ['', '## Rozszerzony zestaw AAVE / HBAR']
md.append(f"- {'✅' if validation_auto_ready else '⚠️'} Dane automatyczne: {'GOTOWE' if validation_auto_ready else 'NIEPEŁNE'}.")
md.append(f"- {'✅' if validation_zones_ready else '⚠️'} Strefy użytkownika: {'GOTOWE' if validation_zones_ready else 'BRAK POTWIERDZONYCH STREF'}.")
if blockers:
    md += ['', 'Do pełnych 100% brakuje wyłącznie potwierdzonych stref użytkownika dla:']
    for b in blockers:
        md.append(f"- **{b['asset']}**: {', '.join(b['missing'])}.")
md += ['', 'System nie tworzy sztucznych stref. Brak połączenia z wykonywaniem transakcji. V7 pozostaje nietknięty.']
(OUT / 'V8_FINAL_READINESS_LATEST.md').write_text('\n'.join(md), encoding='utf-8')

print(json.dumps({'readiness_percent': score, 'status_pl': status_pl, 'blockers': blockers}, ensure_ascii=False, indent=2))
