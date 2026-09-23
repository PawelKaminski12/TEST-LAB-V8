import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path('lab')
REPORT_PATH = ROOT / 'LAB_REPORT.json'
CFG_PATH = Path('config/lab_assets.csv')
CSV_PATH = ROOT / 'LAB_CHECKPOINTS.csv'
JSON_PATH = ROOT / 'LAB_CHECKPOINTS.json'
STATUS_PATH = ROOT / 'LAB_CHECKPOINT_STATUS.json'
NOW = datetime.now(timezone.utc)

CRYPTO_POINTS = [('D0', 0.0), ('D1', 1.0), ('D3', 3.0), ('D7', 7.0), ('D30', 30.0)]
STOCK_POINTS = [('D0', 0.0), ('D7', 7.0), ('D30', 30.0)]


def sf(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def parse_dt(v):
    if v is None:
        return None
    try:
        return datetime.fromisoformat(str(v).replace('Z', '+00:00')).astimezone(timezone.utc)
    except Exception:
        return None


def canonical_hash(obj):
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def read_existing():
    if not CSV_PATH.exists() or CSV_PATH.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(CSV_PATH)
    except Exception:
        return pd.DataFrame()


def due_points(asset_type, elapsed_days):
    points = CRYPTO_POINTS if asset_type in ('CRYPTO', 'MEME') else STOCK_POINTS
    return [name for name, day in points if elapsed_days >= day]


def selected_snapshot(report):
    tech = report.get('technical') or {}
    t1 = tech.get('1H') or {}
    t4 = tech.get('4H') or {}
    td = tech.get('1D') or {}
    market = report.get('crypto_market_context') or {}
    onchain = report.get('onchain_context') or {}
    etf_btc = report.get('btc_etf_context') or {}
    etf_eth = report.get('eth_etf_context') or {}
    fast = report.get('fast_analysis') or {}
    engine = report.get('existing_engine_context') or {}
    fundamentals = report.get('stock_fundamentals') or {}
    return {
        'symbol': report.get('symbol'),
        'asset_type': report.get('asset_type'),
        'source_symbol': report.get('source_symbol'),
        'report_generated_at_utc': report.get('generated_at_utc'),
        'data_quality_0_100': report.get('data_quality_0_100'),
        'data_status': report.get('data_status'),
        'fast_score_0_10': fast.get('score_0_10'),
        'fast_label': fast.get('label'),
        'price_1d': td.get('price'),
        'trend_1h': t1.get('trend_0_4'),
        'trend_4h': t4.get('trend_0_4'),
        'trend_1d': td.get('trend_0_4'),
        'rsi_1h': t1.get('rsi14'),
        'rsi_4h': t4.get('rsi14'),
        'rsi_1d': td.get('rsi14'),
        'mfi_1h': t1.get('mfi14'),
        'mfi_4h': t4.get('mfi14'),
        'mfi_1d': td.get('mfi14'),
        'fomo_1h': t1.get('fomo_0_10'),
        'fomo_4h': t4.get('fomo_0_10'),
        'fomo_1d': td.get('fomo_0_10'),
        'market_phase': market.get('phase'),
        'rotation_score_0_10': market.get('rotation_score_0_10'),
        'btc_dominance_pct': market.get('btc_dominance_pct'),
        'eth_dominance_pct': market.get('eth_dominance_pct'),
        'eth_btc_20d_pct': market.get('eth_btc_20d_pct'),
        'btc_etf_5d_usdm': market.get('btc_etf_5d_usdm'),
        'btc_etf_20d_usdm': market.get('btc_etf_20d_usdm'),
        'eth_etf_5d_usdm': market.get('eth_etf_5d_usdm'),
        'eth_etf_20d_usdm': market.get('eth_etf_20d_usdm'),
        'btc_etf_label': etf_btc.get('label_pl'),
        'eth_etf_label': etf_eth.get('label_pl'),
        'onchain_long': onchain.get('long_score'),
        'onchain_tactical': onchain.get('tactical_score'),
        'engine_decision': engine.get('decision'),
        'revenue_growth': fundamentals.get('revenue_growth'),
        'earnings_growth': fundamentals.get('earnings_growth'),
        'free_cashflow': fundamentals.get('free_cashflow'),
    }


def main():
    if not REPORT_PATH.exists():
        raise SystemExit('Brak lab/LAB_REPORT.json')
    if not CFG_PATH.exists():
        raise SystemExit('Brak config/lab_assets.csv')

    report_payload = json.loads(REPORT_PATH.read_text(encoding='utf-8'))
    engine_version = report_payload.get('engine')
    cfg = pd.read_csv(CFG_PATH)
    cfg_map = {str(r['symbol']).upper().strip(): r for _, r in cfg.iterrows()}
    existing = read_existing()
    existing_keys = set()
    if not existing.empty and {'symbol', 'checkpoint'}.issubset(existing.columns):
        existing_keys = set(zip(existing['symbol'].astype(str).str.upper(), existing['checkpoint'].astype(str)))

    new_rows = []
    skipped_not_due = 0
    skipped_existing = 0
    deep_assets = 0

    for report in report_payload.get('reports', []):
        symbol = str(report.get('symbol') or '').upper().strip()
        if not symbol or symbol not in cfg_map:
            continue
        cfg_row = cfg_map[symbol]
        mode = str(cfg_row.get('mode', '')).upper().strip()
        if mode not in ('DEEP', 'BOTH'):
            continue
        if str(cfg_row.get('enabled', '')).lower().strip() != 'true':
            continue
        deep_assets += 1
        added = parse_dt(cfg_row.get('added_at_utc')) or parse_dt(report.get('generated_at_utc')) or NOW
        elapsed = max(0.0, (NOW - added).total_seconds() / 86400.0)
        asset_type = str(report.get('asset_type') or '').upper().strip()
        points = CRYPTO_POINTS if asset_type in ('CRYPTO', 'MEME') else STOCK_POINTS
        due = set(due_points(asset_type, elapsed))
        snap = selected_snapshot(report)
        snap_hash = canonical_hash(snap)

        for checkpoint, target_day in points:
            key = (symbol, checkpoint)
            if checkpoint not in due:
                skipped_not_due += 1
                continue
            if key in existing_keys:
                skipped_existing += 1
                continue
            delay = max(0.0, elapsed - target_day)
            new_rows.append({
                'snapshot_id': f'{symbol}-{checkpoint}-{snap_hash[:12]}',
                'symbol': symbol,
                'asset_type': asset_type,
                'checkpoint': checkpoint,
                'target_day': target_day,
                'added_at_utc': added.isoformat(),
                'captured_at_utc': NOW.isoformat(),
                'capture_delay_days': round(delay, 6),
                'source_report_generated_at_utc': report.get('generated_at_utc'),
                'engine_version': engine_version,
                'snapshot_sha256': snap_hash,
                'data_quality_0_100': report.get('data_quality_0_100'),
                'data_status': report.get('data_status'),
                'fast_score_0_10': (report.get('fast_analysis') or {}).get('score_0_10'),
                'fast_label': (report.get('fast_analysis') or {}).get('label'),
                'price': (report.get('technical_1D') or {}).get('price'),
                'trend_1D_0_4': (report.get('technical_1D') or {}).get('trend_0_4'),
                'rsi_1D': (report.get('technical_1D') or {}).get('rsi14'),
                'mfi_1D': (report.get('technical_1D') or {}).get('mfi14'),
                'fomo_1D_0_10': (report.get('technical_1D') or {}).get('fomo_0_10'),
                'onchain_long': (report.get('onchain_context') or {}).get('long_score'),
                'onchain_tactical': (report.get('onchain_context') or {}).get('tactical_score'),
                'engine_decision': (report.get('existing_engine_context') or {}).get('decision'),
                'btc_etf_label': (report.get('btc_etf_context') or {}).get('label_pl'),
                'eth_etf_label': (report.get('eth_etf_context') or {}).get('label_pl'),
                'immutable_after_write': True,
            })
            existing_keys.add(key)

    current = pd.DataFrame(new_rows)
    if existing.empty:
        combined = current.copy()
    elif current.empty:
        combined = existing.copy()
    else:
        combined = pd.concat([existing, current], ignore_index=True, sort=False)

    if not combined.empty:
        combined = combined.drop_duplicates(['symbol', 'checkpoint'], keep='first')
        combined.to_csv(CSV_PATH, index=False, quoting=csv.QUOTE_MINIMAL)
    elif not CSV_PATH.exists():
        pd.DataFrame(columns=['snapshot_id','symbol','asset_type','checkpoint']).to_csv(CSV_PATH, index=False)

    records = combined.where(pd.notna(combined), None).to_dict('records') if not combined.empty else []
    JSON_PATH.write_text(json.dumps({
        'generated_at_utc': NOW.isoformat(),
        'engine': 'V8_LAB_CANONICAL_CHECKPOINTS_v0.1',
        'source_lab_engine': engine_version,
        'immutable_key': 'symbol+checkpoint',
        'crypto_schedule': ['D0','D1','D3','D7','D30'],
        'stock_schedule': ['D0','D7','D30'],
        'checkpoints': records,
        'rules': {
            'first_capture_after_due_is_kept': True,
            'existing_checkpoint_is_never_overwritten': True,
            'snapshot_hash_sha256': True,
            'no_portfolio_connection': True,
            'no_trade_execution': True,
        }
    }, indent=2, ensure_ascii=False), encoding='utf-8')

    status = {
        'generated_at_utc': NOW.isoformat(),
        'engine': 'V8_LAB_CANONICAL_CHECKPOINTS_v0.1',
        'deep_assets_seen': deep_assets,
        'new_checkpoints_written': len(new_rows),
        'total_checkpoints': len(records),
        'skipped_not_due': skipped_not_due,
        'skipped_existing': skipped_existing,
        'immutable_checkpoints': True,
        'snapshot_sha256_enabled': True,
        'portfolio_connection': False,
        'execution_connection': False,
    }
    STATUS_PATH.write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(status, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
