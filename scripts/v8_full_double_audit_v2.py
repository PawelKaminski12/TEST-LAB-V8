#!/usr/bin/env python3
import argparse,csv,json,math
from pathlib import Path
from datetime import datetime,timezone

P=Path('.')
ALTS=['ETH','SOL','LINK','ONDO','RENDER','FLOKI','PEPE','SPX6900','XRP','XLM','HBAR']
ALL=['BTC']+ALTS
ZT=['1D','2D','3D','4D','5D','1T','2T']
TT=['1H','4H','1D']
a=argparse.ArgumentParser(); a.add_argument('--pass-number',type=int,required=True); N=a.parse_args().pass_number
C=[]
def ck(n,v,d=''): C.append({'kontrola':n,'ok':bool(v),'szczegol':str(d)})
def J(p):
 q=P/p; ck('PLIK '+p,q.exists());
 return json.loads(q.read_text(encoding='utf-8')) if q.exists() else {}
def rows(p):
 q=P/p; ck('PLIK '+p,q.exists());
 if not q.exists(): return []
 with q.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def fin(x):
 try:return math.isfinite(float(x))
 except:return False

# Uniwersum
u=rows('config/alt_universe.csv'); m={r['symbol'].upper():r for r in u}; act=[r['symbol'].upper() for r in u if r['enabled'].lower()=='true']
ck('AKTYWNE BTC + 11 ALTÓW',act==ALL,act); ck('BTC = REŻIM RYNKU',m.get('BTC',{}).get('role')=='MARKET_REGIME'); ck('AAVE = ARCHIWUM',m.get('AAVE',{}).get('enabled')=='false' and m.get('AAVE',{}).get('target_scope')=='ARCHIVE')

# Strefy — zero jest dozwolone jako dolna granica historycznej strefy widocznej na wykresie; wartości ujemne nie są.
z=rows('config/alt_zones.csv'); cov={s:set() for s in ALTS}; bad=[]
for r in z:
 s=r.get('symbol','').upper(); tf=r.get('timeframe','').upper()
 if s not in ALTS or tf not in ZT: continue
 try: lo=float(r['from']); hi=float(r['to']); ok=math.isfinite(lo) and math.isfinite(hi) and lo>=0 and hi>lo and r.get('source_status','').upper()=='CONFIRMED'
 except: ok=False
 if ok: cov[s].add(tf)
 else: bad.append((s,tf,r.get('from'),r.get('to')))
for s in ALTS: ck('STREFY '+s+' 7/7',cov[s]==set(ZT),sorted(cov[s]))
ck('STREFY — ZAKRESY LICZBOWE POPRAWNE',not bad,bad[:10])
za=J('audit/V8_ZONE_FINAL_77_OF_77.json'); ck('AUDYT STREF 77/77',za.get('ready_points')==77 and za.get('total_points')==77 and za.get('assets_complete')==11 and za.get('percent')==100.0)

# LONG
L=J('crypto_data_hub/ALT_DECISION_ENGINE.json'); ck('LONG v1.0',L.get('engine')=='ALT_DECISION_ENGINE_v1.0'); ck('LONG = 11 ALTÓW',L.get('asset_count')==11 and L.get('universe')==ALTS,L.get('universe')); ck('LONG — BRAK AUTOMATYCZNEJ REALIZACJI',(L.get('rules') or {}).get('execution_connected') is False); ck('LONG — NIE ZGADUJE STREF',(L.get('rules') or {}).get('no_zone_guessing') is True)
LM={x.get('symbol'):x for x in L.get('assets',[])}
for s in ALTS:
 x=LM.get(s,{}); zz=x.get('zones') or {}; ck('LONG '+s+' TECHNIKA',x.get('technical_ready') is True); ck('LONG '+s+' STREFY 7/7',zz.get('complete_7_of_7') is True and zz.get('missing_timeframes')==[],zz.get('missing_timeframes'))
 if str(x.get('decision','')).startswith('KUP'): ck('LONG '+s+' KUP BEZ BLOKAD',not x.get('blockers') and not x.get('entry_blockers'),(x.get('blockers'),x.get('entry_blockers')))

# Readiness + master
R=J('crypto_data_hub/ALT_ENGINE_READINESS.json'); RM={x.get('symbol'):x for x in R.get('assets',[])}
ck('GOTOWOŚĆ v1.0',R.get('engine')=='ALT_ENGINE_READINESS_v1.0'); ck('GOTOWOŚĆ 11/11',R.get('summary',{}).get('production_data_ready')==11 and R.get('summary',{}).get('production_with_full_zones')==11,R.get('summary')); ck('GOTOWOŚĆ BEZ AAVE/BTC W WIERSZACH',set(RM)==set(ALTS),sorted(RM))
for s in ALTS: ck('GOTOWOŚĆ '+s,RM.get(s,{}).get('readiness_status')=='PRODUCTION_DATA_READY' and RM.get(s,{}).get('zones_full_ready') is True)
M=J('crypto_data_hub/ALT_ENGINE_MASTER_CHECKPOINT.json'); ck('MASTER v1.0',M.get('engine')=='ALT_ENGINE_MASTER_CHECKPOINT_v1.0'); ck('MASTER 11/11',M.get('production_assets_count')==11 and M.get('production_assets_ready')==11); ck('MASTER 77/77',M.get('full_zone_map')=='77/77'); ck('MASTER BEZ AUTOMATYCZNEJ REALIZACJI',M.get('not_execution_connected') is True)

# Tactical
T=J('tactical_engine/TACTICAL_ENGINE.json'); ck('TACTICAL v1.0',T.get('engine')=='V8_TACTICAL_ENGINE_v1.0'); ck('TACTICAL BTC + 11',T.get('asset_count')==12 and T.get('universe')==ALL,T.get('universe')); ck('TACTICAL BEZ SPÓŁEK',T.get('stocks_included') is False); ck('TACTICAL BEZ AUTOMATYCZNEJ REALIZACJI',T.get('not_execution_connected') is True)
TM={x.get('symbol'):x for x in T.get('assets',[])}
for s in ALL:
 x=TM.get(s,{}); ck('TACTICAL '+s+' QA',x.get('qa')=='PASS'); t=x.get('timeframes') or {}; ck('TACTICAL '+s+' 1H/4H/1D',all(k in t for k in TT),list(t))
 for tf in TT:
  y=t.get(tf,{}); ck('TACTICAL '+s+' '+tf+' ZAMKNIĘTA ŚWIECA',y.get('closed_bar_only') is True); ck('TACTICAL '+s+' '+tf+' ŚWIEŻE DANE',y.get('stale') is False)
  ck('TACTICAL '+s+' '+tf+' RSI',fin(y.get('rsi14')) and 0<=float(y.get('rsi14'))<=100,y.get('rsi14')); ck('TACTICAL '+s+' '+tf+' MFI',fin(y.get('mfi14')) and 0<=float(y.get('mfi14'))<=100,y.get('mfi14')); ck('TACTICAL '+s+' '+tf+' FOMO',fin(y.get('fomo_score_0_10')) and 0<=float(y.get('fomo_score_0_10'))<=10,y.get('fomo_score_0_10'))
TR=J('tactical_engine/TACTICAL_READINESS.json'); ck('TACTICAL GOTOWOŚĆ 12/12',TR.get('asset_count')==12 and TR.get('all_assets_ready') is True); ck('TRADINGVIEW ŚWIADOMIE ODŁOŻONE',TR.get('tradingview_connected') is False); ck('EXECUTION OFF',TR.get('execution_connected') is False)

# ETF
E=J('institutional_data_hub/ETF_BTC_ETH_STATUS.json'); EA=E.get('assets') or {}; ck('ETF BTC + ETH',set(EA)=={'BTC','ETH'},list(EA))
for s in ['BTC','ETH']:
 rr=EA.get(s,{}).get('rules') or {}; ck('ETF '+s+' DZIEŃ NIEFINALNY',rr.get('today_never_treated_as_final_same_day') is True); ck('ETF '+s+' TREND BEZ DZISIAJ',rr.get('closed_trend_excludes_today') is True); ck('ETF '+s+' ZERO NIE = FINALNE ZERO',rr.get('zero_today_does_not_mean_final_zero') is True)
EC=J('institutional_data_hub/ETF_BTC_ETH_CONFIRMATION.json'); ck('ETF POTWIERDZENIE 2/2',set((EC.get('assets') or {}).keys())=={'BTC','ETH'})

# LAB
B=J('lab/LAB_STATUS.json'); ck('LAB SZYBKA ANALIZA',B.get('fast_mode_ready') is True and B.get('fast_multitimeframe_enabled') is True); ck('LAB GŁĘBOKA OBSERWACJA',B.get('deep_mode_ready') is True and B.get('deep_comparison_enabled') is True); ck('LAB PO POLSKU',B.get('polish_user_language') is True); ck('LAB BEZ REALIZACJI',B.get('execution_connection') is False and B.get('portfolio_connection') is False); ck('LAB CHECKPOINTY KRYPTO',B.get('crypto_checkpoints')==['D0','D1','D3','D7','D30']); ck('LAB CHECKPOINTY SPÓŁKI',B.get('stock_checkpoints')==['D0','D7','D30'])

# On-chain, walidacja, alarmy, Market Reader, Google Sheets i pliki poboczne
O=J('crypto_data_hub/ONCHAIN_ACTIVITY.json'); ck('ONCHAIN DZIAŁA',str(O.get('engine','')).startswith('ONCHAIN_ACTIVITY_') and len(O.get('assets') or [])>0)
files=['tactical_validation/TACTICAL_THRESHOLD_LAB.json','tactical_validation/TACTICAL_VALIDATION.json','tactical_validation/TACTICAL_VALIDATION_SUMMARY.csv','tactical_engine/TACTICAL_MACD_EXTREMES.csv','tactical_engine/TACTICAL_EXTREME_CONFLUENCE.csv','market_reader/TACTICAL_CONFLUENCE.csv','google_sheets/DUAL_PANEL.csv','google_sheets/DUAL_ENGINE_MACHINE_ROOM.csv','google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL.txt','lab/LAB_REPORT.json','lab/LAB_DEEP_REPORT.json','lab/LAB_CHECKPOINTS.csv','institutional_data_hub/ETF_BTC_ETH_HISTORY.csv','institutional_data_hub/ETF_PRICE_DIVERGENCE_LATEST.md']
for f in files: ck('MODUŁ '+f,(P/f).exists())
bridge=(P/'google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL.txt').read_text(encoding='utf-8'); ck('MOST SHEETS — LONG','ALT_ENGINE_MASTER_CHECKPOINT.json' in bridge); ck('MOST SHEETS — TACTICAL','TACTICAL_ENGINE.json' in bridge and 'TACTICAL_READINESS.json' in bridge); ck('MOST SHEETS — ETF','ETF_BTC_ETH_STATUS.json' in bridge and 'ETF_BTC_ETH_HISTORY.csv' in bridge); ck('MOST SHEETS — BEZ BROKERA','no broker execution' in bridge.lower())
F=(P/'audit/V8_FINAL_READINESS_LATEST.md').read_text(encoding='utf-8'); ck('STATUS PROJEKTU 100%','Gotowość całego projektu: 100%' in F); ck('TRADINGVIEW NIE WLICZONY','TradingView' in F and 'później' in F)

bad=[x for x in C if not x['ok']]; out={'generated_at_utc':datetime.now(timezone.utc).isoformat(),'test':f'{N}/2','kontrole':len(C),'poprawne':len(C)-len(bad),'bledy':len(bad),'status_pl':'ZAKOŃCZONE POPRAWNIE' if not bad else 'WYKRYTO ELEMENTY DO POPRAWY','problemy':bad,'szczegoly':C}
Path('audit').mkdir(exist_ok=True); Path(f'audit/V8_FULL_AUDIT_PASS_{N}.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8'); Path(f'audit/V8_FULL_AUDIT_PASS_{N}.md').write_text(f"# V8 — PEŁNY TEST {N}/2\n\n**{out['status_pl']}**\n\nKontrole: **{out['poprawne']}/{out['kontrole']}** poprawne.\n"+('' if not bad else '\n'.join('- '+x['kontrola']+': '+x['szczegol'] for x in bad))+'\n',encoding='utf-8')
print(json.dumps({'test':out['test'],'status_pl':out['status_pl'],'kontrole':out['kontrole'],'poprawne':out['poprawne'],'bledy':out['bledy'],'problemy':bad},ensure_ascii=False,indent=2))
if bad: raise SystemExit(1)
