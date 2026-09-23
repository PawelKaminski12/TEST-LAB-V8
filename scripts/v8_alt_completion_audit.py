import csv
import io
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path('.')
CFG = ROOT / 'config' / 'alt_universe.csv'
ZONES = ROOT / 'config' / 'alt_zones.csv'
OUT = ROOT / 'crypto_data_hub'
OUT.mkdir(exist_ok=True)

NOW = datetime.now(timezone.utc)
TF_MAP = {'1H':'1h','4H':'4h','1D':'1d'}
BINANCE = 'https://data-api.binance.vision/api/v3/klines'
FALLBACK = 'https://api.binance.com/api/v3/klines'


def finite(x):
    try:
        v=float(x)
        return v if math.isfinite(v) else None
    except Exception:
        return None


def ema(s,n):
    return s.ewm(span=n,adjust=False).mean()


def rsi(s,n=14):
    d=s.diff(); up=d.clip(lower=0); dn=-d.clip(upper=0)
    au=up.ewm(alpha=1/n,adjust=False,min_periods=n).mean()
    ad=dn.ewm(alpha=1/n,adjust=False,min_periods=n).mean()
    rs=au/ad.replace(0,float('nan'))
    out=100-(100/(1+rs))
    out=out.mask((au>0)&(ad==0),100).mask((au==0)&(ad>0),0).mask((au==0)&(ad==0),50)
    return out.clip(0,100)


def mfi(df,n=14):
    tp=(df.High+df.Low+df.Close)/3
    mf=tp*df.Volume
    d=tp.diff()
    pos=mf.where(d>0,0.0); neg=mf.where(d<0,0.0)
    ps=pos.rolling(n,min_periods=n).sum(); ns=neg.rolling(n,min_periods=n).sum()
    ratio=ps/ns.replace(0,float('nan'))
    out=100-(100/(1+ratio))
    out=out.mask((ps==0)&(ns==0),50.0)
    out=out.mask((ps>0)&(ns==0),100.0)
    out=out.mask((ps==0)&(ns>0),0.0)
    return out.clip(0,100)


def fetch_klines(pair, interval, limit=500):
    params={'symbol':pair,'interval':interval,'limit':limit}
    err=[]
    for base in (BINANCE,FALLBACK):
        try:
            r=requests.get(base,params=params,timeout=30,headers={'User-Agent':'TEST-LAB-V8/alt-completion'})
            r.raise_for_status()
            raw=r.json()
            rows=[]
            now_ms=int(time.time()*1000)
            for x in raw:
                # closed candles only
                if int(x[6]) >= now_ms:
                    continue
                rows.append([int(x[0]),float(x[1]),float(x[2]),float(x[3]),float(x[4]),float(x[5]),int(x[6])])
            if len(rows)<220:
                raise RuntimeError(f'za mało zamkniętych świec: {len(rows)}')
            return pd.DataFrame(rows,columns=['OpenTime','Open','High','Low','Close','Volume','CloseTime']), base
        except Exception as e:
            err.append(f'{base}: {e}')
    raise RuntimeError('; '.join(err))


def technical(df):
    c=df.Close
    e20,e50,e200=ema(c,20),ema(c,50),ema(c,200)
    macd=ema(c,12)-ema(c,26); sig=ema(macd,9); hist=macd-sig
    rr=rsi(c,14); mm=mfi(df,14)
    trend=int(c.iloc[-1]>e20.iloc[-1])+int(c.iloc[-1]>e50.iloc[-1])+int(c.iloc[-1]>e200.iloc[-1])+int(e50.iloc[-1]>e50.iloc[-21])
    ret5=(c.iloc[-1]/c.iloc[-6]-1)*100 if len(c)>=6 else None
    ret20=(c.iloc[-1]/c.iloc[-21]-1)*100 if len(c)>=21 else None
    age_h=max(0,(NOW.timestamp()*1000-int(df.CloseTime.iloc[-1]))/3_600_000)
    return {
        'rows':int(len(df)), 'price':finite(c.iloc[-1]), 'trend_0_4':trend,
        'rsi14':finite(rr.iloc[-1]), 'mfi14':finite(mm.iloc[-1]), 'macd_hist':finite(hist.iloc[-1]),
        'ret5_pct':finite(ret5), 'ret20_pct':finite(ret20), 'last_closed_utc':datetime.fromtimestamp(int(df.CloseTime.iloc[-1])/1000,tz=timezone.utc).isoformat(),
        'age_hours':round(age_h,3), 'closed_candles_only':True,
    }


def load_zones():
    if not ZONES.exists(): return pd.DataFrame()
    return pd.read_csv(ZONES)


def zone_summary(zdf,sym):
    if zdf.empty: return {'confirmed_timeframes':[], 'count':0, 'complete_7_of_7':False, 'missing_timeframes':['1D','2D','3D','4D','5D','1T','2T']}
    z=zdf[(zdf.symbol.astype(str).str.upper()==sym)&(zdf.source_status.astype(str).str.upper()=='CONFIRMED')]
    tfs=sorted(set(z.timeframe.astype(str)),key=lambda x:['1D','2D','3D','4D','5D','1T','2T'].index(x) if x in ['1D','2D','3D','4D','5D','1T','2T'] else 99)
    required=['1D','2D','3D','4D','5D','1T','2T']
    missing=[x for x in required if x not in tfs]
    return {'confirmed_timeframes':tfs,'count':int(len(z)),'complete_7_of_7':not missing,'missing_timeframes':missing}


def main():
    cfg=pd.read_csv(CFG)
    cfg=cfg[cfg.enabled.astype(str).str.lower().eq('true')].copy()
    zdf=load_zones()
    assets=[]
    for _,r in cfg.iterrows():
        sym=str(r.symbol).upper().strip(); pair=str(r.binance_pair).upper().strip()
        tfs={}; sources={}; errors=[]
        for name,interval in TF_MAP.items():
            try:
                df,src=fetch_klines(pair,interval,500)
                tfs[name]=technical(df); sources[name]=src
            except Exception as e:
                errors.append(f'{name}: {e}')
        zones=zone_summary(zdf,sym)
        technical_complete=all(x in tfs for x in ['1H','4H','1D'])
        freshness_ok=technical_complete and tfs['1H']['age_hours']<=3 and tfs['4H']['age_hours']<=9 and tfs['1D']['age_hours']<=30
        production=str(r.target_scope).upper().strip()=='PRODUCTION'
        ready_auto=technical_complete and freshness_ok
        full_ready=ready_auto and zones['complete_7_of_7']
        if full_ready:
            status_pl='DANE KOMPLETNE — TECHNIKA I STREFY GOTOWE'
        elif ready_auto and not zones['complete_7_of_7']:
            status_pl='DANE RYNKOWE KOMPLETNE — BRAKUJE POTWIERDZONYCH STREF UŻYTKOWNIKA'
        else:
            status_pl='DANE NIEPEŁNE — WYMAGA UZUPEŁNIENIA'
        assets.append({
            'symbol':sym,'pair':pair,'scope':str(r.target_scope),'role':str(r.role),
            'technical':tfs,'technical_sources':sources,'technical_complete':technical_complete,
            'freshness_ok':freshness_ok,'zones':zones,'auto_layers_ready':ready_auto,'full_ready':full_ready,
            'production_asset':production,'status_pl':status_pl,'errors':errors,
        })

    etf_path=ROOT/'institutional_data_hub'/'ETF_BTC_ETH_STATUS.json'
    etf={'status_pl':'BRAK DANYCH ETF','ready':False}
    if etf_path.exists():
        x=json.loads(etf_path.read_text(encoding='utf-8'))
        etf={
            'ready': set((x.get('assets') or {}).keys())=={'BTC','ETH'} and x.get('safety',{}).get('closed_day_values_drive_scores') is True,
            'status_pl':'ETF BTC I ETH DOPIĘTE' if set((x.get('assets') or {}).keys())=={'BTC','ETH'} else 'ETF WYMAGAJĄ SPRAWDZENIA',
            'generated_at_utc':x.get('generated_at_utc'),
            'global':x.get('global_institutional_interest'),
        }

    payload={
        'generated_at_utc':NOW.isoformat(),'engine':'V8_ALT_COMPLETION_AUDIT_v1.0',
        'assets':assets,'etf':etf,
        'summary':{
            'enabled_assets':len(assets),
            'auto_layers_ready':sum(a['auto_layers_ready'] for a in assets),
            'full_ready':sum(a['full_ready'] for a in assets),
            'production_full_ready':sum(a['full_ready'] for a in assets if a['production_asset']),
            'production_count':sum(a['production_asset'] for a in assets),
            'test_validation_count':sum(not a['production_asset'] for a in assets),
        },
        'rules':{
            'no_fabricated_zones':True,
            'zones_must_come_from_confirmed_user_master':True,
            'technical_uses_closed_candles_only':True,
            'no_execution':True,
        }
    }
    (OUT/'ALT_COMPLETION_AUDIT.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')

    rows=[]
    for a in assets:
        d=a['technical'].get('1D',{})
        rows.append({
            'AKTYWO':a['symbol'],'ZAKRES':a['scope'],'STATUS':a['status_pl'],
            '1H_4H_1D': 'GOTOWE' if a['technical_complete'] else 'BRAKI',
            'CENA':d.get('price'),'TREND_1D_0_4':d.get('trend_0_4'),'RSI_1D':d.get('rsi14'),'MFI_1D':d.get('mfi14'),
            'STREFY_INTERWALY':','.join(a['zones']['confirmed_timeframes']),
            'STREFY_7_Z_7':'TAK' if a['zones']['complete_7_of_7'] else 'NIE',
            'BRAKUJACE_STREFY':','.join(a['zones']['missing_timeframes']),
        })
    pd.DataFrame(rows).to_csv(OUT/'ALT_COMPLETION_PANEL.csv',index=False)

    md=['# V8 — KOMPLETNOŚĆ ALTÓW I ETF','',f"ETF: **{etf['status_pl']}**",'']
    for a in assets:
        md += [f"## {a['symbol']} — {a['scope']}",f"- {a['status_pl']}",f"- Technika 1H/4H/1D: {'GOTOWA' if a['technical_complete'] else 'BRAKI'}.",f"- Potwierdzone strefy: {', '.join(a['zones']['confirmed_timeframes']) if a['zones']['confirmed_timeframes'] else 'brak'}."]
        if a['zones']['missing_timeframes']:
            md.append(f"- Brakujące strefy użytkownika: {', '.join(a['zones']['missing_timeframes'])}.")
        md.append('')
    md += ['System nie tworzy sztucznych stref. Strefy mogą pochodzić wyłącznie z potwierdzonego MASTER-a użytkownika.','Brak połączenia z wykonywaniem transakcji.']
    (OUT/'ALT_COMPLETION_LATEST.md').write_text('\n'.join(md),encoding='utf-8')

    print(json.dumps(payload['summary'],ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
