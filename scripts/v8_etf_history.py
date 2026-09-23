import io
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

OUT = Path('institutional_data_hub')
OUT.mkdir(exist_ok=True)
NOW_UTC = datetime.now(timezone.utc)
TODAY_NY = NOW_UTC.astimezone(ZoneInfo('America/New_York')).date()
BASE = 'https://raw.githubusercontent.com/haturatu/crypto-etf-flow/main'
FILES = {'BTC': 'etf_btc.csv', 'ETH': 'etf_eth.csv'}
UA = {'User-Agent': 'Mozilla/5.0 TEST-LAB-V8 ETF history'}


def load(asset, filename):
    r = requests.get(f'{BASE}/{filename}', timeout=40, headers=UA)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    if 'Date' not in df.columns or 'Total' not in df.columns:
        raise RuntimeError(f'{asset}: nieprawidłowy format danych ETF')
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce', dayfirst=True)
    df['Total'] = pd.to_numeric(df['Total'], errors='coerce')
    df = df.dropna(subset=['Date', 'Total']).sort_values('Date').drop_duplicates('Date', keep='last')
    df = df[df['Date'].dt.date < TODAY_NY].copy()
    if df.empty:
        raise RuntimeError(f'{asset}: brak zakończonych dni ETF')
    return df


def streak(series):
    vals = list(pd.to_numeric(series, errors='coerce').dropna())
    if not vals:
        return {'direction': 'BRAK DANYCH', 'days': 0}
    last = vals[-1]
    if last > 0:
        sign = 1; label = 'NAPŁYW'
    elif last < 0:
        sign = -1; label = 'ODPŁYW'
    else:
        return {'direction': 'NEUTRALNIE', 'days': 1}
    n = 0
    for v in reversed(vals):
        if (v > 0 and sign == 1) or (v < 0 and sign == -1):
            n += 1
        else:
            break
    return {'direction': label, 'days': n}


def rolling_stats(df):
    s = df['Total']
    last = float(s.iloc[-1])
    prev = float(s.iloc[-2]) if len(s) >= 2 else None
    sum5 = float(s.tail(5).sum())
    prev5 = float(s.iloc[-10:-5].sum()) if len(s) >= 10 else None
    sum20 = float(s.tail(20).sum())
    sum30 = float(s.tail(30).sum())
    positive20 = int((s.tail(20) > 0).sum())
    negative20 = int((s.tail(20) < 0).sum())
    return {
        'last_date': df.iloc[-1]['Date'].date().isoformat(),
        'last_flow_usdm': last,
        'previous_flow_usdm': prev,
        'change_vs_previous_usdm': None if prev is None else last - prev,
        'sum_5d_usdm': sum5,
        'previous_5d_usdm': prev5,
        'acceleration_5d_usdm': None if prev5 is None else sum5 - prev5,
        'sum_20d_usdm': sum20,
        'sum_30d_usdm': sum30,
        'positive_days_20': positive20,
        'negative_days_20': negative20,
        'streak': streak(s),
    }


def build_history(btc, eth):
    b = btc[['Date', 'Total']].rename(columns={'Total': 'BTC_MLN_USD'})
    e = eth[['Date', 'Total']].rename(columns={'Total': 'ETH_MLN_USD'})
    h = pd.merge(b, e, on='Date', how='outer').sort_values('Date')
    h['Date'] = h['Date'].dt.date.astype(str)
    h['WSPOLNY_PRZEPLYW_MLN_USD'] = h[['BTC_MLN_USD', 'ETH_MLN_USD']].sum(axis=1, min_count=1)
    h['BTC_KIERUNEK'] = h['BTC_MLN_USD'].apply(lambda v: 'NAPŁYW' if pd.notna(v) and v > 0 else 'ODPŁYW' if pd.notna(v) and v < 0 else 'NEUTRALNIE')
    h['ETH_KIERUNEK'] = h['ETH_MLN_USD'].apply(lambda v: 'NAPŁYW' if pd.notna(v) and v > 0 else 'ODPŁYW' if pd.notna(v) and v < 0 else 'NEUTRALNIE')
    return h.tail(120).copy()


def common_context(bs, es):
    score = 5.0
    for x in [bs['sum_5d_usdm'], es['sum_5d_usdm']]:
        score += 1.5 if x > 0 else -1.5 if x < 0 else 0
    for x in [bs['acceleration_5d_usdm'], es['acceleration_5d_usdm']]:
        if x is not None:
            score += 0.75 if x > 0 else -0.75 if x < 0 else 0
    score = max(0.0, min(10.0, score))
    if bs['sum_5d_usdm'] > 0 and es['sum_5d_usdm'] > 0:
        if (bs['acceleration_5d_usdm'] or 0) > 0 and (es['acceleration_5d_usdm'] or 0) > 0:
            label = 'SZEROKIE ZAINTERESOWANIE INSTYTUCJONALNE ROŚNIE'
        else:
            label = 'KAPITAŁ NAPŁYWA DO BTC I ETH, ALE TEMPO JEST NIERÓWNE'
    elif bs['sum_5d_usdm'] < 0 and es['sum_5d_usdm'] < 0:
        label = 'SZEROKIE ZAINTERESOWANIE INSTYTUCJONALNE SŁABNIE'
    else:
        label = 'PRZEPŁYWY BTC I ETH SĄ ROZBIEŻNE'
    return {'score_0_10': round(score, 2), 'label_pl': label}


def fmt(v):
    if v is None:
        return 'brak danych'
    return f'{float(v):,.1f}'.replace(',', ' ')


def main():
    btc = load('BTC', FILES['BTC'])
    eth = load('ETH', FILES['ETH'])
    bs = rolling_stats(btc)
    es = rolling_stats(eth)
    common = common_context(bs, es)
    hist = build_history(btc, eth)
    hist.to_csv(OUT / 'ETF_BTC_ETH_HISTORY.csv', index=False)

    payload = {
        'generated_at_utc': NOW_UTC.isoformat(),
        'engine': 'V8_ETF_HISTORY_v1.0',
        'BTC': bs,
        'ETH': es,
        'global_institutional_interest': common,
        'rules': {
            'closed_days_only': True,
            'today_excluded_until_next_day': True,
            'history_rows_max': 120,
            'research_only': True,
            'execution_connected': False,
        },
    }
    (OUT / 'ETF_BTC_ETH_HISTORY_STATUS.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    lines = [
        '# V8 — HISTORIA ETF BTC / ETH', '',
        f"Czas analizy: {NOW_UTC.isoformat()}", '',
        f"## WSPÓLNY OBRAZ: {common['label_pl']}",
        f"Ocena zainteresowania instytucjonalnego: **{common['score_0_10']}/10**", '',
    ]
    for asset, s in [('BTC', bs), ('ETH', es)]:
        lines += [
            f'## {asset}',
            f"- Ostatni zakończony dzień: **{s['last_date']}** — {fmt(s['last_flow_usdm'])} mln USD.",
            f"- Poprzedni zakończony dzień: {fmt(s['previous_flow_usdm'])} mln USD.",
            f"- Zmiana względem poprzedniego dnia: {fmt(s['change_vs_previous_usdm'])} mln USD.",
            f"- 5 zakończonych dni: {fmt(s['sum_5d_usdm'])} mln USD.",
            f"- Zmiana tempa 5-dniowego: {fmt(s['acceleration_5d_usdm'])} mln USD.",
            f"- 20 zakończonych dni: {fmt(s['sum_20d_usdm'])} mln USD.",
            f"- 30 zakończonych dni: {fmt(s['sum_30d_usdm'])} mln USD.",
            f"- Seria: **{s['streak']['direction']} przez {s['streak']['days']} kolejnych zakończonych dni**.",
            f"- W ostatnich 20 dniach: {s['positive_days_20']} dni napływu i {s['negative_days_20']} dni odpływu.", '',
        ]
    lines += [
        'Historia obejmuje wyłącznie zakończone dni ETF. Dzisiejsze dane wstępne nie zmieniają tej oceny.',
        'Warstwa jest badawcza i nie wykonuje transakcji.'
    ]
    (OUT / 'ETF_BTC_ETH_HISTORY_LATEST.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'BTC': bs, 'ETH': es, 'global': common}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
