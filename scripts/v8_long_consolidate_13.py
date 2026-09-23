#!/usr/bin/env python3
import csv, json, math
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path('.')
OUT=ROOT/'crypto_data_hub'; OUT.mkdir(exist_ok=True)
ALTS=['ETH','SOL','LINK','ONDO','RENDER','FLOKI','PEPE','SPX6900','XRP','XLM','HBAR','AVAX','AWE']
ZT=['1D','2D','3D','4D','5D','1T','2T']
NOW=datetime.now(timezone.utc).isoformat()


def load_json(path, default=None):
    p=ROOT/path
    if not p.exists():
        return {} if default is None else default
    return json.loads(p.read_text(encoding='utf-8'))

def read_csv(path):
    with (ROOT/path).open(encoding='utf-8',newline='') as f:
        return list(csv.DictReader(f))

def fnum(x):
    try:
        v=float(x)
        return v if math.isfinite(v) else None
    except:
        return None

cfg=read_csv('config/alt_universe.csv')
active=[r['symbol'].upper() for r in cfg if r.get('enabled','').lower()=='true' and r['symbol'].upper()!='BTC']
if active!=ALTS:
    raise SystemExit(f'Nieprawidłowa lista LONG: {active}')

tactical=load_json('tactical_engine/TACTICAL_ENGINE.json')
if tactical.get('engine')!='V8_TACTICAL_ENGINE_v1.0' or tactical.get('asset_count')!=14:
    raise SystemExit('TACTICAL nie jest gotowy jako v1.0 / 14 aktywów')
tmap={a.get('symbol'):a for a in tactical.get('assets',[]) if a.get('qa')=='PASS'}

zones=read_csv('config/alt_zones.csv')
zmap={s:[] for s in ALTS}
for r in zones:
    s=r.get('symbol','').upper(); tf=r.get('timeframe','').upper(); side=r.get('side','').upper()
    lo=fnum(r.get('from')); hi=fnum(r.get('to'))
    if s in zmap and tf in ZT and r.get('source_status','').upper()=='CONFIRMED' and lo is not None and hi is not None and lo>=0 and hi>lo:
        zmap[s].append({'timeframe':tf,'side':side,'from':lo,'to':hi,'source_note':r.get('source_note','')})

phase=load_json('crypto_data_hub/CRYPTO_MARKET_PHASE.json')
rotation=load_json('crypto_data_hub/ALT_ROTATION_SCORE.json')
global_score=int(rotation.get('score_0_10') or 0)
market_phase=phase.get('phase')

tech_assets=[]; decisions=[]; readiness=[]
for sym in ALTS:
    a=tmap.get(sym)
    if not a:
        raise SystemExit(f'Brak poprawnych danych TACTICAL dla {sym}')
    d1=(a.get('timeframes') or {}).get('1D') or {}
    req=['close','trend_score_0_4','fomo_score_0_10','volume_ratio_vs_20','breakout_20','retest_10','return_20bars_pct']
    miss=[k for k in req if d1.get(k) is None]
    if miss or d1.get('closed_bar_only') is not True or d1.get('stale') is True:
        raise SystemExit(f'{sym}: niepełna technika 1D: {miss}')
    price=float(d1['close']); trend=int(d1.get('trend_score_0_4') or 0); fomo=int(d1.get('fomo_score_0_10') or 0)
    tech_assets.append({
        'symbol':sym,'pair':a.get('pair'),'qa':'PASS','source':'TACTICAL 1D — zamknięta świeca','source_type':(a.get('source_types') or {}).get('1D'),
        'close':price,'trend_score_0_4':trend,'return_20d_pct':d1.get('return_20bars_pct'),'volume_ratio_vs_20d':d1.get('volume_ratio_vs_20'),
        'fresh_breakout_20d':bool(d1.get('breakout_20')),'retest_confirmed_10d':bool(d1.get('retest_10')),'retest_level':d1.get('retest_level'),
        'fomo_score_0_10':fomo,'fomo_label':d1.get('fomo_label'),'rsi14':d1.get('rsi14'),'mfi14':d1.get('mfi14'),'macd_hist':d1.get('macd_hist'),
        'closed_bar_only':True,'last_close_time_utc':d1.get('last_close_time_utc')
    })

    zz=zmap[sym]; tfs=sorted({z['timeframe'] for z in zz},key=ZT.index); missing=[tf for tf in ZT if tf not in tfs]
    if missing:
        raise SystemExit(f'{sym}: brakuje stref {missing}')
    dem=[z for z in zz if z['side']=='DEMAND']; sup=[z for z in zz if z['side']=='SUPPLY']
    in_dem=any(z['from']<=price<=z['to'] for z in dem); in_sup=any(z['from']<=price<=z['to'] for z in sup)
    d1dem=[z for z in dem if z['timeframe']=='1D']
    d1v=max((z['to'] for z in d1dem),default=None)
    wt=[z for z in dem if z['timeframe']=='1T']
    active_w=[]
    for z in wt:
        note=str(z.get('source_note','')).upper()
        if any(x in note for x in ['NIE UZYWAJ JAKO DCA3','NIE UŻYWAJ JAKO DCA3','REZERWOWA','ARCHIWAL']):
            continue
        active_w.append(z)
    d3v=min((z['from'] for z in active_w),default=None)
    d2v=((d1v+d3v)/2) if d1v is not None and d3v is not None else None
    blockers=[]; entry=[]
    if in_sup: entry.append('IN_SUPPLY')
    if fomo>=8: entry.append('FOMO_HARD_BLOCK')
    if fomo>=8:
        decision='CZEKAJ — FOMO'; reason='FOMO hard block >=8'
    elif in_sup:
        decision='CZEKAJ'; reason='Cena znajduje się w potwierdzonej strefie podaży'
    elif in_dem and trend>=2:
        decision='KUP DCA'; reason='Cena w potwierdzonej strefie popytu i trend nie jest złamany'
    elif global_score>=6 and trend>=3 and bool(d1.get('retest_10')) and fomo<=5:
        decision='KUP PO RETEŚCIE'; reason='Trend i retest potwierdzone, brak twardych blokad'
    elif global_score>=6 and trend>=4 and fomo<=4 and float(d1.get('volume_ratio_vs_20') or 0)>=1.0:
        decision='KUP TRENDOWO'; reason='Silny trend, wolumen i brak podaży'
    else:
        decision='CZEKAJ'; reason='Brak pełnego zestawu warunków wejścia'
    if decision.startswith('KUP') and entry:
        raise SystemExit(f'SAFETY FAIL {sym}: KUP przy blokadach {entry}')
    decisions.append({
        'symbol':sym,'technical_ready':True,'decision':decision,'reason':reason,'price':price,'trend_score_0_4':trend,'fomo_score_0_10':fomo,
        'zones':{'complete_7_of_7':True,'missing_timeframes':[],'timeframes':ZT,'zone_count':len(zz),'in_demand':in_dem,'in_supply':in_sup,'dca1':d1v,'dca2':d2v,'dca3':d3v},
        'blockers':blockers,'entry_blockers':entry
    })
    readiness.append({'symbol':sym,'target_scope':'PRODUCTION','price_data_ready':True,'rotation_data_ready':True,'zone_rows':len(zz),'zone_timeframes':','.join(ZT),'core_zone_missing':'','full_zone_missing':'','zones_core_ready':True,'zones_full_ready':True,'decision':decision,'decision_ready':True,'data_quality_score_0_100':100,'readiness_status':'PRODUCTION_DATA_READY'})

tech_payload={'date':datetime.now(timezone.utc).date().isoformat(),'generated_at_utc':NOW,'engine':'ALT_TECHNICAL_LAYER_v1.0','universe_source':'config/alt_universe.csv','data_source':'tactical_engine/TACTICAL_ENGINE.json — interwał 1D','asset_count':13,'rules':{'btc_is_market_regime_not_alt_decision_row':True,'closed_1d_only':True,'no_zone_guessing':True,'execution_connected':False},'assets':tech_assets}
(OUT/'ALT_TECHNICAL_LAYER.json').write_text(json.dumps(tech_payload,ensure_ascii=False,indent=2),encoding='utf-8')

dec_payload={'date':datetime.now(timezone.utc).date().isoformat(),'generated_at_utc':NOW,'engine':'ALT_DECISION_ENGINE_v1.0','universe':ALTS,'asset_count':13,'rules':{'execution_connected':False,'no_zone_guessing':True,'btc_is_market_regime_not_alt_decision_row':True,'fomo_hard_block_at_8':True,'in_supply_blocks_buy':True},'market_phase':market_phase,'rotation_score_0_10':global_score,'assets':decisions}
(OUT/'ALT_DECISION_ENGINE.json').write_text(json.dumps(dec_payload,ensure_ascii=False,indent=2),encoding='utf-8')

ready_payload={'date':datetime.now(timezone.utc).date().isoformat(),'engine':'ALT_ENGINE_READINESS_v1.0','rules':{'btc_is_market_regime_not_alt_row':True,'active_alts_exactly_13':True,'no_zone_guessing':True,'full_zone_timeframes':ZT,'data_pending_is_not_trade_signal':True},'summary':{'production_assets':13,'production_data_ready':13,'production_with_full_zones':13},'assets':readiness}
(OUT/'ALT_ENGINE_READINESS.json').write_text(json.dumps(ready_payload,ensure_ascii=False,indent=2),encoding='utf-8')
with (OUT/'ALT_ENGINE_READINESS.csv').open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=readiness[0].keys()); w.writeheader(); w.writerows(readiness)
with (OUT/'ALT_PRODUCTION_COCKPIT.csv').open('w',encoding='utf-8',newline='') as f:
    cols=['symbol','decision','data_quality_score_0_100','readiness_status','full_zone_missing']; w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows([{k:r[k] for k in cols} for r in readiness])

master_assets=[]
for r,d in zip(readiness,decisions):
    master_assets.append({'symbol':r['symbol'],'data_quality':100,'readiness_status':'PRODUCTION_DATA_READY','full_zones_ready':True,'zone_timeframes':','.join(ZT),'trend_score_0_4':d['trend_score_0_4'],'fomo_score_0_10':d['fomo_score_0_10'],'decision':d['decision'],'dca1':d['zones']['dca1'],'dca2':d['zones']['dca2'],'dca3':d['zones']['dca3'],'blockers':''})
master={'date':datetime.now(timezone.utc).date().isoformat(),'generated_at_utc':NOW,'engine':'ALT_ENGINE_MASTER_CHECKPOINT_v1.0','status':'CORE_ALT_ENGINE_READY_FOR_VALIDATION','production_universe':ALTS,'production_assets_count':13,'production_assets_ready':13,'full_zone_map':'91/91','core_modules_ready':'10/10','research_only':True,'not_strategy_frozen':True,'not_execution_connected':True,'market_phase':market_phase,'rules':{'V7_UNTOUCHED':True,'NO_ZONE_GUESSING':True,'DATA_PENDING_NOT_TRADE_SIGNAL':True,'LONG_AND_TACTICAL_SEPARATE':True,'BTC_IS_MARKET_REGIME':True},'assets':master_assets}
(OUT/'ALT_ENGINE_MASTER_CHECKPOINT.json').write_text(json.dumps(master,ensure_ascii=False,indent=2),encoding='utf-8')
with (OUT/'ALT_ENGINE_MASTER_COCKPIT.csv').open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=master_assets[0].keys()); w.writeheader(); w.writerows(master_assets)

print(json.dumps({'status_pl':'ZAKOŃCZONE POPRAWNIE','LONG':'13/13','STREFY':'91/91','TACTICAL_SOURCE':'14/14','execution_connected':False},ensure_ascii=False,indent=2))
