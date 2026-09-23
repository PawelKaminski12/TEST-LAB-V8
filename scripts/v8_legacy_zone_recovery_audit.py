#!/usr/bin/env python3
import csv, json
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
MIG = ROOT / 'config' / 'alt_zone_migration.csv'
ZONES = ROOT / 'config' / 'alt_zones.csv'
OUT_JSON = ROOT / 'audit' / 'LEGACY_ZONE_RECOVERY_STATUS.json'
OUT_MD = ROOT / 'audit' / 'LEGACY_ZONE_RECOVERY_LATEST.md'

REQUIRED = ['1D','2D','3D','4D','5D','1T','2T']
TARGETS = ['RENDER','FLOKI','PEPE','SPX6900','XRP','XLM','HBAR']


def read_csv(path):
    with path.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def b(v):
    return str(v).strip().lower() == 'true'

mig = read_csv(MIG)
zones = read_csv(ZONES)

confirmed = defaultdict(lambda: defaultdict(int))
for r in zones:
    if str(r.get('source_status','')).upper() != 'CONFIRMED':
        continue
    s = str(r.get('symbol','')).upper().strip()
    tf = str(r.get('timeframe','')).upper().strip()
    if s and tf:
        confirmed[s][tf] += 1

by = defaultdict(dict)
for r in mig:
    s = str(r.get('symbol','')).upper().strip()
    tf = str(r.get('timeframe','')).upper().strip()
    if s in TARGETS and tf in REQUIRED:
        by[s][tf] = r

assets = []
for s in TARGETS:
    rows = by.get(s,{})
    tf_rows = []
    numeric_count = 0
    source_count = 0
    for tf in REQUIRED:
        r = rows.get(tf,{})
        source_found = b(r.get('source_found',False))
        numeric_ready = b(r.get('numeric_ready',False))
        actual_confirmed = confirmed[s][tf] > 0
        # Twarda zasada: numeric_ready może być prawdą tylko gdy istnieje CONFIRMED w alt_zones.
        effective_numeric = numeric_ready and actual_confirmed
        if source_found:
            source_count += 1
        if effective_numeric:
            numeric_count += 1
        tf_rows.append({
            'timeframe': tf,
            'source_found': source_found,
            'numeric_ready_declared': numeric_ready,
            'confirmed_rows_in_alt_zones': confirmed[s][tf],
            'numeric_ready_effective': effective_numeric,
            'status_pl': r.get('status_pl','BRAK REKORDU'),
            'source_note': r.get('source_note','')
        })

    if numeric_count == 7:
        overall = 'DOMKNIĘTE — 7/7 INTERWAŁÓW LICZBOWO GOTOWYCH'
    elif source_count == 7:
        overall = 'ŹRÓDŁA 7/7 POTWIERDZONE — TRWA ODZYSKIWANIE LICZB'
    elif source_count > 0:
        overall = 'CZĘŚCIOWO ODZYSKANE — NIE PROSIMY JESZCZE O NOWE DANE'
    else:
        overall = 'BRAK ODZYSKANEGO ŹRÓDŁA — DOPIERO TU MOŻE BYĆ POTRZEBNY NOWY SCREEN'

    assets.append({
        'symbol': s,
        'source_intervals': source_count,
        'numeric_intervals': numeric_count,
        'required_intervals': 7,
        'overall_status_pl': overall,
        'timeframes': tf_rows,
    })

# QA: nie pozwalamy, aby migracja mówiła numeric_ready=true bez faktycznej strefy CONFIRMED.
qa_errors = []
for a in assets:
    for r in a['timeframes']:
        if r['numeric_ready_declared'] and not r['numeric_ready_effective']:
            qa_errors.append(f"{a['symbol']} {r['timeframe']}: numeric_ready=true bez CONFIRMED w alt_zones.csv")

summary = {
    'engine': 'V8_LEGACY_ZONE_RECOVERY_AUDIT_v1.0',
    'required_timeframes': REQUIRED,
    'policy_pl': 'Najpierw odzyskujemy stare źródła. Nie zgadujemy poziomów i nie prosimy o nowe screeny, dopóki istnieje potwierdzona ścieżka odzyskania.',
    'assets': assets,
    'qa': {
        'status_pl': 'ZAKOŃCZONE POPRAWNIE' if not qa_errors else 'BŁĄD SPÓJNOŚCI',
        'errors': qa_errors,
    }
}
OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

lines = [
    '# V8 — ODZYSKIWANIE STARYCH STREF',
    '',
    f"**Kontrola spójności: {summary['qa']['status_pl']}**",
    '',
    'Zasada: **najpierw odzyskujemy stare dane; nie tworzymy poziomów na oko.**',
    ''
]
for a in assets:
    lines += [
        f"## {a['symbol']}",
        f"**{a['overall_status_pl']}**",
        f"- potwierdzone źródła: {a['source_intervals']}/7",
        f"- liczbowo gotowe w V8: {a['numeric_intervals']}/7",
    ]
    missing_numeric = [r['timeframe'] for r in a['timeframes'] if not r['numeric_ready_effective']]
    if missing_numeric:
        lines.append('- do odzyskania liczbowego: ' + ', '.join(missing_numeric))
    else:
        lines.append('- brak luk liczbowych')
    lines.append('')
if qa_errors:
    lines += ['## BŁĘDY SPÓJNOŚCI',''] + [f'- {x}' for x in qa_errors]

OUT_MD.write_text('\n'.join(lines).rstrip() + '\n', encoding='utf-8')
print(summary['qa']['status_pl'])
for a in assets:
    print(f"{a['symbol']}: źródła {a['source_intervals']}/7, liczby {a['numeric_intervals']}/7")
if qa_errors:
    raise SystemExit(1)
