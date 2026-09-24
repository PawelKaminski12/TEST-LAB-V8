import json
from datetime import datetime, timezone
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TACTICAL_JSON = ROOT / 'tactical_engine' / 'TACTICAL_ENGINE.json'
OUT_DIR = ROOT / 'morning_radar'
OUT_JSON = OUT_DIR / 'MORNING_RADAR.json'

sys.path.insert(0, str(ROOT / 'scripts'))
import v8_tactical_engine_v1 as tactical_base

TF_ORDER = ['1H', '2H', '4H']


def clean_number(v):
    try:
        x = float(v)
        if pd.isna(x):
            return None
        return x
    except Exception:
        return None


def derive_2h(pair: str):
    src = ROOT / 'tactical_engine' / f'{pair}_1H.csv'
    if not src.exists():
        raise FileNotFoundError(src)
    df = pd.read_csv(src)
    if df.empty:
        raise RuntimeError(f'Pusty plik {src}')
    for c in ['open', 'high', 'low', 'close', 'volume']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df['open_time'] = pd.to_datetime(df['open_time'], utc=True, errors='coerce')
    df['close_time'] = pd.to_datetime(df['close_time'], utc=True, errors='coerce')
    df = df.dropna(subset=['open_time','close_time','open','high','low','close','volume']).sort_values('open_time')
    if len(df) < 440:
        raise RuntimeError(f'Za mało świec 1H do zbudowania 2H: {pair} {len(df)}')

    x = df.set_index('open_time')
    grouped = x.resample('2h', origin='epoch', label='left', closed='left')
    out = grouped.agg({
        'open':'first',
        'high':'max',
        'low':'min',
        'close':'last',
        'volume':'sum',
        'close_time':'max',
    })
    counts = grouped['close'].count()
    out['bar_count'] = counts
    out = out[out['bar_count'] == 2].drop(columns=['bar_count']).dropna().reset_index()
    if len(out) < 220:
        raise RuntimeError(f'Za mało pełnych świec 2H: {pair} {len(out)}')

    enriched = tactical_base.enrich(out)
    state = tactical_base.bar_state(enriched, '2H')
    state['rows_closed'] = int(len(out))
    state['last_close_time_utc'] = out.iloc[-1]['close_time'].isoformat()
    state['closed_bar_only'] = True
    now = pd.Timestamp.now(tz='UTC')
    last_close = pd.Timestamp(out.iloc[-1]['close_time'])
    state['stale'] = bool(now - last_close > pd.Timedelta(hours=4))
    return state


def normalize_macd_direction(tf):
    """Keep alert strength, but force +/- to follow the actual MACD histogram side of zero.

    This is a Morning Radar display normalization only. It does not modify the frozen
    Tactical production engine. Upper MACD extreme = positive histogram, lower = negative.
    """
    out = dict(tf or {})
    label = str(out.get('macd_extreme_label') or 'NORMAL').upper()
    hist = clean_number(out.get('macd_hist'))
    if hist is None or label in {'NORMAL', 'NO_DATA'}:
        return out

    is_extreme = 'EXTREME' in label
    is_warning = 'WARNING' in label
    if not (is_extreme or is_warning):
        return out

    if hist > 0:
        out['macd_extreme_label'] = 'EXTREME_POSITIVE' if is_extreme else 'WARNING_POSITIVE'
        out['macd_extreme_direction'] = 'POSITIVE'
    elif hist < 0:
        out['macd_extreme_label'] = 'EXTREME_NEGATIVE' if is_extreme else 'WARNING_NEGATIVE'
        out['macd_extreme_direction'] = 'NEGATIVE'
    else:
        out['macd_extreme_label'] = 'NORMAL'
        out['macd_extreme_direction'] = 'NONE'
        out['macd_extreme_warning'] = False
        out['macd_extreme'] = False
    return out


def radar_eval(tf):
    rsi = clean_number(tf.get('rsi14'))
    mfi = clean_number(tf.get('mfi14'))
    fomo = clean_number(tf.get('fomo_score_0_10')) or 0
    trend = clean_number(tf.get('trend_score_0_4')) or 0
    macd_label = str(tf.get('macd_extreme_label') or 'NORMAL').upper()

    hot = 0
    cold = 0
    reasons = []

    if rsi is not None:
        if rsi >= 75:
            hot += 3; reasons.append(f'RSI {rsi:.0f} wysokie')
        elif rsi >= 70:
            hot += 2; reasons.append(f'RSI {rsi:.0f} podwyższone')
        elif rsi <= 25:
            cold += 3; reasons.append(f'RSI {rsi:.0f} niskie')
        elif rsi <= 30:
            cold += 2; reasons.append(f'RSI {rsi:.0f} osłabione')

    if mfi is not None:
        if mfi >= 90:
            hot += 3; reasons.append(f'MFI {mfi:.0f} ekstremum')
        elif mfi >= 80:
            hot += 2; reasons.append(f'MFI {mfi:.0f} wysokie')
        elif mfi <= 10:
            cold += 3; reasons.append(f'MFI {mfi:.0f} ekstremum')
        elif mfi <= 20:
            cold += 2; reasons.append(f'MFI {mfi:.0f} niskie')

    if 'POSITIVE' in macd_label:
        hot += 2
        reasons.append('MACD górne granice' if 'EXTREME' in macd_label else 'MACD górne ostrzeżenie')
    elif 'NEGATIVE' in macd_label:
        cold += 2
        reasons.append('MACD dolne granice' if 'EXTREME' in macd_label else 'MACD dolne ostrzeżenie')

    if fomo >= 8:
        hot += 3; reasons.append(f'FOMO {int(fomo)}')
    elif fomo >= 6:
        hot += 2; reasons.append(f'FOMO {int(fomo)}')

    intensity = max(hot, cold)
    if hot >= 5 and hot > cold:
        status = 'GORĄCO'
        direction = 'HOT'
    elif cold >= 5 and cold > hot:
        status = 'CHŁODNO'
        direction = 'COLD'
    elif hot >= 3 and hot > cold:
        status = 'UWAGA +'
        direction = 'HOT'
    elif cold >= 3 and cold > hot:
        status = 'UWAGA -'
        direction = 'COLD'
    else:
        status = 'NEUTRALNIE'
        direction = 'NEUTRAL'

    return {
        'radar_status': status,
        'radar_direction': direction,
        'radar_intensity_0_10': int(min(10, intensity)),
        'hot_points': int(hot),
        'cold_points': int(cold),
        'reason_pl': '; '.join(reasons) if reasons else 'brak skrajności',
        'rsi_extreme': bool(rsi is not None and (rsi >= 75 or rsi <= 25)),
        'mfi_extreme': bool(mfi is not None and (mfi >= 90 or mfi <= 10)),
        'macd_alert': bool(macd_label not in ['NORMAL', 'NO_DATA']),
        'fomo_hard': bool(fomo >= 8),
        'trend_score_0_4': trend,
    }


def compact_tf(tf):
    tf = normalize_macd_direction(tf)
    keys = [
        'timeframe','close','trend_score_0_4','macd_hist','macd_hist_percentile','macd_hist_zscore',
        'macd_extreme_label','rsi14','mfi14','fomo_score_0_10','fomo_label','last_close_time_utc',
        'closed_bar_only','stale'
    ]
    out = {k: tf.get(k) for k in keys}
    out.update(radar_eval(tf))
    return out


def main():
    data = json.loads(TACTICAL_JSON.read_text(encoding='utf-8'))
    assets = []
    errors = []

    for a in data.get('assets', []):
        sym = str(a.get('symbol') or '')
        if not sym or sym == 'BTC':
            continue
        pair = str(a.get('pair') or f'{sym}USDT')
        try:
            t1 = compact_tf((a.get('timeframes') or {}).get('1H') or {})
            t4 = compact_tf((a.get('timeframes') or {}).get('4H') or {})
            t2 = compact_tf(derive_2h(pair))
            tfs = {'1H': t1, '2H': t2, '4H': t4}
            ranked = sorted(
                TF_ORDER,
                key=lambda tf: (int(tfs[tf]['radar_intensity_0_10']), -TF_ORDER.index(tf)),
                reverse=True,
            )
            auto_tf = ranked[0]
            assets.append({
                'symbol': sym,
                'pair': pair,
                'timeframes': tfs,
                'auto': {
                    'timeframe': auto_tf,
                    **tfs[auto_tf],
                },
            })
        except Exception as e:
            errors.append({'symbol': sym, 'error': str(e)})

    OUT_DIR.mkdir(exist_ok=True)
    payload = {
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'engine': 'V8_MORNING_RADAR_v1',
        'research_only': True,
        'execution_connected': False,
        'purpose_pl': 'Poranny radar krótkoterminowy 1H / 2H / 4H. Nie zastępuje Panelu Taktycznego.',
        'timeframes': TF_ORDER,
        'auto_rule_pl': 'AUTO wybiera dla każdego aktywa najbardziej skrajny interwał 1H/2H/4H; przy remisie preferuje krótszy interwał.',
        'asset_count': len(assets),
        'assets': assets,
        'errors': errors,
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'MORNING RADAR: {len(assets)} aktywów, błędy={len(errors)}')
    if len(assets) != 13 or errors:
        raise SystemExit(f'Niepełny radar: assets={len(assets)} errors={errors}')


if __name__ == '__main__':
    main()
