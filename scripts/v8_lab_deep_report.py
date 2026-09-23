import json
from pathlib import Path
from datetime import datetime, timezone
import math
import pandas as pd

ROOT=Path('lab')
REPORT=ROOT/'LAB_REPORT.json'
CHECKPOINTS=ROOT/'LAB_CHECKPOINTS.csv'
OUT_JSON=ROOT/'LAB_DEEP_REPORT.json'
OUT_CSV=ROOT/'LAB_DEEP_REPORT.csv'
OUT_MD=ROOT/'LAB_DEEP_REPORT.md'
NOW=datetime.now(timezone.utc)


def sf(v):
    try:
        x=float(v)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def diff(cur, old):
    a=sf(cur); b=sf(old)
    return None if a is None or b is None else a-b


def pct(cur, old):
    a=sf(cur); b=sf(old)
    if a is None or b in (None,0): return None
    return (a/b-1)*100


def pl_data(v):
    return {
        'DATA_READY':'DANE WYSTARCZAJĄCE DO ANALIZY',
        'PARTIAL':'DANE NIEPEŁNE — WYNIK TRAKTUJ OSTROŻNIE',
        'NO_DATA':'BRAK WYSTARCZAJĄCYCH DANYCH'
    }.get(str(v),str(v))


def pl_fast(v):
    return {
        'STRONG_CONTEXT':'MOCNE POTWIERDZENIE',
        'POSITIVE_CONTEXT':'PRZEWAGA SYGNAŁÓW POZYTYWNYCH',
        'MIXED_CONTEXT':'SYGNAŁY MIESZANE',
        'WEAK_CONTEXT':'SŁABE POTWIERDZENIE',
        'HIGH_FOMO_RISK':'RYNEK MOCNO ROZGRZANY — NIE GONIĆ CENY',
        'INSUFFICIENT_DATA':'ZA MAŁO DANYCH DO OCENY'
    }.get(str(v),str(v))


def trend_word(x):
    x=sf(x)
    if x is None: return 'BRAK PORÓWNANIA'
    if x >= 1.0: return 'WYRAŹNA POPRAWA'
    if x > 0: return 'LEKKA POPRAWA'
    if x <= -1.0: return 'WYRAŹNE POGORSZENIE'
    if x < 0: return 'LEKKIE POGORSZENIE'
    return 'BEZ ZMIANY'


def fmt(v,d=2):
    x=sf(v)
    return 'brak danych' if x is None else f'{x:.{d}f}'


def main():
    if not REPORT.exists(): raise SystemExit('Brakuje lab/LAB_REPORT.json')
    current=json.loads(REPORT.read_text(encoding='utf-8'))
    cps=pd.read_csv(CHECKPOINTS) if CHECKPOINTS.exists() and CHECKPOINTS.stat().st_size else pd.DataFrame()

    assets=[]; rows=[]; md=['# V8 LAB — GŁĘBOKA OBSERWACJA','',f'Czas raportu: {NOW.isoformat()}','']
    for a in current.get('reports',[]):
        sym=str(a.get('symbol','')).upper(); typ=str(a.get('asset_type',''))
        td=((a.get('technical') or {}).get('1D') or {})
        fast=a.get('fast_analysis') or {}; oc=a.get('onchain_context') or {}; ec=a.get('etf_context') or {}
        engine=a.get('existing_engine_context') or {}

        z=cps[cps['symbol'].astype(str).str.upper().eq(sym)].copy() if not cps.empty and 'symbol' in cps.columns else pd.DataFrame()
        if not z.empty:
            z['captured_at_utc']=pd.to_datetime(z['captured_at_utc'],utc=True,errors='coerce')
            z=z.sort_values(['target_day','captured_at_utc'])
            d0=z[z['checkpoint'].astype(str).eq('D0')]
            baseline=(d0.iloc[0] if not d0.empty else z.iloc[0])
            latest=z.iloc[-1]
            checkpoints_seen=[str(x) for x in z['checkpoint'].tolist()]
        else:
            baseline=None; latest=None; checkpoints_seen=[]

        cur={'price':td.get('price'),'trend':td.get('trend_0_4'),'rsi':td.get('rsi14'),'mfi':td.get('mfi14'),'fomo':td.get('fomo_0_10'),'fast_score':fast.get('score_0_10'),'onchain_long':oc.get('long_score'),'onchain_tactical':oc.get('tactical_score'),'engine_decision':engine.get('decision'),'etf_label':ec.get('label_pl')}
        if baseline is not None:
            changes={'price_pct':pct(cur['price'],baseline.get('price')),'trend_change':diff(cur['trend'],baseline.get('trend_1D_0_4')),'rsi_change':diff(cur['rsi'],baseline.get('rsi_1D')),'mfi_change':diff(cur['mfi'],baseline.get('mfi_1D')),'fomo_change':diff(cur['fomo'],baseline.get('fomo_1D_0_10')),'fast_score_change':diff(cur['fast_score'],baseline.get('fast_score_0_10')),'onchain_long_change':diff(cur['onchain_long'],baseline.get('onchain_long')),'onchain_tactical_change':diff(cur['onchain_tactical'],baseline.get('onchain_tactical'))}
            baseline_time=str(baseline.get('captured_at_utc')); baseline_cp=str(baseline.get('checkpoint'))
        else:
            changes={k:None for k in ['price_pct','trend_change','rsi_change','mfi_change','fomo_change','fast_score_change','onchain_long_change','onchain_tactical_change']}; baseline_time=None; baseline_cp=None

        next_cp='BRAK — OBSERWACJA ZAKOŃCZONA'
        plan=['D0','D1','D3','D7','D30'] if typ in ('CRYPTO','MEME') else ['D0','D7','D30']
        for cp in plan:
            if cp not in checkpoints_seen:
                next_cp=cp; break

        summary=[]
        if changes['price_pct'] is not None: summary.append(f"Cena od punktu startowego: {changes['price_pct']:+.2f}%")
        if changes['fast_score_change'] is not None: summary.append(f"Ocena LAB zmieniła się o {changes['fast_score_change']:+.2f} pkt")
        if changes['trend_change'] is not None: summary.append('Trend: '+trend_word(changes['trend_change']))
        if sym in ('BTC','ETH') and ec.get('label_pl'): summary.append('ETF: '+str(ec.get('label_pl')))
        if not summary: summary.append('Na razie brak wystarczającego punktu odniesienia do porównania zmian.')

        rec={
            'symbol':sym,'asset_type':typ,
            'stan_danych_pl':pl_data(a.get('data_status')),
            'ocena_biezaca_pl':pl_fast(fast.get('label')),
            'ocena_biezaca_0_10':cur['fast_score'],
            'punkt_startowy':baseline_cp,'punkt_startowy_czas':baseline_time,
            'zapisane_punkty':' | '.join(checkpoints_seen),
            'nastepny_punkt':next_cp,
            'cena_biezaca':cur['price'],
            'zmiana_ceny_od_startu_pct':changes['price_pct'],
            'zmiana_oceny_od_startu':changes['fast_score_change'],
            'zmiana_trendu_od_startu':changes['trend_change'],
            'zmiana_rsi_od_startu':changes['rsi_change'],
            'zmiana_mfi_od_startu':changes['mfi_change'],
            'zmiana_fomo_od_startu':changes['fomo_change'],
            'onchain_long':cur['onchain_long'],'onchain_tactical':cur['onchain_tactical'],
            'etf_status':cur['etf_label'],'decyzja_glownego_silnika':cur['engine_decision'],
            'opis_zmian':' | '.join(summary)
        }
        rows.append(rec)
        assets.append({'symbol':sym,'status_po_polsku':rec,'zmiany_od_punktu_startowego':changes,'immutable_checkpoint_count':len(z),'next_checkpoint':next_cp})

        md += [f'## {sym}',f"- Stan danych: **{rec['stan_danych_pl']}**.",f"- Bieżąca ocena LAB: **{rec['ocena_biezaca_pl']} — {fmt(rec['ocena_biezaca_0_10'])}/10**.",f"- Zapisane punkty obserwacji: {rec['zapisane_punkty'] or 'brak'}.",f"- Następny punkt obserwacji: **{next_cp}**.",f"- Cena od punktu startowego: {fmt(rec['zmiana_ceny_od_startu_pct'])}%.",f"- Zmiana oceny LAB od startu: {fmt(rec['zmiana_oceny_od_startu'])} pkt.",f"- Zmiana trendu od startu: {fmt(rec['zmiana_trendu_od_startu'])}.",f"- Zmiana RSI: {fmt(rec['zmiana_rsi_od_startu'])} | zmiana MFI: {fmt(rec['zmiana_mfi_od_startu'])} | zmiana FOMO: {fmt(rec['zmiana_fomo_od_startu'])}."]
        if sym in ('BTC','ETH'): md += [f"- Przepływy ETF: **{rec['etf_status'] or 'brak danych'}**."]
        if cur['engine_decision']: md += [f"- Decyzja głównego silnika: **{cur['engine_decision']}**."]
        md += [f"- Co się zmieniło: {rec['opis_zmian']}.",'','---','']

    payload={'generated_at_utc':NOW.isoformat(),'engine':'V8_LAB_DEEP_REPORT_v0.1','source_lab_engine':current.get('engine'),'assets':assets,'rules':{'uses_immutable_canonical_checkpoints':True,'baseline_prefers_D0':True,'user_language_polish':True,'research_only':True,'portfolio_connection':False,'execution_connection':False}}
    OUT_JSON.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8')
    pd.DataFrame(rows).to_csv(OUT_CSV,index=False)
    md += ['Raport pokazuje zmianę od trwałego punktu startowego D0. Nie jest automatycznym poleceniem kupna ani sprzedaży.']
    OUT_MD.write_text('\n'.join(md),encoding='utf-8')
    print(json.dumps({'engine':payload['engine'],'assets':len(assets),'status':'OK'},ensure_ascii=False))

if __name__=='__main__': main()
