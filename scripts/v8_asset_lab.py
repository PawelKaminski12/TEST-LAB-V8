import json, math
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import yfinance as yf

ROOT=Path('lab'); ROOT.mkdir(exist_ok=True)
CFG=Path('config/lab_assets.csv')
PHASE=Path('crypto_data_hub/CRYPTO_MARKET_PHASE.json')
ONC=Path('crypto_data_hub/ONCHAIN_ACTIVITY.json')
MASTER=Path('crypto_data_hub/ALT_ENGINE_MASTER_CHECKPOINT.json')
NOW=datetime.now(timezone.utc)


def sf(x):
    try:
        v=float(x); return v if math.isfinite(v) else None
    except Exception:return None

def ema(s,n): return s.ewm(span=n,adjust=False,min_periods=n).mean()
def rsi(c,n=14):
    d=c.diff(); up=d.clip(lower=0); dn=-d.clip(upper=0)
    au=up.ewm(alpha=1/n,adjust=False,min_periods=n).mean(); ad=dn.ewm(alpha=1/n,adjust=False,min_periods=n).mean()
    rs=au/ad.replace(0,np.nan); out=100-(100/(1+rs)); return out.where(~((au==0)&(ad==0)),50)
def mfi(df,n=14):
    tp=(df.High+df.Low+df.Close)/3; raw=tp*df.Volume; d=tp.diff()
    p=raw.where(d>0,0).rolling(n,min_periods=n).sum(); q=raw.where(d<0,0).rolling(n,min_periods=n).sum()
    out=100-(100/(1+p/q.replace(0,np.nan)))
    out=out.mask((p==0)&(q==0),50).mask((p>0)&(q==0),100).mask((p==0)&(q>0),0)
    return out.clip(0,100)

def tech(df):
    if len(df)<220:return {'status':'INSUFFICIENT_HISTORY'}
    x=df.copy(); x['ema20']=ema(x.Close,20); x['ema50']=ema(x.Close,50); x['ema200']=ema(x.Close,200)
    x['macd']=ema(x.Close,12)-ema(x.Close,26); x['signal']=ema(x.macd,9); x['hist']=x.macd-x.signal; x['rsi']=rsi(x.Close); x['mfi']=mfi(x)
    r=x.iloc[-1]; close=sf(r.Close)
    trend=sum([close>r.ema20,close>r.ema50,r.ema20>r.ema50,close>r.ema200])
    ret5=(close/x.Close.iloc[-6]-1)*100 if len(x)>=6 else None; ret20=(close/x.Close.iloc[-21]-1)*100 if len(x)>=21 else None
    fomo=0
    rv=sf(r.rsi); mv=sf(r.mfi)
    if rv is not None: fomo += 4 if rv>=80 else 3 if rv>=75 else 2 if rv>=70 else 0
    if ret5 is not None: fomo += 3 if ret5>=15 else 2 if ret5>=10 else 1 if ret5>=6 else 0
    return {'status':'OK','price':close,'trend_0_4':int(trend),'rsi14':rv,'mfi14':mv,'macd_hist':sf(r['hist']),'ret5_pct':ret5,'ret20_pct':ret20,'fomo_0_10':min(10,int(fomo))}

def load_yf(sym,period='2y',interval='1d'):
    try:
        d=yf.download(sym,period=period,interval=interval,auto_adjust=True,progress=False,threads=False)
        if isinstance(d.columns,pd.MultiIndex): d.columns=[c[0] for c in d.columns]
        d=d[['Open','High','Low','Close','Volume']].dropna().copy(); return d,'OK'
    except Exception as e:return pd.DataFrame(),'ERROR_'+type(e).__name__

def stock_fundamentals(sym):
    out={'status':'NO_DATA'}
    try:
        t=yf.Ticker(sym); info=t.info or {}
        out={'status':'OK','market_cap':sf(info.get('marketCap')),'trailing_pe':sf(info.get('trailingPE')),'forward_pe':sf(info.get('forwardPE')),'price_to_sales':sf(info.get('priceToSalesTrailing12Months')),'revenue_growth':sf(info.get('revenueGrowth')),'earnings_growth':sf(info.get('earningsGrowth')),'debt_to_equity':sf(info.get('debtToEquity')),'free_cashflow':sf(info.get('freeCashflow'))}
    except Exception as e: out={'status':'ERROR_'+type(e).__name__}
    return out

def checkpoint(asset_type,added):
    if not added:return 'D0'
    try: days=(NOW-datetime.fromisoformat(str(added).replace('Z','+00:00'))).total_seconds()/86400
    except Exception:return 'D0'
    marks=[(30,'D30'),(7,'D7')]
    if asset_type in ('CRYPTO','MEME'): marks=[(30,'D30'),(7,'D7'),(3,'D3'),(1,'D1')]
    for n,l in marks:
        if days>=n:return l
    return 'D0'

def main():
    cfg=pd.read_csv(CFG); cfg=cfg[cfg.enabled.astype(str).str.lower().eq('true')].copy()
    phase=json.loads(PHASE.read_text()) if PHASE.exists() else {}; onc=json.loads(ONC.read_text()) if ONC.exists() else {}; master=json.loads(MASTER.read_text()) if MASTER.exists() else {}
    onmap={a.get('symbol'):a for a in onc.get('assets',[])}; mmap={a.get('symbol'):a for a in master.get('assets',[])}
    reports=[]; rows=[]
    for _,r in cfg.iterrows():
        sym=str(r.symbol).upper().strip(); src=str(r.source_symbol).strip(); typ=str(r.asset_type).upper().strip(); mode=str(r.mode).upper().strip()
        if typ=='AUTO': typ='CRYPTO' if src.upper().endswith('-USD') else 'STOCK'
        daily,ds=load_yf(src)
        td=tech(daily) if ds=='OK' else {'status':ds}
        fundamentals=stock_fundamentals(src) if typ=='STOCK' else {'status':'NOT_APPLICABLE'}
        oc=onmap.get(sym,{}) if typ in ('CRYPTO','MEME') else {}
        mm=mmap.get(sym,{}) if typ in ('CRYPTO','MEME') else {}
        cp=checkpoint(typ,r.get('added_at_utc'))
        quality=0
        quality+=40 if td.get('status')=='OK' else 0
        quality+=25 if typ=='STOCK' and fundamentals.get('status')=='OK' else 0
        quality+=25 if typ in ('CRYPTO','MEME') and oc.get('quality_gate')=='TRUSTED' else 0
        quality+=10 if typ in ('CRYPTO','MEME') and phase.get('phase') else 0
        label='DATA_READY' if quality>=60 else 'PARTIAL' if quality>0 else 'NO_DATA'
        report={'generated_at_utc':NOW.isoformat(),'symbol':sym,'source_symbol':src,'asset_type':typ,'mode':mode,'checkpoint':cp,'data_quality_0_100':quality,'data_status':label,'technical_1D':td,'stock_fundamentals':fundamentals,'crypto_market_context':{'phase':phase.get('phase'),'confidence':phase.get('phase_confidence'),'rotation_score':phase.get('alt_rotation_score_0_10')} if typ in ('CRYPTO','MEME') else None,'onchain_context':{'quality_gate':oc.get('quality_gate'),'coverage_pct':oc.get('coverage_pct'),'long_score':oc.get('long_onchain_score_0_10'),'tactical_score':oc.get('tactical_onchain_score_0_10')} if typ in ('CRYPTO','MEME') else None,'existing_engine_context':{'decision':mm.get('decision'),'long_flow':mm.get('long_flow_score_0_10'),'tactical_flow':mm.get('tactical_flow_score_0_5')} if mm else None,'rules':{'FAST_is_current_snapshot':True,'DEEP_crypto_checkpoints':['D0','D1','D3','D7','D30'],'DEEP_stock_checkpoints':['D0','D7','D30'],'never_auto_add_to_portfolio':True,'not_trade_execution':True}}
        reports.append(report)
        rows.append({'generated_at_utc':NOW.isoformat(),'symbol':sym,'asset_type':typ,'mode':mode,'checkpoint':cp,'price':td.get('price'),'trend_0_4':td.get('trend_0_4'),'rsi14':td.get('rsi14'),'mfi14':td.get('mfi14'),'macd_hist':td.get('macd_hist'),'fomo_0_10':td.get('fomo_0_10'),'quality_0_100':quality,'status':label,'onchain_long':oc.get('long_onchain_score_0_10'),'onchain_tactical':oc.get('tactical_onchain_score_0_10'),'engine_decision':mm.get('decision')})
    payload={'generated_at_utc':NOW.isoformat(),'engine':'V8_ASSET_LAB_v0.1','active_assets':len(reports),'reports':reports,'purpose':'FAST current analysis plus DEEP observation; research only'}
    (ROOT/'LAB_REPORT.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False))
    cur=pd.DataFrame(rows); cur.to_csv(ROOT/'LAB_COCKPIT.csv',index=False)
    hp=ROOT/'LAB_HISTORY.csv'; hist=cur
    if hp.exists() and not cur.empty:
        old=pd.read_csv(hp); hist=pd.concat([old,cur],ignore_index=True,sort=False).drop_duplicates(['generated_at_utc','symbol'],keep='last')
    hist.to_csv(hp,index=False)
    status={'generated_at_utc':NOW.isoformat(),'engine':'V8_ASSET_LAB_v0.1','active_assets':len(reports),'fast_mode_ready':True,'deep_mode_ready':True,'crypto_checkpoints':['D0','D1','D3','D7','D30'],'stock_checkpoints':['D0','D7','D30'],'portfolio_connection':False,'execution_connection':False}
    (ROOT/'LAB_STATUS.json').write_text(json.dumps(status,indent=2))
    print(json.dumps(status,indent=2))
if __name__=='__main__': main()
