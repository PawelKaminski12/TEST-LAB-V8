import json
from pathlib import Path

REPORT=Path('lab/LAB_REPORT.json')
OUT=Path('lab/LAB_LATEST.md')

def fmt(v,d=2):
    if v is None:return 'brak danych'
    try:return f'{float(v):.{d}f}'
    except Exception:return str(v)

def fmt_score(v):
    return 'brak danych' if v is None else f'{v}/10'

def fmt_trend(v):
    return 'brak danych' if v is None else f'{v}/4'

def fmt_fomo(v):
    return 'brak danych' if v is None else f'{v}/10'

def phase_pl(x):
    return {
        'ALT_ROTATION_CANDIDATE':'RYNEK ZACZYNA SPRZYJAĆ ALTOM',
        'ALT_ROTATION_CONFIRMED':'ROTACJA W ALTY POTWIERDZONA',
        'BTC_DOMINANCE':'DOMINUJE BITCOIN',
        'RISK_OFF':'RYNEK OSTROŻNY / UCIECZKA OD RYZYKA',
    }.get(x, 'brak jednoznacznej fazy rynku' if not x else str(x).replace('_',' '))

def main():
    x=json.loads(REPORT.read_text(encoding='utf-8'))
    lines=['# V8 LAB — NAJNOWSZA ANALIZA','',f"Czas analizy: {x.get('generated_at_utc','')}",'']
    for a in x.get('reports',[]):
        tt=a.get('technical') or {}; t1=tt.get('1H') or {}; t4=tt.get('4H') or {}; td=tt.get('1D') or {}
        fast=a.get('fast_analysis') or {}; deep=a.get('deep_observation') or {}; pl=a.get('opis_po_polsku') or {}
        risks=pl.get('ryzyka') or []
        lines += [
            f"## {a.get('symbol')} — {pl.get('typ_aktywa','')} — {pl.get('tryb','')}",
            f"- Stan danych: **{pl.get('stan_danych','')}** ({a.get('data_quality_0_100')}/100). Pełne interwały: {a.get('mtf_ready_0_3')}/3.",
            f"- Wniosek z szybkiej analizy: **{pl.get('wniosek_szybki','')} — {fmt(fast.get('score_0_10'))}/10**.",
            f"- Ryzyka / ostrzeżenia: {', '.join(risks) if risks else 'brak ważnych ostrzeżeń'}.",
            f"- 1 godzina: trend {fmt_trend(t1.get('trend_0_4'))}, RSI {fmt(t1.get('rsi14'))}, MFI {fmt(t1.get('mfi14'))}, FOMO {fmt_fomo(t1.get('fomo_0_10'))}.",
            f"- 4 godziny: trend {fmt_trend(t4.get('trend_0_4'))}, RSI {fmt(t4.get('rsi14'))}, MFI {fmt(t4.get('mfi14'))}, FOMO {fmt_fomo(t4.get('fomo_0_10'))}.",
            f"- 1 dzień: cena {fmt(td.get('price'))}, trend {fmt_trend(td.get('trend_0_4'))}, RSI {fmt(td.get('rsi14'))}, MFI {fmt(td.get('mfi14'))}, FOMO {fmt_fomo(td.get('fomo_0_10'))}.",
        ]
        if a.get('asset_type') in ('CRYPTO','MEME'):
            m=a.get('crypto_market_context') or {}; o=a.get('onchain_context') or {}; e=a.get('existing_engine_context') or {}
            lines += [
                f"- Sytuacja rynku krypto: **{phase_pl(m.get('phase'))}** | siła rotacji w alty: {fmt_score(m.get('rotation_score_0_10'))}.",
                f"- Dominacja BTC: {fmt(m.get('btc_dominance_pct'))}% | dominacja ETH: {fmt(m.get('eth_dominance_pct'))}% | ETH/BTC za 20 dni: {fmt(m.get('eth_btc_20d_pct'))}%.",
                f"- Płynność stablecoinów: 7 dni {fmt(m.get('stablecoin_7d_pct'))}% | 30 dni {fmt(m.get('stablecoin_30d_pct'))}%.",
                f"- Dane z sieci blockchain: długi termin {fmt_score(o.get('long_score'))} | krótki termin {fmt_score(o.get('tactical_score'))}.",
                f"- Decyzja głównego silnika: {e.get('decision') or 'brak osobnej decyzji dla tego aktywa'}.",
            ]
            if a.get('symbol')=='BTC':
                b=a.get('btc_etf_context') or {}
                lines += [
                    f"- **ETF BTC: {b.get('label_pl','BRAK DANYCH')}**.",
                    f"- Przepływ do ETF BTC: 1 dzień {fmt(b.get('flow_1d_usdm'))} mln USD | 5 dni {fmt(b.get('flow_5d_usdm'))} mln USD | 20 dni {fmt(b.get('flow_20d_usdm'))} mln USD | 30 dni {fmt(b.get('flow_30d_usdm'))} mln USD.",
                    f"- Zmiana tempa napływów z ostatnich 5 dni: {fmt(b.get('acceleration_5d_usdm'))} mln USD.",
                    f"- Co to znaczy: {b.get('explanation_pl','')}",
                ]
            else:
                lines += [f"- Tło ETF: BTC 5 dni {fmt(m.get('btc_etf_5d_usdm'))} mln USD / 20 dni {fmt(m.get('btc_etf_20d_usdm'))} mln USD; ETH 5 dni {fmt(m.get('eth_etf_5d_usdm'))} mln USD / 20 dni {fmt(m.get('eth_etf_20d_usdm'))} mln USD."]
        else:
            f=a.get('stock_fundamentals') or {}
            rg=(f.get('revenue_growth') or 0)*100; eg=(f.get('earnings_growth') or 0)*100
            lines += [
                f"- Kapitalizacja: {fmt(f.get('market_cap'),0)} | P/E: {fmt(f.get('trailing_pe'))} | przyszłe P/E: {fmt(f.get('forward_pe'))} | cena/sprzedaż: {fmt(f.get('price_to_sales'))}.",
                f"- Wzrost przychodów: {fmt(rg)}% | wzrost zysków: {fmt(eg)}% | wolne przepływy pieniężne: {fmt(f.get('free_cashflow'),0)}.",
            ]
        if deep:
            lines += [f"- Głęboka obserwacja: **{pl.get('stan_obserwacji','')}**. Minęło {fmt(deep.get('elapsed_days'))} dnia; zmiana ceny od punktu startowego {fmt(deep.get('price_change_pct'))}%."]
        lines += ['','---','']
    lines += ['Wynik LAB-u jest pomocą w analizie. Nie jest automatycznym poleceniem kupna ani sprzedaży.','LAB nie wykonuje transakcji i nie dodaje aktywów automatycznie do portfela produkcyjnego.']
    OUT.write_text('\n'.join(lines),encoding='utf-8')

if __name__=='__main__': main()
