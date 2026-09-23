import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ETF_STATUS = Path('institutional_data_hub/ETF_BTC_ETH_STATUS.json')
LAB_REPORT = Path('lab/LAB_REPORT.json')
OUT = Path('institutional_data_hub')
OUT.mkdir(exist_ok=True)
NOW = datetime.now(timezone.utc)


def sf(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def sign(v):
    x = sf(v)
    if x is None:
        return 0
    return 1 if x > 0 else -1 if x < 0 else 0


def report_map(lab):
    out = {}
    for r in lab.get('reports', []):
        sym = str(r.get('symbol', '')).upper()
        if sym in ('BTC', 'ETH'):
            out[sym] = r
    return out


def quality_for_asset(x):
    last_closed = x.get('last_closed_date')
    today_status = str(x.get('today_status_pl') or '')
    completeness = sf(x.get('today_fund_completeness_pct')) or 0.0
    score = 100
    reasons = []
    try:
        d = datetime.fromisoformat(str(last_closed)).date()
        age = (NOW.date() - d).days
    except Exception:
        age = None
        score -= 45
        reasons.append('BRAK PEWNEJ DATY OSTATNIEGO ZAMKNIĘTEGO DNIA')
    if age is not None:
        if age <= 1:
            pass
        elif age <= 3:
            score -= 10
            reasons.append('OSTATNI ZAMKNIĘTY DZIEŃ MA KILKA DNI')
        else:
            score -= 30
            reasons.append('DANE ZAMKNIĘTE SĄ STARE')
    if 'WSTĘPNE' in today_status:
        if completeness == 0:
            score -= 5
            reasons.append('DZISIAJ FUNDUSZE NIE OPUBLIKOWAŁY JESZCZE DANYCH')
        elif completeness < 70:
            score -= 3
            reasons.append('DZISIAJ DANE SĄ CZĘŚCIOWE')
    score = max(0, min(100, int(round(score))))
    if score >= 90:
        label = 'ŹRÓDŁO ŚWIEŻE — DANE ZAMKNIĘTE WIARYGODNE'
    elif score >= 75:
        label = 'DANE DOBRE, ALE DZISIEJSZY ODCZYT JESZCZE NIEPEŁNY'
    elif score >= 50:
        label = 'DANE WYMAGAJĄ OSTROŻNOŚCI'
    else:
        label = 'DANE ZA SŁABE DO PEWNEJ OCENY'
    return {'score_0_100': score, 'label_pl': label, 'reasons_pl': reasons}


def divergence(price_ret, flow, horizon):
    p = sf(price_ret)
    f = sf(flow)
    if p is None or f is None:
        return {'horizon': horizon, 'price_change_pct': p, 'etf_flow_usdm': f, 'label_pl': 'ZA MAŁO DANYCH DO PORÓWNANIA CENY I ETF', 'confirmation_adjustment': 0.0}
    ps, fs = sign(p), sign(f)
    if ps > 0 and fs > 0:
        label, adj = 'CENA I ETF POTWIERDZAJĄ SIĘ — NAPŁYW WSPIERA WZROST', 0.5
    elif ps < 0 and fs < 0:
        label, adj = 'CENA I ETF POTWIERDZAJĄ SŁABOŚĆ — ODPŁYW WSPIERA SPADEK', -0.5
    elif ps > 0 and fs < 0:
        label, adj = 'ROZBIEŻNOŚĆ: CENA ROŚNIE MIMO ODPŁYWU ETF — RUCH MA SŁABSZE POTWIERDZENIE', -0.5
    elif ps < 0 and fs > 0:
        label, adj = 'ROZBIEŻNOŚĆ: ETF KUPUJĄ PRZY SPADKU CENY — MOŻLIWA AKUMULACJA, ALE CENA JESZCZE NIE POTWIERDZA', 0.25
    elif ps == 0 and fs != 0:
        label, adj = 'CENA STOI, ALE ETF POKAZUJĄ KIERUNEK — CZEKAJ NA POTWIERDZENIE CENY', 0.0
    elif fs == 0 and ps != 0:
        label, adj = 'CENA SIĘ RUSZA, ALE ZAMKNIĘTE PRZEPŁYWY ETF SĄ NEUTRALNE', 0.0
    else:
        label, adj = 'CENA I ETF NEUTRALNE', 0.0
    return {'horizon': horizon, 'price_change_pct': p, 'etf_flow_usdm': f, 'label_pl': label, 'confirmation_adjustment': adj}


def asset_analysis(sym, status, lab):
    tech = ((lab.get('technical') or {}).get('1D') or {})
    ret5 = sf(tech.get('ret5_pct'))
    ret20 = sf(tech.get('ret20_pct'))
    d5 = divergence(ret5, status.get('closed_5d_usdm'), '5D')
    d20 = divergence(ret20, status.get('closed_20d_usdm'), '20D')
    q = quality_for_asset(status)
    adj = round((d5['confirmation_adjustment'] + d20['confirmation_adjustment']) / 2.0, 2)
    labels = {d5['label_pl'], d20['label_pl']}
    if any('ROZBIEŻNOŚĆ' in x and 'CENA ROŚNIE' in x for x in labels):
        overall = 'UWAGA — CENA ROŚNIE BEZ PEŁNEGO POTWIERDZENIA ETF'
    elif any('ROZBIEŻNOŚĆ' in x and 'ETF KUPUJĄ' in x for x in labels):
        overall = 'ETF WSKAZUJĄ AKUMULACJĘ, ALE CENA JESZCZE NIE POTWIERDZA'
    elif all('POTWIERDZAJĄ SIĘ' in x for x in labels):
        overall = 'CENA I ETF DAJĄ ZGODNE DODATNIE POTWIERDZENIE'
    elif all('POTWIERDZAJĄ SŁABOŚĆ' in x for x in labels):
        overall = 'CENA I ETF DAJĄ ZGODNE UJEMNE POTWIERDZENIE'
    else:
        overall = 'OBRAZ CENY I ETF JEST MIESZANY'
    return {
        'asset': sym,
        'quality': q,
        'last_closed_date': status.get('last_closed_date'),
        'last_closed_flow_usdm': status.get('last_closed_flow_usdm'),
        'closed_5d_usdm': status.get('closed_5d_usdm'),
        'closed_20d_usdm': status.get('closed_20d_usdm'),
        'closed_30d_usdm': status.get('closed_30d_usdm'),
        'flow_trend_pl': ((status.get('closed_trend') or {}).get('label_pl')),
        'today_status_pl': status.get('today_status_pl'),
        'today_preview_usdm': status.get('today_flow_preview_usdm'),
        'today_completeness_pct': status.get('today_fund_completeness_pct'),
        'price_ret5_pct': ret5,
        'price_ret20_pct': ret20,
        'price_vs_etf_5d': d5,
        'price_vs_etf_20d': d20,
        'overall_confirmation_pl': overall,
        'confirmation_adjustment': adj,
        'role': 'dodatkowy filtr jakości ruchu; nie nadpisuje blokad LONG ani TACTICAL',
    }


def main():
    etf = json.loads(ETF_STATUS.read_text(encoding='utf-8'))
    lab = json.loads(LAB_REPORT.read_text(encoding='utf-8'))
    lm = report_map(lab)
    assets = {}
    for sym in ('BTC', 'ETH'):
        if sym not in etf.get('assets', {}):
            raise RuntimeError(f'Brak {sym} w monitorze ETF')
        if sym not in lm:
            raise RuntimeError(f'Brak {sym} w LAB_REPORT')
        assets[sym] = asset_analysis(sym, etf['assets'][sym], lm[sym])
    global_ctx = etf.get('global_institutional_interest') or {}
    payload = {
        'generated_at_utc': NOW.isoformat(),
        'engine': 'V8_ETF_BTC_ETH_CONFIRMATION_v1.0',
        'assets': assets,
        'global_institutional_interest': global_ctx,
        'rules': {
            'closed_etf_days_only_for_confirmation': True,
            'today_preview_never_used_as_final': True,
            'price_etf_divergence_reduces_confirmation': True,
            'etf_never_overrides_hard_blockers': True,
            'execution_connected': False,
        },
    }
    (OUT / 'ETF_BTC_ETH_CONFIRMATION.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    rows = []
    for sym in ('BTC', 'ETH'):
        a = assets[sym]
        rows.append({
            'AKTYWO': sym,
            'JAKOSC_DANYCH_0_100': a['quality']['score_0_100'],
            'JAKOSC_DANYCH': a['quality']['label_pl'],
            'OSTATNI_ZAMKNIETY_DZIEN': a['last_closed_date'],
            '1D_MLN_USD': a['last_closed_flow_usdm'],
            '5D_MLN_USD': a['closed_5d_usdm'],
            '20D_MLN_USD': a['closed_20d_usdm'],
            '30D_MLN_USD': a['closed_30d_usdm'],
            'TREND_ETF': a['flow_trend_pl'],
            'CENA_5D_PROC': a['price_ret5_pct'],
            'CENA_20D_PROC': a['price_ret20_pct'],
            'CENA_VS_ETF_5D': a['price_vs_etf_5d']['label_pl'],
            'CENA_VS_ETF_20D': a['price_vs_etf_20d']['label_pl'],
            'WSPOLNY_WNIOSEK': a['overall_confirmation_pl'],
            'DZISIAJ_STATUS': a['today_status_pl'],
            'DZISIAJ_PODGLAD_MLN_USD': a['today_preview_usdm'],
            'DZISIAJ_KOMPLETNOSC_PROC': a['today_completeness_pct'],
        })
    pd.DataFrame(rows).to_csv(OUT / 'ETF_BTC_ETH_CONFIRMATION.csv', index=False)
    md = ['# V8 — POTWIERDZENIE ETF BTC / ETH', '', f"Wspólny obraz: **{global_ctx.get('label_pl', 'BRAK DANYCH')}**", f"Ocena zainteresowania instytucjonalnego: **{global_ctx.get('score_0_10', 'brak danych')}/10**", '']
    for sym in ('BTC', 'ETH'):
        a = assets[sym]
        md += [
            f'## {sym}',
            f"- Jakość danych: **{a['quality']['label_pl']} — {a['quality']['score_0_100']}/100**.",
            f"- Trend ETF: **{a['flow_trend_pl']}**.",
            f"- 5D cena vs ETF: {a['price_vs_etf_5d']['label_pl']}",
            f"- 20D cena vs ETF: {a['price_vs_etf_20d']['label_pl']}",
            f"- Wniosek: **{a['overall_confirmation_pl']}**.",
            f"- Dzisiaj: **{a['today_status_pl']}**; podgląd {a['today_preview_usdm']} mln USD; kompletność {a['today_completeness_pct']}%.",
            '',
        ]
    md += ['Dzisiejszy podgląd nie jest używany jako finalny przepływ. Filtr ETF nie nadpisuje twardych blokad silnika i nie wykonuje transakcji.']
    (OUT / 'ETF_BTC_ETH_CONFIRMATION.md').write_text('\n'.join(md), encoding='utf-8')
    print(json.dumps({sym: assets[sym]['overall_confirmation_pl'] for sym in assets}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
