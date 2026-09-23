import json
from datetime import datetime, timezone
from pathlib import Path

OUT=Path('institutional_data_hub')
LAB=Path('lab/LAB_REPORT.json')
ETF=OUT/'ETF_BTC_ETH_STATUS.json'
HIST=OUT/'ETF_BTC_ETH_HISTORY_STATUS.json'


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def safe(v):
    try:
        return float(v)
    except Exception:
        return None


def classify(asset, price5, etf5, accel, streak_dir, streak_days):
    if price5 is None or etf5 is None:
        return {
            'status_pl':'ZA MAŁO DANYCH',
            'quality_pl':'NIEPEŁNE',
            'meaning_pl':'Brakuje pełnych danych do porównania ceny z przepływami ETF.',
            'score_adjustment':0.0,
            'risk_flag':None,
        }

    price_up=price5>0
    price_down=price5<0
    flow_up=etf5>0
    flow_down=etf5<0
    accel_up=(accel or 0)>0
    accel_down=(accel or 0)<0

    if price_up and flow_up:
        if accel_up:
            return {
                'status_pl':'CENA I ETF POTWIERDZAJĄ WZROST',
                'quality_pl':'MOCNE POTWIERDZENIE',
                'meaning_pl':'Cena rośnie, a kapitał ETF napływa i przyspiesza. Ruch ma wsparcie ze strony rynku tradycyjnego.',
                'score_adjustment':0.4,
                'risk_flag':None,
            }
        return {
            'status_pl':'CENA ROŚNIE, ETF NADAL NAPŁYWA',
            'quality_pl':'POTWIERDZENIE',
            'meaning_pl':'Cena rośnie razem z dodatnimi przepływami ETF, ale tempo napływu nie przyspiesza.',
            'score_adjustment':0.2,
            'risk_flag':None,
        }

    if price_down and flow_down:
        if accel_down:
            return {
                'status_pl':'CENA I ETF POTWIERDZAJĄ SŁABOŚĆ',
                'quality_pl':'MOCNE OSTRZEŻENIE',
                'meaning_pl':'Cena spada, a odpływy ETF rosną. Słabość jest potwierdzona przez kapitał tradycyjny.',
                'score_adjustment':-0.4,
                'risk_flag':'CENA_I_ETF_SŁABE',
            }
        return {
            'status_pl':'CENA SPADA I ETF ODPŁYWA',
            'quality_pl':'OSTRZEŻENIE',
            'meaning_pl':'Cena i przepływy ETF wskazują ten sam słaby kierunek.',
            'score_adjustment':-0.2,
            'risk_flag':'CENA_I_ETF_SŁABE',
        }

    if price_up and flow_down:
        return {
            'status_pl':'ROZBIEŻNOŚĆ — CENA ROŚNIE, ETF ODPŁYWA',
            'quality_pl':'RUCH CENOWY SŁABIEJ POTWIERDZONY',
            'meaning_pl':'Cena rośnie bez wsparcia przepływów ETF. Traktujemy wzrost ostrożniej i nie podnosimy oceny tylko na podstawie ceny.',
            'score_adjustment':-0.35,
            'risk_flag':'ROZBIEŻNOŚĆ_CENA_W_GÓRĘ_ETF_W_DÓŁ',
        }

    if price_down and flow_up:
        extra=''
        if streak_dir=='NAPŁYW' and (streak_days or 0)>=2:
            extra=f' Napływ ETF trwa już {streak_days} kolejne zakończone dni.'
        return {
            'status_pl':'ROZBIEŻNOŚĆ — CENA SPADA, ETF NAPŁYWA',
            'quality_pl':'AKUMULACJA DO OBSERWACJI',
            'meaning_pl':'Cena słabnie mimo dodatnich przepływów ETF. To może oznaczać absorpcję podaży lub opóźnioną reakcję ceny.'+extra,
            'score_adjustment':0.1,
            'risk_flag':'ROZBIEŻNOŚĆ_CENA_W_DÓŁ_ETF_W_GÓRĘ',
        }

    return {
        'status_pl':'BRAK WYRAŹNEJ ZGODNOŚCI',
        'quality_pl':'NEUTRALNIE',
        'meaning_pl':'Cena lub przepływy ETF są blisko zera. Nie wyciągamy mocnego wniosku.',
        'score_adjustment':0.0,
        'risk_flag':None,
    }


def main():
    lab=load_json(LAB)
    etf=load_json(ETF)
    hist=load_json(HIST)
    reports={r.get('symbol'):r for r in lab.get('reports',[])}
    hist_assets=hist.get('assets',{})

    assets={}
    for symbol in ['BTC','ETH']:
        r=reports.get(symbol,{})
        one_d=((r.get('technical') or {}).get('1D') or {})
        price5=safe(one_d.get('ret5_pct'))
        e=(etf.get('assets') or {}).get(symbol,{})
        etf5=safe(e.get('closed_5d_usdm'))
        accel=safe(((e.get('closed_trend') or {}).get('acceleration_5d_usdm')))
        hs=hist_assets.get(symbol,{})
        streak_dir=hs.get('current_streak_direction_pl')
        streak_days=hs.get('current_streak_days')
        c=classify(symbol,price5,etf5,accel,streak_dir,streak_days)
        assets[symbol]={
            'price_change_5d_pct':price5,
            'etf_closed_5d_usdm':etf5,
            'etf_acceleration_5d_usdm':accel,
            'etf_last_closed_date':e.get('last_closed_date'),
            'etf_last_closed_flow_usdm':e.get('last_closed_flow_usdm'),
            'streak_direction_pl':streak_dir,
            'streak_days':streak_days,
            **c,
            'today_data_policy_pl':'Dzisiejsze niepełne dane ETF nie wpływają na ocenę rozbieżności. Używamy tylko zakończonych dni.',
        }

    payload={
        'generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'engine':'V8_ETF_PRICE_DIVERGENCE_v1.0',
        'assets':assets,
        'rules':{
            'closed_etf_days_only':True,
            'same_day_preview_excluded':True,
            'context_not_trade_signal':True,
            'execution_connected':False,
        }
    }
    (OUT/'ETF_PRICE_DIVERGENCE.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')

    lines=['# V8 — ZGODNOŚĆ CENY Z PRZEPŁYWAMI ETF','']
    for symbol in ['BTC','ETH']:
        x=assets[symbol]
        lines += [
            f'## {symbol}',
            f"- Cena 5 dni: {x['price_change_5d_pct']:.2f}%" if x['price_change_5d_pct'] is not None else '- Cena 5 dni: brak danych',
            f"- ETF 5 zakończonych dni: {x['etf_closed_5d_usdm']:.1f} mln USD" if x['etf_closed_5d_usdm'] is not None else '- ETF 5 dni: brak danych',
            f"- Ocena: **{x['status_pl']}**",
            f"- Jakość potwierdzenia: **{x['quality_pl']}**",
            f"- Znaczenie: {x['meaning_pl']}",
            ''
        ]
    lines += [
        'Ocena używa wyłącznie zakończonych dni ETF. Dzisiejszy podgląd nie jest traktowany jako wynik końcowy.',
        'To jest warstwa kontekstu, nie samodzielny sygnał kupna ani sprzedaży.'
    ]
    (OUT/'ETF_PRICE_DIVERGENCE_LATEST.md').write_text('\n'.join(lines),encoding='utf-8')

    print(json.dumps({s:assets[s]['status_pl'] for s in assets},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
