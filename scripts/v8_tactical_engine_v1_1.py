import pandas as pd
import requests

import v8_tactical_engine_v1 as base

ORIGINAL_FETCH = base.fetch_klines
KRAKEN_INTERVALS = {'1h': 60, '4h': 240, '1d': 1440}


def fetch_with_kraken_spx(symbol, pair, interval, limit):
    try:
        return ORIGINAL_FETCH(symbol, pair, interval, limit)
    except Exception as original_error:
        if symbol != 'SPX6900':
            raise

        kraken_interval = KRAKEN_INTERVALS.get(interval)
        if kraken_interval is None:
            raise original_error

        url = 'https://api.kraken.com/0/public/OHLC'
        r = requests.get(url, params={'pair': 'SPXUSD', 'interval': kraken_interval}, timeout=30)
        r.raise_for_status()
        payload = r.json()
        if payload.get('error'):
            raise RuntimeError('Kraken SPX6900: ' + ' | '.join(payload['error']))
        result = payload.get('result', {})
        key = next((k for k in result if k != 'last'), None)
        rows = result.get(key, []) if key else []
        if len(rows) < 220:
            raise RuntimeError(f'Kraken SPX6900: za mało świec {len(rows)}')

        df = pd.DataFrame(rows, columns=['time','open','high','low','close','vwap','volume','count'])
        for c in ['open','high','low','close','volume']:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        df['open_time'] = pd.to_datetime(df['time'], unit='s', utc=True)
        delta = pd.Timedelta(hours=1 if interval == '1h' else 4 if interval == '4h' else 24)
        df['close_time'] = df['open_time'] + delta - pd.Timedelta(milliseconds=1)
        df = df[['open_time','close_time','open','high','low','close','volume']].dropna().drop_duplicates('open_time').sort_values('open_time').reset_index(drop=True)
        df = df[df['close_time'] < base.NOW - pd.Timedelta(seconds=5)].reset_index(drop=True)
        if len(df) < 220:
            raise RuntimeError(f'Kraken SPX6900: za mało zamkniętych świec {len(df)}')
        if limit and len(df) > limit:
            df = df.tail(limit).reset_index(drop=True)
        return df, url, 'SPOT_KRAKEN'


base.fetch_klines = fetch_with_kraken_spx
base.main()
