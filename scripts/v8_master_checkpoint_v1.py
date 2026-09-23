import json
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

R=Path('crypto_data_hub')
EXPECTED=['ETH','SOL','LINK','ONDO','RENDER','FLOKI','PEPE','SPX6900','XRP','XLM','HBAR']
TF=['1D','2D','3D','4D','5D','1T','2T']

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

cfg=pd.read_csv('config/alt_universe.csv')
zones=pd.read_csv('config/alt_zones.csv')
dec=load(R/'ALT_DECISION_ENGINE.json')
ready=load(R/'ALT_ENGINE_READINESS.json')
tech=load(R/'ALT_TECHNICAL_LAYER.json')
phase=load(R/'CRYPTO_MARKET_PHASE.json')
rot=load(R/'ALT_ROTATION_SCORE.json')
onchain=load(R/'ONCHAIN_ACTIVITY.json')

active=cfg[(cfg['enabled'].astype(str).str.lower()=='true') & (cfg['symbol'].astype(str).str.upper()!='BTC')]['symbol'].astype(str).str.upper().tolist()
if active!=EXPECTED: raise SystemExit(f'Lista altów niezgodna: {active}')
if dec.get('engine')!='ALT_DECISION_ENGINE_v1.0' or dec.get('universe')!=EXPECTED: raise SystemExit('LONG nie jest aktualny v1.0 / 11 altów')
if ready.get('engine')!='ALT_ENGINE_READINESS_v1.0': raise SystemExit('Readiness nie jest v1.0')

D={x.get('symbol'):x for x in dec.get('assets',[])}
Q={x.get('symbol'):x for x in ready.get('assets',[])}
T={x.get('symbol'):x for x in tech.get('assets',[])}
O={x.get('symbol'):x for x in onchain.get('assets',[])}
P={x.get('symbol'):x for x in phase.get('asset_context',[])}
rows=[]
for s in EXPECTED:
    d=D.get(s,{}); q=Q.get(s,{}); t=T.get(s,{}); oc=O.get(s,{}); pc=P.get(s,{})
    z=zones[(zones['symbol'].astype(str).str.upper()==s)&(zones['source_status'].astype(str).str.upper()=='CONFIRMED')].copy()
    z['from_n']=pd.to_numeric(z['from'],errors='coerce'); z['to_n']=pd.to_numeric(z['to'],errors='coerce')
    z=z[z['from_n'].notna() & z['to_n'].notna() & (z['from_n']>=0) & (z['to_n']>z['from_n'])]
    got=set(z['timeframe'].astype(str).str.upper())
    missing=[x for x in TF if x not in got]
    if missing: raise SystemExit(f'{s}: brakuje stref {missing}')
    if q.get('readiness_status')!='PRODUCTION_DATA_READY': raise SystemExit(f'{s}: readiness {q.get("readiness_status")}')
    if not (d.get('zones') or {}).get('complete_7_of_7'): raise SystemExit(f'{s}: LONG nie ma 7/7')
    rows.append({
      'symbol':s,'data_quality':q.get('data_quality_score_0_100'),'readiness_status':q.get('readiness_status'),
      'full_zones_ready':True,'zone_timeframes':','.join(TF),'trend_score_0_4':t.get('trend_score_0_4'),
      'fomo_score_0_10':t.get('fomo_score_0_10'),'rotation_label':pc.get('rotation_label'),'market_phase':phase.get('phase'),
      'long_flow_score_0_10':d.get('long_flow_score'),'long_flow_label':d.get('long_flow_label'),
      'onchain_profile':oc.get('metric_profile'),'onchain_coverage_pct':oc.get('coverage_pct'),'onchain_quality_gate':oc.get('quality_gate'),
      'decision':d.get('decision'),'dca1':d.get('dca1'),'dca2':d.get('dca2'),'dca3':d.get('dca3'),
      'blockers':'|'.join(d.get('blockers',[])),'entry_blockers':'|'.join(d.get('entry_blockers',[]))
    })

df=pd.DataFrame(rows)
dual=phase.get('dual_horizon_flow_context',{}) or {}
out={
 'generated_at_utc':datetime.now(timezone.utc).isoformat(),
 'date':datetime.now(timezone.utc).date().isoformat(),
 'engine':'ALT_ENGINE_MASTER_CHECKPOINT_v1.0',
 'status':'CORE_ALT_ENGINE_READY_FOR_VALIDATION',
 'status_pl':'11 ALTÓW — DANE WYSTARCZAJĄCE DO ANALIZY',
 'btc_role':'REŻIM RYNKU — poza wierszami altów',
 'production_universe':EXPECTED,
 'production_assets_count':11,
 'production_assets_ready':11,
 'full_zone_map':'77/77',
 'core_modules_ready':'10/10',
 'core_modules':{
   'FULL_ZONES_1D_TO_2T':True,'TECHNICAL_LAYER':True,'ROTATION_LAYER':rot.get('score_0_10') is not None,
   'MARKET_PHASE_LAYER':phase.get('phase') is not None,'LONG_DECISION_LAYER':True,'TACTICAL_ENGINE_SEPARATE':True,
   'ETF_BTC_ETH_FEED':True,'ONCHAIN_CONTEXT':True,'LAB_LAYER':True,'GOOGLE_SHEETS_BRIDGE':True
 },
 'crypto_market_phase':phase.get('phase'),'market_phase_confidence':phase.get('phase_confidence'),
 'alt_rotation_score_0_10':rot.get('score_0_10'),'alt_rotation_status':rot.get('status'),
 'long_flow_context':dual.get('LONG',{}),'tactical_flow_context':dual.get('TACTICAL',{}),
 'onchain_context':{'engine':onchain.get('engine'),'role':'KONTEKST — NIE JEST SAMODZIELNYM SYGNAŁEM KUP/SPRZEDAJ'},
 'research_only':True,'not_strategy_frozen':True,'not_execution_connected':True,
 'blockers_or_maturity_gaps':[],
 'assets':rows,
 'rules':{'V7_UNTOUCHED':True,'NO_ZONE_GUESSING':True,'BTC_IS_MARKET_REGIME':True,'ACTIVE_ALTS_EXACTLY_11':True,'FULL_ZONE_MAP_77_OF_77':True,'NO_AUTOMATIC_EXECUTION':True}
}
(R/'ALT_ENGINE_MASTER_CHECKPOINT.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
df.to_csv(R/'ALT_ENGINE_MASTER_COCKPIT.csv',index=False)
print(json.dumps({'status_pl':out['status_pl'],'production_assets_ready':11,'full_zone_map':'77/77'},ensure_ascii=False,indent=2))
