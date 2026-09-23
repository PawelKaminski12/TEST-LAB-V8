import json
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path('tactical_engine')
ROOT.mkdir(exist_ok=True)
CFG = Path('config/tactical_universe.csv')
ZONES = Path('config/alt_zones.csv')
PHASE = Path('crypto_data_hub/CRYPTO_MARKET_PHASE.json')

EXPECTED = ['BTC','ETH','SOL','LINK','ONDO','RENDER','FLOKI','PEPE','SPX6900','XRP','XLM','HBAR']
INTERVALS = {'1H':'1h','4H':'4h','1D':'1d'}
LIMITS = {'1H':1000,'4H':1000,'1D':500}
MAX_STALE = {'1H':timedelta(hours=2),'4H':timedelta(hours=8),'1D':timedelta(days=2)}
NOW = pd.Timestamp.now(tz='UTC')

SPOT_BASES = [
    'https://data-api.binance.vision/api/v3/klines',
    'https://api.binance.com/api/v3/klines',
]
FUTURES_BASES = ['https://fapi.binance.com/fapi/v1/klines']

MFI_WARN_HIGH = 80.0
MFI_EXTREME_HIGH = 90.0
MFI_WARN_LOW = 20.0
MFI_EXTREME_LOW = 10.0
MACD_LOOKBACK = 250
MACD_WARN_P_HIGH = 95.0
MACD_EXTREME_P_HIGH = 97.5
MACD_WARN_P_LOW = 5.0
MACD_EXTREME_P_LOW = 2.5
MACD_WARN_Z = 1.75
MACD_EXTREME_Z = 2.0


def finite(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def fetch_klines(symbol, pair, interval, limit):
    candidates = [('SPOT', x) for x in SPOT_BASES]
    if symbol == 'SPX6900':
        candidates += [('FUTURES', x) for x in FUTURES_BASES]
    errors = []
    for source_type, base in candidates:
        try:
            r = requests.get(base, params={'symbol':pair,'interval':interval,'limit':limit}, timeout=30)
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, list) or len(data) < 220:
                raise RuntimeError(f'za mało świec: {len(data) if isinstance(data,list) else 0}')
            cols = ['open_time','open','high','low','close','volume','close_time','qav','trades','tb_base','tb_quote','ignore']
            df = pd.DataFrame(data, columns=cols)
            for c in ['open','high','low','close','volume']:
                df[c] = pd.to_numeric(df[c], errors='coerce')
            df['open_time'] = pd.to_datetime(df['open_time'], unit='ms', utc=True)
            df['close_time'] = pd.to_datetime(df['close_time'], unit='ms', utc=True)
            df = df[['open_time','close_time','open','high','low','close','volume']].dropna().drop_duplicates('open_time').sort_values('open_time').reset_index(drop=True)
            df = df[df['close_time'] < NOW - pd.Timedelta(seconds=5)].reset_index(drop=True)
            if len(df) < 220:
                raise RuntimeError(f'za mało zamkniętych świec: {len(df)}')
            return df, base, source_type
        except Exception as e:
            errors.append(f'{source_type}:{base}:{e}')
    raise RuntimeError(' | '.join(errors))


def ema(s, n):
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def rsi_wilder(close, n=14):
    d = close.diff()
    up = d.clip(lower=0)
    dn = -d.clip(upper=0)
    au = up.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    ad = dn.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    rs = au / ad.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    out = out.mask((au == 0) & (ad == 0), 50.0)
    out = out.mask((au > 0) & (ad == 0), 100.0)
    return out


def mfi(df, n=14):
    tp = (df['high'] + df['low'] + df['close']) / 3.0
    raw = tp * df['volume']
    direction = tp.diff()
    pos = raw.where(direction > 0, 0.0)
    neg = raw.where(direction < 0, 0.0)
    pos_sum = pos.rolling(n, min_periods=n).sum()
    neg_sum = neg.rolling(n, min_periods=n).sum()
    ratio = pos_sum / neg_sum.replace(0, np.nan)
    out = 100 - (100 / (1 + ratio))
    out = out.mask((pos_sum == 0) & (neg_sum == 0), 50.0)
    out = out.mask((pos_sum > 0) & (neg_sum == 0), 100.0)
    out = out.mask((pos_sum == 0) & (neg_sum > 0), 0.0)
    return out.clip(0,100)


def atr(df, n=14):
    pc = df['close'].shift(1)
    tr = pd.concat([
        (df['high']-df['low']).abs(),
        (df['high']-pc).abs(),
        (df['low']-pc).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False, min_periods=n).mean()


def enrich(df):
    x = df.copy()
    x['ema20'] = ema(x['close'],20)
    x['ema50'] = ema(x['close'],50)
    x['ema200'] = ema(x['close'],200)
    x['macd'] = ema(x['close'],12) - ema(x['close'],26)
    x['macd_signal'] = ema(x['macd'],9)
    x['macd_hist'] = x['macd'] - x['macd_signal']
    x['rsi14'] = rsi_wilder(x['close'],14)
    x['mfi14'] = mfi(x,14)
    x['atr14'] = atr(x,14)
    x['vol_sma20'] = x['volume'].rolling(20,min_periods=20).mean()
    x['vol_ratio'] = x['volume'] / x['vol_sma20']
    x['high20_prev'] = x['high'].shift(1).rolling(20,min_periods=20).max()
    x['low20_prev'] = x['low'].shift(1).rolling(20,min_periods=20).min()
    x['ret5'] = x['close'].pct_change(5)*100
    x['ret20'] = x['close'].pct_change(20)*100
    return x


def classify_macd(hist):
    clean = pd.to_numeric(hist, errors='coerce').dropna().reset_index(drop=True)
    if len(clean) < 80:
        return {'macd_hist_percentile':None,'macd_hist_zscore':None,'macd_extreme_label':'NO_DATA','macd_extreme_warning':False,'macd_extreme':False,'macd_extreme_direction':'NONE','macd_extreme_lookback':int(len(clean))}
    cur = float(clean.iloc[-1])
    ref = clean.iloc[max(0,len(clean)-MACD_LOOKBACK-1):-1]
    if len(ref) < 60:
        ref = clean.iloc[:-1]
    mean = float(ref.mean())
    std = float(ref.std(ddof=0))
    z = (cur-mean)/std if std > 0 else 0.0
    pct = float((ref <= cur).mean()*100.0)
    if pct >= MACD_EXTREME_P_HIGH and z >= MACD_EXTREME_Z:
        label,warn,ext,direction='EXTREME_POSITIVE',True,True,'POSITIVE'
    elif pct <= MACD_EXTREME_P_LOW and z <= -MACD_EXTREME_Z:
        label,warn,ext,direction='EXTREME_NEGATIVE',True,True,'NEGATIVE'
    elif pct >= MACD_WARN_P_HIGH or z >= MACD_WARN_Z:
        label,warn,ext,direction='WARNING_POSITIVE',True,False,'POSITIVE'
    elif pct <= MACD_WARN_P_LOW or z <= -MACD_WARN_Z:
        label,warn,ext,direction='WARNING_NEGATIVE',True,False,'NEGATIVE'
    else:
        label,warn,ext,direction='NORMAL',False,False,'NONE'
    return {'macd_hist_percentile':pct,'macd_hist_zscore':float(z),'macd_extreme_label':label,'macd_extreme_warning':warn,'macd_extreme':ext,'macd_extreme_direction':direction,'macd_extreme_lookback':int(len(ref))}


def mfi_zone(v):
    if v is None: return 'NO_DATA'
    if v >= MFI_EXTREME_HIGH: return 'EXTREME_OVERBOUGHT'
    if v >= MFI_WARN_HIGH: return 'OVERBOUGHT_WARNING'
    if v <= MFI_EXTREME_LOW: return 'EXTREME_OVERSOLD'
    if v <= MFI_WARN_LOW: return 'OVERSOLD_WARNING'
    return 'NORMAL'


def bar_state(x, label):
    r = x.iloc[-1]
    p = x.iloc[-2]
    close = float(r['close'])
    e20,e50,e200 = finite(r['ema20']),finite(r['ema50']),finite(r['ema200'])
    macd_v,sig,hist = finite(r['macd']),finite(r['macd_signal']),finite(r['macd_hist'])
    hist_prev = finite(p['macd_hist'])
    rv,mfiv,vr,a = finite(r['rsi14']),finite(r['mfi14']),finite(r['vol_ratio']),finite(r['atr14'])
    h20,l20 = finite(r['high20_prev']),finite(r['low20_prev'])
    trend = sum([
        int(e20 is not None and close > e20),
        int(e50 is not None and close > e50),
        int(e20 is not None and e50 is not None and e20 > e50),
        int(e200 is not None and close > e200),
    ])
    macd_score = 0
    if macd_v is not None and sig is not None:
        macd_score = int(macd_v > sig) + int(hist is not None and hist_prev is not None and hist > hist_prev)
    rsi_score = 2 if rv is not None and 50 <= rv <= 70 else 1 if rv is not None and (40 <= rv < 50 or 70 < rv <= 75) else 0
    volume_score = 2 if vr is not None and vr >= 1.5 else 1 if vr is not None and vr >= 1.0 else 0
    mfi_confirmation = 1 if mfiv is not None and 45 <= mfiv <= 75 else 0
    breakout = bool(h20 is not None and close > h20)
    breakdown = bool(l20 is not None and close < l20)
    retest = False
    retest_level = None
    if a and a > 0:
        start = max(20, len(x)-11)
        for i in range(start, len(x)-1):
            rr = x.iloc[i]
            if pd.notna(rr['high20_prev']) and float(rr['close']) > float(rr['high20_prev']):
                level = float(rr['high20_prev'])
                after = x.iloc[i+1:]
                if len(after) and ((after['low'] <= level + 0.5*a) & (after['close'] >= level)).any():
                    retest=True; retest_level=level
    fomo = 0
    if rv is not None:
        fomo += 4 if rv >= 80 else 3 if rv >= 75 else 2 if rv >= 70 else 0
    r5 = finite(r['ret5'])
    if r5 is not None:
        fomo += 3 if r5 >= 15 else 2 if r5 >= 10 else 1 if r5 >= 6 else 0
    if a and e20:
        extension = (close-e20)/a
        fomo += 3 if extension >= 3 else 2 if extension >= 2 else 1 if extension >= 1.5 else 0
    fomo = min(10,int(fomo))
    mz = mfi_zone(mfiv)
    mex = classify_macd(x['macd_hist'])
    flags=[]
    if rv is not None and rv >= 75: flags.append('RSI_OVERBOUGHT')
    if rv is not None and rv <= 25: flags.append('RSI_OVERSOLD')
    if mz not in ['NORMAL','NO_DATA']: flags.append('MFI_'+mz)
    if mex['macd_extreme_label'] not in ['NORMAL','NO_DATA']: flags.append('MACD_'+mex['macd_extreme_label'])
    if fomo >= 8: flags.append('FOMO_HARD_BLOCK')
    out={
        'timeframe':label,'close':close,'trend_score_0_4':int(trend),
        'macd':macd_v,'macd_signal':sig,'macd_hist':hist,'macd_score_0_2':int(macd_score),
        'rsi14':rv,'rsi_score_0_2':int(rsi_score),'mfi14':mfiv,'mfi_zone':mz,
        'mfi_warning':mz in ['OVERBOUGHT_WARNING','OVERSOLD_WARNING'],
        'mfi_extreme':mz in ['EXTREME_OVERBOUGHT','EXTREME_OVERSOLD'],
        'volume_ratio_vs_20':vr,'volume_score_0_2':int(volume_score),'atr14':a,
        'breakout_20':breakout,'breakdown_20':breakdown,'retest_10':retest,'retest_level':retest_level,
        'fomo_score_0_10':fomo,'fomo_label':'HARD_BLOCK' if fomo>=8 else 'RISK' if fomo>=6 else 'WATCH' if fomo>=4 else 'NORMAL',
        'return_5bars_pct':r5,'return_20bars_pct':finite(r['ret20']),
        'technical_confirmation_0_10':int(min(10,trend+macd_score+rsi_score+volume_score+mfi_confirmation)),
        'extreme_flags':flags,
    }
    out.update(mex)
    return out


def load_zones():
    if not ZONES.exists():
        return pd.DataFrame(columns=['symbol','timeframe','side','from','to','source_status','source_note'])
    z=pd.read_csv(ZONES)
    for c in ['symbol','timeframe','side','source_status','source_note']:
        if c in z.columns: z[c]=z[c].astype(str)
    return z


def zone_context(zones, sym, price):
    if zones.empty: return {'ready':False,'status_pl':'BRAK POTWIERDZONYCH STREF'}
    z=zones[(zones['symbol'].str.upper()==sym)&(zones['source_status'].str.upper()=='CONFIRMED')].copy()
    if z.empty: return {'ready':False,'status_pl':'BRAK POTWIERDZONYCH STREF'}
    z['from_n']=pd.to_numeric(z['from'],errors='coerce'); z['to_n']=pd.to_numeric(z['to'],errors='coerce')
    z=z.dropna(subset=['from_n','to_n']); z=z[z['to_n']>=z['from_n']]
    dem=z[z['side'].str.upper()=='DEMAND']; sup=z[z['side'].str.upper()=='SUPPLY']
    def dist(row):
        lo,hi=float(row.from_n),float(row.to_n)
        if lo<=price<=hi: return 0.0
        return min(abs(price-lo),abs(price-hi))
    def nearest(part):
        if part.empty: return None
        row=min((r for _,r in part.iterrows()),key=dist)
        return {'timeframe':str(row.timeframe),'from':float(row.from_n),'to':float(row.to_n),'distance_pct':dist(row)/price*100}
    return {
        'ready':True,'status_pl':'STREFY POTWIERDZONE',
        'in_demand':any(float(r.from_n)<=price<=float(r.to_n) for _,r in dem.iterrows()),
        'in_supply':any(float(r.from_n)<=price<=float(r.to_n) for _,r in sup.iterrows()),
        'nearest_demand':nearest(dem),'nearest_supply':nearest(sup),
        'confirmed_timeframes':sorted(set(z['timeframe'].str.upper()))
    }


def confluence_label(states):
    over=0; under=0
    weights={'1H':1,'4H':2,'1D':3}
    for tf,st in states.items():
        w=weights[tf]
        if st.get('rsi14') is not None and st['rsi14']>=75: over+=w
        if st.get('rsi14') is not None and st['rsi14']<=25: under+=w
        if st.get('mfi14') is not None and st['mfi14']>=80: over+=w
        if st.get('mfi14') is not None and st['mfi14']<=20: under+=w
        if st.get('macd_extreme_direction')=='POSITIVE' and st.get('macd_extreme_warning'): over+=w
        if st.get('macd_extreme_direction')=='NEGATIVE' and st.get('macd_extreme_warning'): under+=w
        if st.get('fomo_score_0_10',0)>=8: over+=w
    if over>=10 and over>=under+4: return 'HIGH_PRIORITY_OVERHEAT',over,under
    if under>=8 and under>=over+4: return 'HIGH_PRIORITY_OVERSOLD',over,under
    if over>=6: return 'OVERHEAT_CONFLUENCE',over,under
    if under>=6: return 'OVERSOLD_CONFLUENCE',over,under
    if over>=3 or under>=3: return 'WATCH_EXTREMES',over,under
    return 'NORMAL',over,under


def main():
    cfg=pd.read_csv(CFG)
    cfg=cfg[cfg['enabled'].astype(str).str.lower().eq('true')].copy()
    got=list(cfg['symbol'].astype(str).str.upper())
    if got != EXPECTED:
        raise SystemExit(f'Nieprawidłowa aktywna lista TACTICAL: {got}')
    if any('STOCK' in str(x).upper() for x in cfg.get('role',[])):
        raise SystemExit('TACTICAL nie może zawierać spółek')
    zones=load_zones()
    phase=json.loads(PHASE.read_text(encoding='utf-8')) if PHASE.exists() else {}
    generated=datetime.now(timezone.utc).isoformat()
    assets=[]; qa=[]; macd_rows=[]; conf_rows=[]; ready_rows=[]

    for _,row in cfg.iterrows():
        sym=str(row['symbol']).upper().strip(); pair=str(row['pair']).upper().strip(); scope=str(row['target_scope']).upper().strip()
        states={}; sources={}; source_types={}; errors=[]
        for tf,iv in INTERVALS.items():
            try:
                raw,src,src_type=fetch_klines(sym,pair,iv,LIMITS[tf])
                enriched=enrich(raw)
                st=bar_state(enriched,tf)
                last_close=enriched.iloc[-1]['close_time']; age=NOW-last_close
                st['rows_closed']=int(len(enriched)); st['last_close_time_utc']=last_close.isoformat(); st['closed_bar_only']=True; st['stale']=bool(age>pd.Timedelta(MAX_STALE[tf]))
                if st['stale']: errors.append(f'{tf}:DANE NIEŚWIEŻE')
                states[tf]=st; sources[tf]=src; source_types[tf]=src_type
                raw.to_csv(ROOT/f'{pair}_{tf}.csv',index=False)
            except Exception as e:
                errors.append(f'{tf}:{e}')
        if errors or set(states)!=set(INTERVALS):
            assets.append({'symbol':sym,'pair':pair,'target_scope':scope,'qa':'FAIL','errors':errors})
            qa.append({'symbol':sym,'PASS':False,'errors':' | '.join(errors)})
            continue

        h1,h4,d1=states['1H'],states['4H'],states['1D']
        zc=zone_context(zones,sym,h4['close'])
        score=0
        score += 2 if d1['trend_score_0_4']>=3 else 1 if d1['trend_score_0_4']>=2 else 0
        score += 3 if h4['trend_score_0_4']>=3 and h4['macd_score_0_2']>=1 else 1 if h4['trend_score_0_4']>=2 else 0
        score += 2 if h4['rsi14'] is not None and 45<=h4['rsi14']<=70 else 0
        score += 1 if (h4['volume_ratio_vs_20'] or 0)>=1 else 0
        score += 1 if h1['macd_score_0_2']>=1 else 0
        score += 1 if h1['retest_10'] or h4['retest_10'] else 0
        score=min(10,int(score))
        hard_fomo=max(h1['fomo_score_0_10'],h4['fomo_score_0_10'])>=8
        daily_weak=d1['trend_score_0_4']<=1
        breakdown=h4['breakdown_20']; in_supply=bool(zc.get('in_supply'))
        blockers=[]
        if hard_fomo: blockers.append('FOMO_HARD_BLOCK')
        if daily_weak: blockers.append('DAILY_REGIME_WEAK')
        if breakdown: blockers.append('4H_BREAKDOWN')
        if in_supply: blockers.append('IN_SUPPLY')
        if hard_fomo: decision,reason='NO_TRADE_FOMO','Skrajne FOMO na 1H/4H blokuje nowe wejście.'
        elif daily_weak or breakdown: decision,reason='NO_TRADE','Słaby kierunek 1D lub wybicie dołem na 4H.'
        elif in_supply: decision,reason='WATCH_SUPPLY','Cena jest w potwierdzonej strefie podaży.'
        elif score>=8 and (h4['retest_10'] or h1['retest_10']): decision,reason='LONG_SETUP_RETEST','Mocne potwierdzenie i retest.'
        elif score>=8 and h4['breakout_20']: decision,reason='WATCH_BREAKOUT','Mocne wybicie wymaga utrzymania lub retestu.'
        elif score>=7: decision,reason='LONG_SETUP_WATCH','Dobre ustawienie wielu interwałów; timing jeszcze niepełny.'
        elif score>=5: decision,reason='WAIT','Sygnały mieszane.'
        else: decision,reason='NO_TRADE','Za mało potwierdzeń.'
        exit_risk=min(10,
            (2 if h1['rsi14'] is not None and h1['rsi14']>=75 else 0)+
            (2 if h4['rsi14'] is not None and h4['rsi14']>=75 else 0)+
            (2 if h1['macd_hist'] is not None and h1['macd_hist']<0 else 0)+
            (2 if h4['macd_hist'] is not None and h4['macd_hist']<0 else 0)+
            (2 if breakdown else 0)+(1 if in_supply else 0)+
            (1 if h1['mfi_extreme'] and (h1['mfi14'] or 0)>=90 else 0)+
            (1 if h4['mfi_extreme'] and (h4['mfi14'] or 0)>=90 else 0))
        exit_label='EXIT_RISK_HIGH' if exit_risk>=7 else 'TAKE_PROFIT_WATCH' if exit_risk>=4 else 'HOLD_TACTICAL_OK'
        extreme_summary=[f'{tf}:{flag}' for tf,st in states.items() for flag in st.get('extreme_flags',[])]
        conf_label,overheat,oversold=confluence_label(states)
        asset={
            'symbol':sym,'pair':pair,'target_scope':scope,'qa':'PASS','sources':sources,'source_types':source_types,'timeframes':states,
            'tactical_score_0_10':score,'tactical_status':decision,'reason_pl':reason,'entry_blockers':blockers,'zone_context':zc,
            'market_phase_context':{'phase':phase.get('phase'),'confidence':phase.get('phase_confidence'),'role':'kontekst, nie samodzielna blokada'},
            'exit_risk_0_10':exit_risk,'exit_risk_label':exit_label,'extreme_summary':extreme_summary,
            'extreme_confluence':{'label':conf_label,'overheat_score':overheat,'oversold_score':oversold,'role':'alarm kontekstowy, nie samodzielny sygnał transakcyjny'},
            'market_reader_external':{'status':'DO PODŁĄCZENIA PÓŹNIEJ','role':'drugie oko; TradingView później'}
        }
        assets.append(asset); qa.append({'symbol':sym,'PASS':True,'errors':''})
        for tf,st in states.items():
            macd_rows.append({'symbol':sym,'timeframe':tf,'macd_hist':st['macd_hist'],'macd_hist_percentile':st['macd_hist_percentile'],'macd_hist_zscore':st['macd_hist_zscore'],'macd_extreme_label':st['macd_extreme_label'],'macd_extreme_warning':st['macd_extreme_warning'],'macd_extreme':st['macd_extreme'],'lookback':st['macd_extreme_lookback']})
        conf_rows.append({'symbol':sym,'label':conf_label,'overheat_score':overheat,'oversold_score':oversold,'extremes':' | '.join(extreme_summary)})
        ready_rows.append({'symbol':sym,'status_pl':'GOTOWY' if set(states)==set(INTERVALS) else 'DANE NIEPEŁNE','1H':True,'4H':True,'1D':True,'zones_ready':bool(zc.get('ready')),'source_1H':source_types['1H'],'source_4H':source_types['4H'],'source_1D':source_types['1D']})

    good=[a for a in assets if a.get('qa')=='PASS']
    if len(good)!=len(EXPECTED) or [a['symbol'] for a in good]!=EXPECTED:
        print(json.dumps({'qa':qa},ensure_ascii=False,indent=2))
        raise SystemExit('TACTICAL: nie wszystkie 12 aktywów mają komplet danych 1H/4H/1D')

    payload={
        'generated_at_utc':generated,'engine':'V8_TACTICAL_ENGINE_v1.0','purpose_pl':'Silnik krótkoterminowy: 1H timing, 4H główna decyzja, 1D kierunek.',
        'research_only':True,'not_execution_connected':True,'separate_from_long_engine':True,'stocks_included':False,
        'universe':EXPECTED,'asset_count':len(EXPECTED),
        'rules':{
            'closed_candles_only':True,'1H_role':'timing','4H_role':'główna decyzja','1D_role':'kierunek',
            'macd_rsi_mfi_volume_are_confirmation_not_standalone_trade_signals':True,'mfi_period':14,'mfi_edge_cases_fixed':True,
            'macd_extremes_relative_to_own_history':True,'macd_extreme_lookback_bars':MACD_LOOKBACK,'fomo_hard_block':8,
            'higher_timeframe_zones_are_context_not_standalone_signal':True,'in_supply_blocks_tactical_long_labels':True,
            'missing_user_zones_do_not_block_indicator_monitoring':True,'market_phase_context_not_hard_gate':True,
            'tradingview_connected':False,'email_alarm_layer_supported_by_google_sheets_bridge':True,
            'spx6900_source_policy':'Binance spot if available; otherwise Binance USD-M perpetual futures',
        },
        'assets':assets
    }
    ROOT.joinpath('TACTICAL_ENGINE.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    pd.DataFrame(qa).to_csv(ROOT/'TACTICAL_QA.csv',index=False)
    pd.DataFrame(macd_rows).to_csv(ROOT/'TACTICAL_MACD_EXTREMES.csv',index=False)
    pd.DataFrame(conf_rows).to_csv(ROOT/'TACTICAL_EXTREME_CONFLUENCE.csv',index=False)
    pd.DataFrame(ready_rows).to_csv(ROOT/'TACTICAL_READINESS.csv',index=False)
    readiness={'generated_at_utc':generated,'engine':'V8_TACTICAL_READINESS_v1.0','status_pl':'WSZYSTKIE 12 AKTYWÓW GOTOWE','asset_count':len(ready_rows),'all_assets_ready':True,'timeframes':['1H','4H','1D'],'stocks_included':False,'tradingview_connected':False,'execution_connected':False,'assets':ready_rows}
    ROOT.joinpath('TACTICAL_READINESS.json').write_text(json.dumps(readiness,ensure_ascii=False,indent=2),encoding='utf-8')
    cockpit=[]
    for a in assets:
        t=a['timeframes']
        cockpit.append({'symbol':a['symbol'],'qa':'PASS','status':a['tactical_status'],'score_0_10':a['tactical_score_0_10'],'exit_risk_0_10':a['exit_risk_0_10'],'1H_rsi':t['1H']['rsi14'],'1H_mfi':t['1H']['mfi14'],'1H_macd_percentile':t['1H']['macd_hist_percentile'],'4H_rsi':t['4H']['rsi14'],'4H_mfi':t['4H']['mfi14'],'4H_macd_percentile':t['4H']['macd_hist_percentile'],'1D_rsi':t['1D']['rsi14'],'1D_mfi':t['1D']['mfi14'],'1D_macd_percentile':t['1D']['macd_hist_percentile'],'extreme_confluence':a['extreme_confluence']['label'],'zones':a['zone_context']['status_pl'],'source':a['source_types']['4H']})
    pd.DataFrame(cockpit).to_csv(ROOT/'TACTICAL_COCKPIT.csv',index=False)
    print(json.dumps({'engine':payload['engine'],'assets':[a['symbol'] for a in assets],'all_ready':True},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
