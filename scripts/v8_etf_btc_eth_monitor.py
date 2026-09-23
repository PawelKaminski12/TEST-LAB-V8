import io
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

OUT = Path('institutional_data_hub')
OUT.mkdir(exist_ok=True)

NOW_UTC = datetime.now(timezone.utc)
NOW_NY = NOW_UTC.astimezone(ZoneInfo('America/New_York'))
TODAY_NY = NOW_NY.date()

BASE = 'https://raw.githubusercontent.com/haturatu/crypto-etf-flow/main'
FILES = {'BTC': 'etf_btc.csv', 'ETH': 'etf_eth.csv'}
UA = {'User-Agent': 'Mozilla/5.0 TEST-LAB-V8 ETF monitor'}


def finite(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except Exception:
        return None


def fetch_csv(asset, filename):
    url = f'{BASE}/{filename}'
    r = requests.get(url, timeout=40, headers=UA)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    if 'Date' not in df.columns or 'Total' not in df.columns:
        raise RuntimeError(f'{asset}: nieprawidłowy format źródła ETF')
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce', dayfirst=True)
    df = df.dropna(subset=['Date']).sort_values('Date').drop_duplicates('Date', keep='last').copy()
    df['Total_num'] = pd.to_numeric(df['Total'], errors='coerce')
    fund_cols = [c for c in df.columns if c not in {'Date', 'Total', 'Total_num'}]
    for c in fund_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    return df, fund_cols, url


def closed_rows(df):
    return df[df['Date'].dt.date < TODAY_NY].copy()


def latest_today_row(df):
    z = df[df['Date'].dt.date == TODAY_NY]
    return None if z.empty else z.iloc[-1]


def row_completeness(row, fund_cols):
    if row is None or not fund_cols:
        return 0.0, 0, len(fund_cols)
    present = sum(pd.notna(row[c]) for c in fund_cols)
    return round(100.0 * present / len(fund_cols), 1), int(present), int(len(fund_cols))


def sum_tail(s, n):
    s = pd.to_numeric(s, errors='coerce').dropna()
    if s.empty:
        return None
    return float(s.tail(n).sum())


def flow_trend(closed):
    s = closed['Total_num'].dropna()
    if len(s) < 10:
        return {'label_pl': 'ZA MAŁO HISTORII', 'score_adjustment': 0.0}
    sum5 = float(s.tail(5).sum())
    prev5 = float(s.iloc[-10:-5].sum())
    accel = sum5 - prev5
    if sum5 > 0 and accel > 0:
        label, adj = 'NAPŁYW PRZYSPIESZA', 1.0
    elif sum5 > 0:
        label, adj = 'NAPŁYW KAPITAŁU, ALE TEMPO SŁABNIE', 0.5
    elif sum5 < 0 and accel < 0:
        label, adj = 'ODPŁYW PRZYSPIESZA', -1.0
    elif sum5 < 0:
        label, adj = 'ODPŁYW KAPITAŁU, ALE PRESJA SŁABNIE', -0.5
    else:
        label, adj = 'PRZEPŁYWY NEUTRALNE', 0.0
    return {'label_pl': label, 'score_adjustment': adj, 'closed_5d_usdm': sum5, 'previous_5d_usdm': prev5, 'acceleration_5d_usdm': accel}


def build_asset(asset, filename):
    df, fund_cols, url = fetch_csv(asset, filename)
    closed = closed_rows(df)
    if closed.empty:
        raise RuntimeError(f'{asset}: brak zamkniętych dni ETF')

    last_closed = closed.iloc[-1]
    today = latest_today_row(df)
    completeness_pct, funds_present, funds_total = row_completeness(today, fund_cols)

    trend = flow_trend(closed)
    s = closed['Total_num'].dropna()
    closed_1d = finite(last_closed['Total_num'])
    closed_5d = sum_tail(s, 5)
    closed_20d = sum_tail(s, 20)
    closed_30d = sum_tail(s, 30)

    today_total = finite(today['Total_num']) if today is not None else None
    if today is None:
        today_status = 'DZISIAJ BRAK JESZCZE WIERSZA W ŹRÓDLE'
        today_note = 'Nie traktujemy braku dzisiejszego wiersza jako odpływu ani napływu.'
    else:
        today_status = 'DZISIAJ — DANE WSTĘPNE'
        today_note = 'Dzisiejszy wiersz jest tylko podglądem. Do oceny trendu używamy wyłącznie zakończonych dni.'

    return {
        'asset': asset,
        'source_url': url,
        'primary_source': 'Farside Investors',
        'transport': 'haturatu/crypto-etf-flow mirror',
        'last_source_date': df.iloc[-1]['Date'].date().isoformat(),
        'last_closed_date': last_closed['Date'].date().isoformat(),
        'last_closed_flow_usdm': closed_1d,
        'closed_5d_usdm': closed_5d,
        'closed_20d_usdm': closed_20d,
        'closed_30d_usdm': closed_30d,
        'closed_trend': trend,
        'today_date': TODAY_NY.isoformat(),
        'today_status_pl': today_status,
        'today_flow_preview_usdm': today_total,
        'today_fund_completeness_pct': completeness_pct,
        'today_funds_present': funds_present,
        'today_funds_total': funds_total,
        'today_note_pl': today_note,
        'rules': {
            'today_never_treated_as_final_same_day': True,
            'closed_trend_excludes_today': True,
            'zero_today_does_not_mean_final_zero': True,
        },
    }


def global_interest(assets):
    b = assets['BTC']['closed_trend']
    e = assets['ETH']['closed_trend']
    b5 = finite(assets['BTC']['closed_5d_usdm'])
    e5 = finite(assets['ETH']['closed_5d_usdm'])
    ba = finite(b.get('acceleration_5d_usdm'))
    ea = finite(e.get('acceleration_5d_usdm'))

    score = 5.0
    if b5 is not None:
        score += 1.5 if b5 > 0 else -1.5 if b5 < 0 else 0
    if e5 is not None:
        score += 1.5 if e5 > 0 else -1.5 if e5 < 0 else 0
    if ba is not None:
        score += 0.75 if ba > 0 else -0.75 if ba < 0 else 0
    if ea is not None:
        score += 0.75 if ea > 0 else -0.75 if ea < 0 else 0
    score = max(0.0, min(10.0, score))

    if b5 is not None and e5 is not None and b5 > 0 and e5 > 0:
        if (ba or 0) > 0 and (ea or 0) > 0:
            label = 'SZEROKIE ZAINTERESOWANIE INSTYTUCJONALNE ROŚNIE'
        else:
            label = 'KAPITAŁ NAPŁYWA DO BTC I ETH, ALE TEMPO NIE JEST JEDNOLITE'
    elif b5 is not None and e5 is not None and b5 < 0 and e5 < 0:
        label = 'SZEROKIE ZAINTERESOWANIE INSTYTUCJONALNE SŁABNIE'
    else:
        label = 'KAPITAŁ INSTYTUCJONALNY JEST PODZIELONY MIĘDZY BTC I ETH'

    return {
        'score_0_10': round(score, 2),
        'label_pl': label,
        'btc_closed_5d_usdm': b5,
        'eth_closed_5d_usdm': e5,
        'btc_acceleration_5d_usdm': ba,
        'eth_acceleration_5d_usdm': ea,
        'role': 'kontekst instytucjonalny, nie samodzielny sygnał kupna lub sprzedaży',
    }


def fmt(v):
    return 'brak danych' if v is None else f'{v:,.1f}'.replace(',', ' ')


def main():
    assets = {a: build_asset(a, f) for a, f in FILES.items()}
    global_ctx = global_interest(assets)
    payload = {
        'generated_at_utc': NOW_UTC.isoformat(),
        'generated_at_new_york': NOW_NY.isoformat(),
        'engine': 'V8_ETF_BTC_ETH_MONITOR_v1.0',
        'assets': assets,
        'global_institutional_interest': global_ctx,
        'safety': {
            'research_only': True,
            'execution_connected': False,
            'same_day_etf_values_are_provisional': True,
            'closed_day_values_drive_scores': True,
        },
    }
    (OUT / 'ETF_BTC_ETH_STATUS.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    rows = []
    for a in ['BTC', 'ETH']:
        x = assets[a]
        rows.append({
            'AKTYWO': a,
            'OSTATNI_ZAMKNIETY_DZIEN': x['last_closed_date'],
            'OSTATNI_ZAMKNIETY_PRZEPLYW_MLN_USD': x['last_closed_flow_usdm'],
            '5_DNI_MLN_USD': x['closed_5d_usdm'],
            '20_DNI_MLN_USD': x['closed_20d_usdm'],
            '30_DNI_MLN_USD': x['closed_30d_usdm'],
            'TREND': x['closed_trend']['label_pl'],
            'DZISIAJ_STATUS': x['today_status_pl'],
            'DZISIAJ_PODGLAD_MLN_USD': x['today_flow_preview_usdm'],
            'DZISIAJ_KOMPLETNOSC_FUNDUSZY_PROC': x['today_fund_completeness_pct'],
        })
    pd.DataFrame(rows).to_csv(OUT / 'ETF_BTC_ETH_PANEL.csv', index=False)

    md = [
        '# V8 — ETF BTC / ETH', '',
        f"Czas odczytu: {NOW_UTC.isoformat()}", '',
        f"## WSPÓLNY OBRAZ: {global_ctx['label_pl']}",
        f"Ocena zainteresowania instytucjonalnego: **{global_ctx['score_0_10']}/10**", '',
    ]
    for a in ['BTC', 'ETH']:
        x = assets[a]
        md += [
            f'## {a}',
            f"- Ostatni zakończony dzień: **{x['last_closed_date']}** — {fmt(x['last_closed_flow_usdm'])} mln USD.",
            f"- 5 zakończonych dni: {fmt(x['closed_5d_usdm'])} mln USD.",
            f"- 20 zakończonych dni: {fmt(x['closed_20d_usdm'])} mln USD.",
            f"- 30 zakończonych dni: {fmt(x['closed_30d_usdm'])} mln USD.",
            f"- Trend: **{x['closed_trend']['label_pl']}**.",
            f"- Dzisiaj: **{x['today_status_pl']}** — podgląd {fmt(x['today_flow_preview_usdm'])} mln USD; kompletność funduszy {x['today_fund_completeness_pct']}%.",
            f"- {x['today_note_pl']}", '',
        ]
    md += [
        'Dzisiejszy odczyt nie jest traktowany jako wynik końcowy. Do oceny trendu wchodzą wyłącznie zakończone dni ETF.',
        'Warstwa jest badawcza i nie wykonuje transakcji.'
    ]
    (OUT / 'ETF_BTC_ETH_LATEST.md').write_text('\n'.join(md), encoding='utf-8')

    print(json.dumps({
        'engine': payload['engine'],
        'BTC': assets['BTC']['closed_trend']['label_pl'],
        'ETH': assets['ETH']['closed_trend']['label_pl'],
        'global': global_ctx['label_pl'],
        'score': global_ctx['score_0_10'],
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
