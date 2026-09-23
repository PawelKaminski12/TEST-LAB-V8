import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT=Path('crypto_data_hub')
CFG=Path('config/alt_universe.csv')
TECH=ROOT/'ALT_TECHNICAL_LAYER.json'
ZONES=Path('config/alt_zones.csv')
PHASE=ROOT/'CRYPTO_MARKET_PHASE.json'
OUT=ROOT/'ALT_DECISION_ENGINE.json'
HIST=ROOT/'ALT_DECISION_HISTORY.csv'
EXPECTED=['ETH','SOL','LINK','ONDO','RENDER','FLOKI','PEPE','SPX6900','XRP','XLM','HBAR','AVAX','AWE']
REQUIRED_TF=['1D','2D','3D','4D','5D','1T','2T']


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def zone_state(zones,sym,price):
    z=zones[(zones['symbol'].str.upper()==sym)&(zones['source_status'].str.upper()=='CONFIRMED')].copy()
    z['timeframe']=z['timeframe'].str.upper(); z['side']=z['side'].str.upper()
    z['from_n']=pd.to_numeric(z['from'],errors='coerce'); z['to_n']=pd.to_numeric(z['to'],errors='coerce')
    z=z.dropna(subset=['from_n','to_n']); z=z[z['to_n']>=z['from_n']]
    tfs=sorted(set(z['timeframe']))
    missing=[tf for tf in REQUIRED_TF if tf not in tfs]
    dem=z[z['side']=='DEMAND']; sup=z[z['side']=='SUPPLY']
    def in_zone(part):
        return any(float(r.from_n)<=price<=float(r.to_n) for _,r in part.iterrows())
    def nearest(part):
        if part.empty: return None
        def d(r):
            lo,hi=float(r.from_n),float(r.to_n)
            if lo<=price<=hi: return 0.0
            return min(abs(price-lo),abs(price-hi))
        r=min((r for _,r in part.iterrows()),key=d)
        return {'timeframe':str(r.timeframe),'from':float(r.from_n),'to':float(r.to_n),'distance_pct':d(r)/price*100}
    d1=dem[dem['timeframe']=='1D']
    t1=dem[dem['timeframe']=='1T'].copy()
    dca1=float(d1['to_n'].max()) if not d1.empty else None
    dca3=None
    if not t1.empty:
        note=t1.get('source_note',pd.Series('',index=t1.index)).fillna('').astype(str).str.upper()
        canon=t1[note.str.contains('KANON DCA3',regex=False)]
        if not canon.empty:
            dca3=float(canon['from_n'].min())
        else:
            exclude=(note.str.contains('NIE UZYWAJ',regex=False)|note.str.contains('NIE UŻYWAJ',regex=False)|note.str.contains('REZERWOWA',regex=False)|note.str.contains('HISTORYCZNA',regex=False)|note.str.contains('ARCHIWAL',regex=False))
            active=t1[~exclude]
            if not active.empty: dca3=float(active['from_n'].min())
    dca2=(dca1+dca3)/2 if dca1 is not None and dca3 is not None else None
    return {
        'complete_7_of_7':len(missing)==0,
        'confirmed_timeframes':tfs,
        'missing_timeframes':missing,
        'in_demand':in_zone(dem),
        'in_supply':in_zone(sup),
        'nearest_demand':nearest(dem),
        'nearest_supply':nearest(sup),
        'dca1':dca1,'dca2':dca2,'dca3':dca3,
    }


def main():
    cfg=pd.read_csv(CFG)
    cfg=cfg[cfg['enabled'].astype(str).str.lower().eq('true')]
    active=[s for s in cfg['symbol'].astype(str).str.upper().tolist() if s!='BTC']
    if active!=EXPECTED: raise SystemExit(f'Nieprawidłowa lista LONG: {active}')
    tech=load_json(TECH)
    if tech.get('engine')!='ALT_TECHNICAL_LAYER_v1.0' or tech.get('asset_count')!=13:
        raise SystemExit('Brak kompletnej techniki LONG 13/13')
    tmap={x['symbol']:x for x in tech.get('assets',[]) if x.get('qa')=='PASS'}
    zones=pd.read_csv(ZONES)
    zones['symbol']=zones['symbol'].astype(str); zones['timeframe']=zones['timeframe'].astype(str); zones['side']=zones['side'].astype(str); zones['source_status']=zones['source_status'].astype(str)
    phase=load_json(PHASE)
    flow=((phase.get('dual_horizon_flow_context') or {}).get('LONG') or {})
    rotation_score=phase.get('rotation_score_0_10') or phase.get('alt_rotation_score_0_10')
    if rotation_score is None:
        rotation_score=phase.get('inputs',{}).get('alt_rotation_score_0_10')
    assets=[]
    for sym in EXPECTED:
        t=tmap.get(sym)
        if not t: raise SystemExit(f'{sym}: brak techniki')
        price=float(t['close']); zs=zone_state(zones,sym,price)
        trend=int(t.get('trend_score_0_4') or 0); fomo=int(t.get('fomo_score_0_10') or 0)
        retest=bool(t.get('retest_confirmed_10d')); breakout=bool(t.get('fresh_breakout_20d')); vr=float(t.get('volume_ratio_vs_20d') or 0)
        blockers=[]; entry=[]
        if not zs['complete_7_of_7']: blockers.append('BRAK_PEŁNEJ_MAPY_STREF_7_Z_7')
        if zs['in_supply']: entry.append('W_STREFIE_PODAŻY')
        if fomo>=8: entry.append('FOMO_SKRAJNE')
        if blockers:
            decision='DANE NIEPEŁNE'; reason='Technika działa, ale pełna decyzja LONG czeka na potwierdzone strefy 7/7.'
        elif fomo>=8:
            decision='CZEKAJ'; reason='FOMO jest skrajne — nowe wejście zablokowane.'
        elif zs['in_supply']:
            decision='SPRAWDŹ'; reason='Cena znajduje się w potwierdzonej strefie podaży.'
        elif zs['in_demand'] and trend>=2:
            decision='KUP DCA'; reason='Cena w potwierdzonym popycie, trend nie jest złamany.'
        elif trend>=3 and retest and fomo<=5:
            decision='KUP PO RETEŚCIE'; reason='Trend mocny, retest potwierdzony, brak skrajnego FOMO.'
        elif trend>=3 and breakout and fomo<=5:
            decision='SPRAWDŹ'; reason='Świeże wybicie — czekamy na utrzymanie lub retest.'
        elif trend>=4 and fomo<=4 and vr>=1.0:
            decision='KUP TRENDOWO'; reason='Silny trend, wolumen i brak blokad podaży/FOMO.'
        else:
            decision='CZEKAJ'; reason='Brak pełnego zestawu warunków wejścia.'
        if decision.startswith('KUP') and (blockers or entry):
            raise SystemExit(f'{sym}: niedozwolone KUP z blokadą')
        assets.append({
            'symbol':sym,'price':price,'decision':decision,'reason_pl':reason,
            'technical_ready':True,'zones':zs,'trend_score_0_4':trend,'fomo_score_0_10':fomo,
            'fresh_breakout_20d':breakout,'retest_confirmed_10d':retest,'volume_ratio_vs_20d':vr,
            'rsi14':t.get('rsi14'),'mfi14':t.get('mfi14'),'macd_hist':t.get('macd_hist'),
            'market_phase':phase.get('phase'),'long_flow_score':flow.get('score_0_10'),'long_flow_label':flow.get('label'),
            'blockers':blockers,'entry_blockers':entry,
            'dca1':zs['dca1'],'dca2':zs['dca2'],'dca3':zs['dca3'],
        })
    out={
        'generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'engine':'ALT_DECISION_ENGINE_v1.0','asset_count':len(EXPECTED),'universe':EXPECTED,
        'btc_role':'REŻIM RYNKU — nie jest wierszem decyzji alta',
        'stocks_role':'SPÓŁKI pozostają osobną częścią silnika LONG',
        'rules':{'no_zone_guessing':True,'full_zone_map_required_for_final_long_decision':True,'fomo_hard_block_at_8':True,'no_buy_in_supply':True,'execution_connected':False},
        'assets':assets
    }
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    new=pd.DataFrame([{'date':datetime.now(timezone.utc).date().isoformat(),'symbol':x['symbol'],'decision':x['decision'],'price':x['price'],'trend_score':x['trend_score_0_4'],'fomo_score':x['fomo_score_0_10'],'zones_complete':x['zones']['complete_7_of_7'],'blockers':'|'.join(x['blockers']),'entry_blockers':'|'.join(x['entry_blockers'])} for x in assets])
    if HIST.exists():
        old=pd.read_csv(HIST); new=pd.concat([old,new],ignore_index=True).drop_duplicates(['date','symbol'],keep='last').sort_values(['date','symbol'])
    new.to_csv(HIST,index=False)
    print(json.dumps({'engine':out['engine'],'asset_count':len(EXPECTED),'technical_ready':sum(a['technical_ready'] for a in assets),'zones_7_of_7':sum(a['zones']['complete_7_of_7'] for a in assets)},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
