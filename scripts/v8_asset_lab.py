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

def pct(a,b):
    a=sf(a); b=sf(b)
    if a is None or b in (None,0): return None
    return (a/b-1)*100

def delta(a,b):
    a=sf(a); b=sf(b)
    return None if a is None or b is None else a-b

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

def index_age_hours(df):
    if df.empty:return None
    try:
        ts=pd.Timestamp(df.index[-1])
        if ts.tzinfo is None: ts=ts.tz_localize('UTC')
        else: ts=ts.tz_convert('UTC')
        return max(0.0,(pd.Timestamp(NOW)-ts).total_seconds()/3600)
    except Exception:return None

def tech(df,min_rows=120):
    if len(df)<min_rows:return {'status':'INSUFFICIENT_HISTORY','rows':int(len(df)),'age_hours':index_age_hours(df)}
    x=df.copy(); x['ema20']=ema(x.Close,20); x['ema50']=ema(x.Close,50); x['ema200']=ema(x.Close,200)
    x['macd']=ema(x.Close,12)-ema(x.Close,26); x['signal']=ema(x.macd,9); x['hist']=x.macd-x.signal; x['rsi']=rsi(x.Close); x['mfi']=mfi(x)
    r=x.iloc[-1]; close=sf(r.Close)
    vals=[close>r.ema20,close>r.ema50,r.ema20>r.ema50,close>r.ema200]
    trend=sum(bool(v) for v in vals if pd.notna(v))
    ret5=(close/x.Close.iloc[-6]-1)*100 if len(x)>=6 else None; ret20=(close/x.Close.iloc[-21]-1)*100 if len(x)>=21 else None
    fomo=0; rv=sf(r.rsi); mv=sf(r.mfi)
    if rv is not None: fomo += 4 if rv>=80 else 3 if rv>=75 else 2 if rv>=70 else 0
    if mv is not None: fomo += 2 if mv>=90 else 1 if mv>=80 else 0
    if ret5 is not None: fomo += 3 if ret5>=15 else 2 if ret5>=10 else 1 if ret5>=6 else 0
    return {'status':'OK','rows':int(len(x)),'age_hours':index_age_hours(x),'price':close,'trend_0_4':int(trend),'rsi14':rv,'mfi14':mv,'macd_hist':sf(r['hist']),'ret5_pct':ret5,'ret20_pct':ret20,'fomo_0_10':min(10,int(fomo))}

def load_yf(sym,period='2y',interval='1d'):
    try:
        d=yf.download(sym,period=period,interval=interval,auto_adjust=True,progress=False,threads=False,prepost=False)
        if isinstance(d.columns,pd.MultiIndex): d.columns=[c[0] for c in d.columns]
        d=d[['Open','High','Low','Close','Volume']].dropna().copy(); return d,'OK'
    except Exception as e:return pd.DataFrame(),'ERROR_'+type(e).__name__

def resample_4h(hourly):
    if hourly.empty:return hourly
    try:
        return hourly.resample('4h').agg({'Open':'first','High':'max','Low':'min','Close':'last','Volume':'sum'}).dropna()
    except Exception:return pd.DataFrame()

def stock_fundamentals(sym):
    try:
        info=yf.Ticker(sym).info or {}
        return {'status':'OK','market_cap':sf(info.get('marketCap')),'trailing_pe':sf(info.get('trailingPE')),'forward_pe':sf(info.get('forwardPE')),'price_to_sales':sf(info.get('priceToSalesTrailing12Months')),'revenue_growth':sf(info.get('revenueGrowth')),'earnings_growth':sf(info.get('earningsGrowth')),'debt_to_equity':sf(info.get('debtToEquity')),'free_cashflow':sf(info.get('freeCashflow'))}
    except Exception as e:return {'status':'ERROR_'+type(e).__name__}

def checkpoint(asset_type,added):
    if not added:return 'D0'
    try: days=(NOW-datetime.fromisoformat(str(added).replace('Z','+00:00'))).total_seconds()/86400
    except Exception:return 'D0'
    marks=[(30,'D30'),(7,'D7')]
    if asset_type in ('CRYPTO','MEME'): marks=[(30,'D30'),(7,'D7'),(3,'D3'),(1,'D1')]
    for n,l in marks:
        if days>=n:return l
    return 'D0'

def read_history(path):
    if not path.exists() or path.stat().st_size==0:return pd.DataFrame()
    try:return pd.read_csv(path)
    except (pd.errors.EmptyDataError,pd.errors.ParserError):return pd.DataFrame()

def deep_compare(history,sym,current):
    if history.empty or 'symbol' not in history.columns:return {'status':'BASELINE_CREATED','baseline_checkpoint':'D0'}
    z=history[history.symbol.astype(str).str.upper().eq(sym)].copy()
    if z.empty:return {'status':'BASELINE_CREATED','baseline_checkpoint':'D0'}
    if 'generated_at_utc' in z.columns:
        z['generated_at_utc']=pd.to_datetime(z['generated_at_utc'],utc=True,errors='coerce'); z=z.sort_values('generated_at_utc')
    b=z.iloc[0]; btime=b.get('generated_at_utc'); elapsed=None
    try: elapsed=(pd.Timestamp(NOW)-pd.Timestamp(btime)).total_seconds()/86400
    except Exception: pass
    return {'status':'TRACKING','baseline_utc':str(btime),'elapsed_days':elapsed,'price_change_pct':pct(current.get('price'),b.get('price')),'trend_change':delta(current.get('trend_0_4'),b.get('trend_0_4')),'rsi_change':delta(current.get('rsi14'),b.get('rsi14')),'mfi_change':delta(current.get('mfi14'),b.get('mfi14')),'fomo_change':delta(current.get('fomo_0_10'),b.get('fomo_0_10')),'onchain_long_change':delta(current.get('onchain_long'),b.get('onchain_long')),'onchain_tactical_change':delta(current.get('onchain_tactical'),b.get('onchain_tactical')),'baseline_engine_decision':None if pd.isna(b.get('engine_decision')) else str(b.get('engine_decision')),'current_engine_decision':current.get('engine_decision')}

def fast_score(t1,t4,td,typ,oc,phase,mm):
    if td.get('status')!='OK': return {'score_0_10':None,'label':'INSUFFICIENT_DATA','risk_flags':['NO_DAILY_DATA']}
    score=0.0; flags=[]
    score += (td.get('trend_0_4') or 0)*0.9
    if t4.get('status')=='OK': score += (t4.get('trend_0_4') or 0)*0.55
    if t1.get('status')=='OK': score += (t1.get('trend_0_4') or 0)*0.25
    if sf(td.get('macd_hist')) is not None and td.get('macd_hist')>0: score+=0.8
    if sf(t4.get('macd_hist')) is not None and t4.get('macd_hist')>0: score+=0.7
    if sf(t1.get('macd_hist')) is not None and t1.get('macd_hist')>0: score+=0.4
    r4=sf(t4.get('rsi14')); m4=sf(t4.get('mfi14'))
    if r4 is not None and 45<=r4<=70: score+=0.5
    if m4 is not None and 40<=m4<=75: score+=0.4
    f=max([v for v in [td.get('fomo_0_10'),t4.get('fomo_0_10'),t1.get('fomo_0_10')] if v is not None] or [0])
    if f>=8: score-=2.0; flags.append('HIGH_FOMO')
    elif f>=6: score-=1.0; flags.append('ELEVATED_FOMO')
    for name,t in [('1H',t1),('4H',t4),('1D',td)]:
        rv=sf(t.get('rsi14')); mv=sf(t.get('mfi14'))
        if rv is not None and rv>=75: flags.append(name+'_RSI_OVERHEAT')
        if mv is not None and mv>=85: flags.append(name+'_MFI_OVERHEAT')
    if typ in ('CRYPTO','MEME'):
        if phase.get('phase') in ('ALT_ROTATION_CANDIDATE','ALT_ROTATION_CONFIRMED'): score+=0.4
        if oc.get('quality_gate')=='TRUSTED':
            os=sf(oc.get('tactical_onchain_score_0_10'))
            if os is not None: score += (os-5)*0.08
        if mm.get('decision') in ('NIE DOKŁADAJ','NO_TRADE'): flags.append('EXISTING_ENGINE_BLOCK')
    score=max(0.0,min(10.0,score))
    if 'HIGH_FOMO' in flags: label='HIGH_FOMO_RISK'
    elif score>=8: label='STRONG_CONTEXT'
    elif score>=6.5: label='POSITIVE_CONTEXT'
    elif score>=4.5: label='MIXED_CONTEXT'
    else: label='WEAK_CONTEXT'
    return {'score_0_10':round(score,2),'label':label,'risk_flags':sorted(set(flags)),'role':'research context only; never standalone buy/sell signal'}

def main():
    cfg=pd.read_csv(CFG); cfg=cfg[cfg.enabled.astype(str).str.lower().eq('true')].copy()
    phase=json.loads(PHASE.read_text()) if PHASE.exists() else {}; onc=json.loads(ONC.read_text()) if ONC.exists() else {}; master=json.loads(MASTER.read_text()) if MASTER.exists() else {}
    onmap={a.get('symbol'):a for a in onc.get('assets',[])}; mmap={a.get('symbol'):a for a in master.get('assets',[])}
    hp=ROOT/'LAB_HISTORY.csv'; prior=read_history(hp)
    reports=[]; rows=[]
    for _,r in cfg.iterrows():
        sym=str(r['symbol']).upper().strip(); src=str(r['source_symbol']).strip(); typ=str(r['asset_type']).upper().strip(); mode=str(r['mode']).upper().strip()
        if typ=='AUTO': typ='CRYPTO' if src.upper().endswith('-USD') else 'STOCK'
        daily,ds=load_yf(src,'2y','1d'); hourly,hs=load_yf(src,'60d','1h'); four=resample_4h(hourly) if hs=='OK' else pd.DataFrame()
        td=tech(daily,120) if ds=='OK' else {'status':ds}; t1=tech(hourly,120) if hs=='OK' else {'status':hs}; t4=tech(four,120) if not four.empty else {'status':'NO_4H_DATA','rows':0}
        fundamentals=stock_fundamentals(src) if typ=='STOCK' else {'status':'NOT_APPLICABLE'}
        oc=onmap.get(sym,{}) if typ in ('CRYPTO','MEME') else {}; mm=mmap.get(sym,{}) if typ in ('CRYPTO','MEME') else {}
        cp=checkpoint(typ,r.get('added_at_utc'))
        mtf_ready=sum(t.get('status')=='OK' for t in (t1,t4,td))
        quality=(20 if td.get('status')=='OK' else 0)+(20 if t4.get('status')=='OK' else 0)+(15 if t1.get('status')=='OK' else 0)+(20 if typ=='STOCK' and fundamentals.get('status')=='OK' else 0)+(15 if typ in ('CRYPTO','MEME') and oc.get('quality_gate')=='TRUSTED' else 0)+(10 if typ in ('CRYPTO','MEME') and phase.get('phase') else 0)
        label='DATA_READY' if quality>=65 and mtf_ready>=2 else 'PARTIAL' if quality>0 else 'NO_DATA'
        fast=fast_score(t1,t4,td,typ,oc,phase,mm)
        row={'generated_at_utc':NOW.isoformat(),'symbol':sym,'asset_type':typ,'mode':mode,'checkpoint':cp,'price':td.get('price'),'trend_0_4':td.get('trend_0_4'),'rsi14':td.get('rsi14'),'mfi14':td.get('mfi14'),'macd_hist':td.get('macd_hist'),'fomo_0_10':max([v for v in [td.get('fomo_0_10'),t4.get('fomo_0_10'),t1.get('fomo_0_10')] if v is not None] or [None]),'quality_0_100':quality,'status':label,'mtf_ready_0_3':mtf_ready,'fast_score_0_10':fast.get('score_0_10'),'fast_label':fast.get('label'),'onchain_long':oc.get('long_onchain_score_0_10'),'onchain_tactical':oc.get('tactical_onchain_score_0_10'),'engine_decision':mm.get('decision')}
        deep=deep_compare(prior,sym,row)
        inputs=phase.get('inputs') or {}
        market_ctx={'phase':phase.get('phase'),'phase_score_0_10':phase.get('phase_score_0_10'),'confidence':phase.get('phase_confidence'),'rotation_score_0_10':phase.get('rotation_score_0_10'),'rotation_status':phase.get('rotation_status'),'btc_dominance_pct':inputs.get('btc_dominance_pct'),'eth_dominance_pct':inputs.get('eth_dominance_pct'),'eth_btc_5d_pct':inputs.get('eth_btc_5d_pct'),'eth_btc_20d_pct':inputs.get('eth_btc_20d_pct'),'btc_etf_5d_usdm':inputs.get('btc_etf_5d_usdm'),'btc_etf_20d_usdm':inputs.get('btc_etf_20d_usdm'),'eth_etf_5d_usdm':inputs.get('eth_etf_5d_usdm'),'eth_etf_20d_usdm':inputs.get('eth_etf_20d_usdm'),'stablecoin_7d_pct':inputs.get('stablecoin_7d_pct'),'stablecoin_30d_pct':inputs.get('stablecoin_30d_pct')} if typ in ('CRYPTO','MEME') else None
        report={'generated_at_utc':NOW.isoformat(),'symbol':sym,'source_symbol':src,'asset_type':typ,'mode':mode,'checkpoint':cp,'data_quality_0_100':quality,'data_status':label,'mtf_ready_0_3':mtf_ready,'fast_analysis':fast,'technical':{'1H':t1,'4H':t4,'1D':td,'bar_policy':'LATEST_AVAILABLE_MAY_BE_OPEN','4H_source':'synthetic resample from 1H'},'technical_1D':td,'stock_fundamentals':fundamentals,'crypto_market_context':market_ctx,'onchain_context':{'quality_gate':oc.get('quality_gate'),'coverage_pct':oc.get('coverage_pct'),'long_score':oc.get('long_onchain_score_0_10'),'tactical_score':oc.get('tactical_onchain_score_0_10')} if typ in ('CRYPTO','MEME') else None,'existing_engine_context':{'decision':mm.get('decision'),'long_flow':mm.get('long_flow_score_0_10'),'tactical_flow':mm.get('tactical_flow_score_0_5')} if mm else None,'deep_observation':deep,'rules':{'FAST_is_current_snapshot':True,'DEEP_crypto_checkpoints':['D0','D1','D3','D7','D30'],'DEEP_stock_checkpoints':['D0','D7','D30'],'never_auto_add_to_portfolio':True,'not_trade_execution':True,'fast_score_is_context_not_trade_signal':True}}
        reports.append(report); rows.append(row)
    payload={'generated_at_utc':NOW.isoformat(),'engine':'V8_ASSET_LAB_v0.3','active_assets':len(reports),'reports':reports,'purpose':'FAST multi-timeframe current analysis plus DEEP observation; research only'}
    (ROOT/'LAB_REPORT.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False)); cur=pd.DataFrame(rows); cur.to_csv(ROOT/'LAB_COCKPIT.csv',index=False)
    hist=cur if prior.empty else pd.concat([prior,cur],ignore_index=True,sort=False).drop_duplicates(['generated_at_utc','symbol'],keep='last')
    hist.to_csv(hp,index=False)
    status={'generated_at_utc':NOW.isoformat(),'engine':'V8_ASSET_LAB_v0.3','active_assets':len(reports),'fast_mode_ready':True,'fast_multitimeframe_enabled':True,'deep_mode_ready':True,'deep_comparison_enabled':True,'crypto_checkpoints':['D0','D1','D3','D7','D30'],'stock_checkpoints':['D0','D7','D30'],'portfolio_connection':False,'execution_connection':False}
    (ROOT/'LAB_STATUS.json').write_text(json.dumps(status,indent=2)); print(json.dumps(status,indent=2))
if __name__=='__main__': main()
