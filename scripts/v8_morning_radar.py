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
FRESH_LIMIT_H = {'1H': 3, '2H': 5, '4H': 10}


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


def macd_context(tf):
    """Morning Radar MACD semantics.

    The historical MACD alert label already says whether the histogram is in a positive
    or negative warning/extreme tail. That polarity defines the user-facing side:
    WARNING/EXTREME_NEGATIVE -> DOLNE, WARNING/EXTREME_POSITIVE -> GÓRNE.

    The actual MACD line versus zero is kept only as technical context and must not flip
    the visible DOLNE/GÓRNE label. This avoids cases where a strongly negative histogram
    is shown as 'GÓRNE' merely because the slower MACD line has not crossed zero yet.

    Momentum wording stays separate:
    histogram > 0 -> ODBICIE +
    histogram < 0 -> SCHŁODZENIE −

    This affects Morning Radar presentation/scoring only; frozen Tactical production
    calculations and thresholds are not modified.
    """
    label = str(tf.get('macd_extreme_label') or 'NORMAL').upper()
    macd_line = clean_number(tf.get('macd'))
    hist = clean_number(tf.get('macd_hist'))

    alert = label not in {'NORMAL', 'NO_DATA'}
    extreme = 'EXTREME' in label
    warning = 'WARNING' in label

    # User-facing side comes from the alert polarity, not from MACD line vs zero.
    if 'NEGATIVE' in label:
        side = 'LOWER'
    elif 'POSITIVE' in label:
        side = 'UPPER'
    elif macd_line is None:
        side = 'NONE'
    elif macd_line < 0:
        side = 'LOWER'
    elif macd_line > 0:
        side = 'UPPER'
    else:
        side = 'ZERO'

    if macd_line is None:
        line_side = 'NONE'
    elif macd_line < 0:
        line_side = 'LOWER'
    elif macd_line > 0:
        line_side = 'UPPER'
    else:
        line_side = 'ZERO'

    if hist is None or hist == 0:
        momentum = 'PŁASKO'
        momentum_code = 'FLAT'
    elif hist > 0:
        momentum = 'ODBICIE +'
        momentum_code = 'UP'
    else:
        momentum = 'SCHŁODZENIE −'
        momentum_code = 'DOWN'

    display = 'NORMALNY'
    reason = None
    if alert and (extreme or warning):
        strength = 'GRANICE' if extreme else 'OSTRZEŻ.'
        strength_reason = 'granice' if extreme else 'ostrzeżenie'
        if side == 'LOWER':
            display = f'DOLNE {strength}'
            reason = f'MACD dolne {strength_reason}; {momentum.lower()}'
        elif side == 'UPPER':
            display = f'GÓRNE {strength}'
            reason = f'MACD górne {strength_reason}; {momentum.lower()}'
        else:
            display = 'MACD ALERT'
            reason = f'MACD alert; {momentum.lower()}'

    return {
        'macd_level_side': side,
        'macd_line_side': line_side,
        'macd_momentum': momentum_code,
        'macd_momentum_pl': momentum,
        'macd_display_pl': display,
        'macd_reason_pl': reason,
        'macd_alert_strength': 'EXTREME' if extreme else 'WARNING' if warning else 'NORMAL',
    }


def radar_eval(tf):
    rsi = clean_number(tf.get('rsi14'))
    mfi = clean_number(tf.get('mfi14'))
    fomo = clean_number(tf.get('fomo_score_0_10')) or 0
    trend = clean_number(tf.get('trend_score_0_4')) or 0
    ctx = macd_context(tf)

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

    if ctx['macd_alert_strength'] != 'NORMAL':
        if ctx['macd_level_side'] == 'UPPER':
            hot += 2
        elif ctx['macd_level_side'] == 'LOWER':
            cold += 2
        if ctx['macd_reason_pl']:
            reasons.append(ctx['macd_reason_pl'])

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
        'macd_alert': bool(ctx['macd_alert_strength'] != 'NORMAL'),
        'fomo_hard': bool(fomo >= 8),
        'trend_score_0_4': trend,
        **ctx,
    }


def freshness_state(tf_name, tf):
    raw = tf.get('last_close_time_utc')
    if not raw:
        return True, None
    try:
        last = pd.Timestamp(raw)
        if last.tzinfo is None:
            last = last.tz_localize('UTC')
        else:
            last = last.tz_convert('UTC')
        age_h = (pd.Timestamp.now(tz='UTC') - last).total_seconds() / 3600.0
        return bool(age_h > FRESH_LIMIT_H[tf_name]), round(max(0.0, age_h), 2)
    except Exception:
        return True, None


def signal_signature(tf):
    reason = str(tf.get('reason_pl') or 'brak skrajności')
    if reason.lower() == 'brak skrajności':
        return None
    return '|'.join([
        reason,
        str(tf.get('radar_status') or ''),
        str(tf.get('macd_display_pl') or ''),
    ])


def previous_tf(previous, symbol, tf_name):
    for a in (previous or {}).get('assets', []):
        if str(a.get('symbol') or '') == symbol:
            return ((a.get('timeframes') or {}).get(tf_name) or {})
    return {}


def attach_signal_start(symbol, tf_name, tf, previous):
    sig = signal_signature(tf)
    prev = previous_tf(previous, symbol, tf_name)
    prev_sig = prev.get('signal_signature')
    if sig is None:
        tf['signal_signature'] = None
        tf['signal_started_at_utc'] = None
        return tf
    tf['signal_signature'] = sig
    if prev_sig == sig and prev.get('signal_started_at_utc'):
        tf['signal_started_at_utc'] = prev.get('signal_started_at_utc')
    else:
        tf['signal_started_at_utc'] = tf.get('last_close_time_utc') or datetime.now(timezone.utc).isoformat()
    return tf


def compact_tf(tf):
    keys = [
        'timeframe','close','trend_score_0_4','macd','macd_signal','macd_hist',
        'macd_hist_percentile','macd_hist_zscore','macd_extreme_label',
        'rsi14','mfi14','fomo_score_0_10','fomo_label','last_close_time_utc',
        'closed_bar_only','stale'
    ]
    out = {k: tf.get(k) for k in keys}
    out.update(radar_eval(tf))
    return out


def main():
    previous = {}
    if OUT_JSON.exists():
        try:
            previous = json.loads(OUT_JSON.read_text(encoding='utf-8'))
        except Exception:
            previous = {}
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
            for tf_name, tf_state in tfs.items():
                stale, age_h = freshness_state(tf_name, tf_state)
                tf_state['stale'] = stale
                tf_state['age_hours'] = age_h
                tf_state['fresh_limit_hours'] = FRESH_LIMIT_H[tf_name]
                attach_signal_start(sym, tf_name, tf_state, previous)
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
