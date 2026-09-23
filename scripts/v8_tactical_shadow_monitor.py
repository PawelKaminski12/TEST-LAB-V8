#!/usr/bin/env python3
import csv, json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / 'tactical_engine' / 'TACTICAL_ENGINE.json'
LAB = ROOT / 'tactical_validation' / 'TACTICAL_THRESHOLD_LAB.json'
OUTDIR = ROOT / 'tactical_validation'
LATEST_JSON = OUTDIR / 'TACTICAL_SHADOW_LATEST.json'
LATEST_CSV = OUTDIR / 'TACTICAL_SHADOW_LATEST.csv'
HISTORY_CSV = OUTDIR / 'TACTICAL_SHADOW_HISTORY.csv'
REPORT_MD = ROOT / 'audit' / 'V8_TACTICAL_SHADOW_MONITOR.md'

POSITIVE_PROD = {'LONG_SETUP_WATCH','LONG_SETUP_RETEST','WATCH_BREAKOUT'}


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def fnum(v):
    try:
        return float(v)
    except Exception:
        return None


def evaluate(asset, cand):
    symbol = asset.get('symbol','')
    tf = asset.get('timeframes') or {}
    h1 = tf.get('1H') or {}
    h4 = tf.get('4H') or {}
    score = fnum(asset.get('tactical_score_0_10'))
    fomo1 = fnum(h1.get('fomo_score_0_10'))
    fomo4 = fnum(h4.get('fomo_score_0_10'))
    trend4 = fnum(h4.get('trend_score_0_4'))
    rsi4 = fnum(h4.get('rsi14'))
    close4 = fnum(h4.get('close'))
    status = str(asset.get('tactical_status') or '')

    if symbol == 'BTC':
        return {
            'symbol': symbol, 'scope': 'MARKET_REGIME_ONLY', 'shadow_signal': 'N/A',
            'production_status': status, 'production_positive': status in POSITIVE_PROD,
            'score': score, 'fomo_1h': fomo1, 'fomo_4h': fomo4,
            'trend_4h': trend4, 'rsi_4h': rsi4, 'close_4h': close4,
            'reason': 'BTC pozostaje reżimem rynku; kandydat progowy dotyczy altów.'
        }

    checks = [
        ('score', score is not None and score >= cand['score_min']),
        ('fomo1', fomo1 is not None and fomo1 <= cand['fomo_max']),
        ('fomo4', fomo4 is not None and fomo4 <= cand['fomo_max']),
        ('trend4', trend4 is not None and trend4 >= cand['trend4_min']),
        ('rsi4', rsi4 is not None and cand['rsi_lo'] <= rsi4 <= cand['rsi_hi']),
    ]
    passed = all(ok for _, ok in checks)
    failed = [name for name, ok in checks if not ok]
    return {
        'symbol': symbol, 'scope': 'SHADOW_ALT', 'shadow_signal': 'PASS' if passed else 'HOLD',
        'production_status': status, 'production_positive': status in POSITIVE_PROD,
        'score': score, 'fomo_1h': fomo1, 'fomo_4h': fomo4,
        'trend_4h': trend4, 'rsi_4h': rsi4, 'close_4h': close4,
        'reason': 'warunki kandydata spełnione' if passed else 'blokady: ' + ','.join(failed)
    }


def append_history(snapshot_time, rows):
    fields = ['snapshot_time_utc','symbol','scope','shadow_signal','production_status','production_positive','score','fomo_1h','fomo_4h','trend_4h','rsi_4h','close_4h','reason']
    existing = set()
    if HISTORY_CSV.exists():
        with HISTORY_CSV.open(encoding='utf-8', newline='') as f:
            for r in csv.DictReader(f):
                existing.add((r.get('snapshot_time_utc',''), r.get('symbol','')))
    write_header = not HISTORY_CSV.exists()
    with HISTORY_CSV.open('a', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            w.writeheader()
        for r in rows:
            key = (snapshot_time, r['symbol'])
            if key in existing:
                continue
            row = {'snapshot_time_utc': snapshot_time, **r}
            w.writerow({k: row.get(k,'') for k in fields})


def main():
    engine = load(ENGINE)
    lab = load(LAB)
    cand = lab.get('candidate_for_next_validation') or {}
    required = ['score_min','fomo_max','trend4_min','rsi_lo','rsi_hi']
    missing = [k for k in required if k not in cand]
    if missing:
        raise SystemExit('Brak progów kandydata: ' + ','.join(missing))

    rows = [evaluate(a, cand) for a in engine.get('assets',[])]
    alt_rows = [r for r in rows if r['scope'] == 'SHADOW_ALT']
    if len(alt_rows) != 13:
        raise SystemExit(f'Oczekiwano 13 altów shadow, jest {len(alt_rows)}')

    snapshot_time = engine.get('generated_at_utc') or datetime.now(timezone.utc).isoformat()
    pass_rows = [r for r in alt_rows if r['shadow_signal'] == 'PASS']
    prod_pos = [r for r in alt_rows if r['production_positive']]
    divergence = [r for r in alt_rows if (r['shadow_signal']=='PASS') != bool(r['production_positive'])]

    payload = {
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'engine_snapshot_utc': snapshot_time,
        'engine': 'V8_TACTICAL_SHADOW_MONITOR_v1.0',
        'research_only': True,
        'deploy_block': True,
        'auto_execution': False,
        'production_thresholds_modified': False,
        'candidate': {k:cand[k] for k in required},
        'alt_count': len(alt_rows),
        'shadow_pass_count': len(pass_rows),
        'production_positive_count': len(prod_pos),
        'divergence_count': len(divergence),
        'promotion_ready': False,
        'promotion_note': 'Shadow monitor zbiera obserwacje. Kandydat pozostaje DEPLOY HOLD do osobnej przyszłej bramki wielookresowej.',
        'rows': rows,
    }
    LATEST_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    fields = ['symbol','scope','shadow_signal','production_status','production_positive','score','fomo_1h','fomo_4h','trend_4h','rsi_4h','close_4h','reason']
    with LATEST_CSV.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows([{k:r.get(k,'') for k in fields} for r in rows])
    append_history(snapshot_time, rows)

    lines = [
        '# V8 TACTICAL — SHADOW MONITOR KANDYDATA', '',
        'Status: **AKTYWNY BADAWCZO — DEPLOY HOLD**', '',
        f'- Snapshot silnika: {snapshot_time}',
        f'- Alty monitorowane: {len(alt_rows)}',
        f'- Shadow PASS teraz: {len(pass_rows)}',
        f'- Produkcyjne pozytywne statusy teraz: {len(prod_pos)}',
        f'- Rozbieżności shadow vs produkcja: {len(divergence)}', '',
        '## Kandydat',
        f"- score >= {cand['score_min']}",
        f"- FOMO 1H i 4H <= {cand['fomo_max']}",
        f"- trend 4H >= {cand['trend4_min']}",
        f"- RSI 4H = {cand['rsi_lo']}–{cand['rsi_hi']}", '',
        '## Zabezpieczenia',
        '- research_only = true',
        '- deploy_block = true',
        '- AUTO EXECUTION = OFF',
        '- Produkcyjne progi Tactical nie są modyfikowane.',
        '- Wyniki shadow są zapisywane osobno i służą tylko do dalszej walidacji.', '',
        '## Bieżące sygnały shadow',
    ]
    for r in alt_rows:
        lines.append(f"- {r['symbol']}: {r['shadow_signal']} | prod={r['production_status']} | {r['reason']}")
    REPORT_MD.write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps({k:payload[k] for k in ['alt_count','shadow_pass_count','production_positive_count','divergence_count','promotion_ready']}, ensure_ascii=False))

if __name__ == '__main__':
    main()
