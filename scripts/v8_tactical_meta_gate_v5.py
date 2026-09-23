#!/usr/bin/env python3
import csv, json, math, statistics
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OBS = ROOT / 'tactical_validation' / 'TACTICAL_WALKFORWARD_OBSERVATIONS.csv'
CHALLENGER = ROOT / 'tactical_validation' / 'TACTICAL_CHALLENGER_MATRIX_V3.json'
REGIME_HIST = ROOT / 'tactical_validation' / 'TACTICAL_REGIME_GATE_V4_HISTORY.csv'
REGIME_CUR = ROOT / 'tactical_validation' / 'TACTICAL_REGIME_GATE_CURRENT.json'
ENGINE = ROOT / 'tactical_engine' / 'TACTICAL_ENGINE.json'
OUT = ROOT / 'tactical_validation'
OUT_JSON = OUT / 'TACTICAL_META_GATE_V5.json'
OUT_CUR_JSON = OUT / 'TACTICAL_META_GATE_CURRENT.json'
OUT_CUR_CSV = OUT / 'TACTICAL_META_GATE_CURRENT.csv'
OUT_HIST_CSV = OUT / 'TACTICAL_META_GATE_V5_HISTORY.csv'
REPORT = ROOT / 'audit' / 'V8_TACTICAL_META_GATE_V5.md'

RESEARCH_ONLY=True
DEPLOY_BLOCK=True
AUTO_EXECUTION=False
PRODUCTION_MODIFIED=False


def f(v):
    try: return float(v)
    except Exception: return None


def load_obs():
    rows=[]
    with OBS.open(encoding='utf-8', newline='') as fh:
        for r in csv.DictReader(fh):
            if r.get('scope')!='PRODUCTION': continue
            x=dict(r)
            for k in ['score','fomo_1h','fomo_4h','trend_1d','trend_4h','rsi_4h','fwd_3x4h_pct','fwd_6x4h_pct']:
                x[k]=f(r.get(k))
            if any(x[k] is None for k in ['score','fomo_1h','fomo_4h','trend_1d','trend_4h','rsi_4h','fwd_3x4h_pct','fwd_6x4h_pct']):
                continue
            rows.append(x)
    return rows


def top_rule():
    p=json.loads(CHALLENGER.read_text(encoding='utf-8'))
    top=p['top_challenger']
    for r in p['results']:
        if r['name']==top: return top,r['rule']
    raise RuntimeError('Brak top_challenger')


def hit(r, rule):
    return (r['score']>=rule['score_min'] and r['fomo_1h']<=rule['fomo_max'] and
            r['fomo_4h']<=rule['fomo_max'] and r['trend_4h']>=rule['trend4_min'] and
            rule['rsi_lo']<=r['rsi_4h']<=rule['rsi_hi'])


def metric(rows):
    n=len(rows)
    if not n: return {'n':0,'mean12':None,'median12':None,'win12':None,'mean24':None,'lcb12':None}
    a=[r['fwd_3x4h_pct'] for r in rows]; b=[r['fwd_6x4h_pct'] for r in rows]
    m=statistics.mean(a); sd=statistics.stdev(a) if n>1 else 0.0; se=sd/math.sqrt(n)
    return {'n':n,'mean12':m,'median12':statistics.median(a),'win12':100*sum(v>0 for v in a)/n,
            'mean24':statistics.mean(b),'lcb12':m-se}


def load_regimes():
    out={}
    with REGIME_HIST.open(encoding='utf-8', newline='') as fh:
        for r in csv.DictReader(fh): out[r['decision_time_utc']]=r['status']
    return out


def historical_risk_proxy(r):
    pts=0; reasons=[]
    st=(r.get('status') or '').upper()
    if st.startswith('NO_TRADE'):
        pts+=2; reasons.append('status NO_TRADE')
    elif 'SUPPLY' in st:
        pts+=1; reasons.append('status SUPPLY')
    mx=max(r['fomo_1h'],r['fomo_4h'])
    if mx>=8:
        pts+=2; reasons.append('FOMO>=8')
    elif mx>=6:
        pts+=1; reasons.append('FOMO>=6')
    if r['rsi_4h']>=72:
        pts+=1; reasons.append('RSI4H>=72')
    if r['trend_4h']<=1:
        pts+=1; reasons.append('trend4H<=1')
    return pts,reasons


def meta_decision(ch, rg, risk):
    if not ch: return 'HOLD_CHALLENGER'
    if rg=='BLOCK': return 'BLOCK'
    if rg=='CAUTION': return 'CAUTION'
    if risk>=3: return 'BLOCK'
    if risk>=1: return 'CAUTION'
    return 'ALLOW'


def temporal(rows):
    times=sorted({r['decision_time_utc'] for r in rows})
    idx={t:min(3,int(i*4/max(1,len(times)))) for i,t in enumerate(times)}
    out={}
    for i in range(4): out['Q'+str(i+1)]=metric([r for r in rows if idx.get(r['decision_time_utc'])==i])
    return out


def historical(rows, rule):
    regimes=load_regimes()
    selected=[]; groups={k:[] for k in ['ALLOW','CAUTION','BLOCK','HOLD_CHALLENGER']}
    details=[]
    for r in rows:
        ch=hit(r,rule); rg=regimes.get(r['decision_time_utc'],'CAUTION'); risk,reasons=historical_risk_proxy(r)
        d=meta_decision(ch,rg,risk)
        z={**r,'challenger_hit':ch,'regime_gate':rg,'risk_proxy':risk,'meta_decision':d,'risk_reason':'; '.join(reasons)}
        details.append(z); groups[d].append(z)
        if ch: selected.append(z)
    gm={k:metric(v) for k,v in groups.items()}
    ungated=metric(selected)
    tq=temporal(groups['ALLOW'])
    allow=gm['ALLOW']; block=gm['BLOCK']
    gates={
        'allow_n_ge_100': allow['n']>=100,
        'allow_mean12_positive': allow['mean12'] is not None and allow['mean12']>0,
        'allow_mean24_positive': allow['mean24'] is not None and allow['mean24']>0,
        'allow_lcb12_positive': allow['lcb12'] is not None and allow['lcb12']>0,
        'allow_win_not_worse_than_ungated': allow['win12'] is not None and ungated['win12'] is not None and allow['win12']>=ungated['win12'],
        'allow_mean12_beats_ungated': allow['mean12'] is not None and ungated['mean12'] is not None and allow['mean12']>ungated['mean12'],
        'block_underperforms_allow': block['mean12'] is None or (allow['mean12'] is not None and block['mean12']<allow['mean12']),
        'allow_temporal_no_deep_failure': all(v['n']<15 or (v['mean12'] is not None and v['mean12']>=-0.50) for v in tq.values()),
    }
    pc=sum(gates.values())
    verdict='META_GATE_VALIDATED_RESEARCH' if pc==8 else ('WATCH_META_GATE' if pc>=6 else 'HOLD_META_GATE')
    return ungated,gm,tq,gates,pc,verdict,details


def current_risk(a):
    pts=0; reasons=[]
    exitr=f(a.get('exit_risk_0_10')) or 0
    if exitr>=8: pts+=3; reasons.append('exit risk>=8')
    elif exitr>=6: pts+=2; reasons.append('exit risk>=6')
    elif exitr>=4: pts+=1; reasons.append('exit risk>=4')
    st=(a.get('tactical_status') or '').upper()
    if st.startswith('NO_TRADE'): pts+=2; reasons.append('status NO_TRADE')
    elif 'SUPPLY' in st: pts+=1; reasons.append('status SUPPLY')
    z=(a.get('zone_context') or {}).get('status_pl','').upper()
    if 'PODAŻ' in z: pts+=2; reasons.append('strefa podaży')
    tf=a.get('timeframes') or {}
    fomo=max([f((tf.get(k) or {}).get('fomo_score_0_10')) or 0 for k in ['1H','4H','1D']])
    if fomo>=8: pts+=3; reasons.append('FOMO>=8')
    elif fomo>=6: pts+=1; reasons.append('FOMO>=6')
    ec=a.get('extreme_confluence') or {}
    hot=f(ec.get('overheat_score')) or 0
    if hot>=3: pts+=3; reasons.append('przegrzanie ekstremalne')
    elif hot>=2: pts+=2; reasons.append('przegrzanie zbieżne')
    elif hot>=1: pts+=1; reasons.append('przegrzanie')
    return pts,reasons,exitr,fomo,hot


def current(rule):
    eng=json.loads(ENGINE.read_text(encoding='utf-8'))
    rg=json.loads(REGIME_CUR.read_text(encoding='utf-8'))
    rg_status=rg.get('status','CAUTION')
    rg_rows={r['symbol']:r for r in rg.get('rows',[])}
    rows=[]
    for a in eng.get('assets',[]):
        if a.get('symbol')=='BTC': continue
        sym=a.get('symbol'); rr=rg_rows.get(sym,{})
        ch=bool(rr.get('challenger_hit'))
        risk,reasons,exitr,fomo,hot=current_risk(a)
        d=meta_decision(ch,rg_status,risk)
        rows.append({'symbol':sym,'challenger_hit':ch,'regime_gate':rg_status,'risk_points':risk,
                     'exit_risk':exitr,'max_fomo':fomo,'overheat_score':hot,'production_status':a.get('tactical_status',''),
                     'meta_decision':d,'reasons':'; '.join(reasons) if reasons else 'brak dodatkowych blokad'})
    counts={k:sum(r['meta_decision']==k for r in rows) for k in ['ALLOW','CAUTION','BLOCK','HOLD_CHALLENGER']}
    return {'engine_snapshot_utc':eng.get('generated_at_utc'),'regime_gate':rg_status,'rows':rows,'counts':counts}


def write_csv(path,rows,fields):
    with path.open('w',encoding='utf-8',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=fields); w.writeheader(); w.writerows([{k:r.get(k,'') for k in fields} for r in rows])


def main():
    rows=load_obs()
    if len(rows)<500: raise SystemExit(f'Za mało obserwacji: {len(rows)}')
    name,rule=top_rule()
    ungated,gm,tq,gates,pc,verdict,details=historical(rows,rule)
    cur=current(rule)
    payload={'generated_at_utc':datetime.now(timezone.utc).isoformat(),'engine':'V8_TACTICAL_META_GATE_v5.0',
             'research_only':True,'deploy_block':True,'auto_execution':False,'production_modified':False,
             'source_rows':len(rows),'challenger':name,'rule':rule,
             'historical_note':'Pełne pola exit-risk/extreme/strefy nie istnieją w starej próbce; historia używa jawnego risk proxy z status/FOMO/RSI/trend. Bieżący meta-gate używa pełniejszych pól z TACTICAL_ENGINE.',
             'historical_ungated_challenger':ungated,'historical_by_meta_decision':gm,'allow_quarters':tq,
             'validation_gates':gates,'gate_pass_count':pc,'verdict':verdict,
             'current':{k:v for k,v in cur.items() if k!='rows'},'manual_promotion_only':True}
    OUT_JSON.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    OUT_CUR_JSON.write_text(json.dumps({'generated_at_utc':datetime.now(timezone.utc).isoformat(),**cur,'research_only':True,'deploy_block':True},ensure_ascii=False,indent=2),encoding='utf-8')
    write_csv(OUT_CUR_CSV,cur['rows'],['symbol','challenger_hit','regime_gate','risk_points','exit_risk','max_fomo','overheat_score','production_status','meta_decision','reasons'])
    write_csv(OUT_HIST_CSV,details,['decision_time_utc','symbol','status','score','fomo_1h','fomo_4h','trend_1d','trend_4h','rsi_4h','challenger_hit','regime_gate','risk_proxy','meta_decision','risk_reason','fwd_3x4h_pct','fwd_6x4h_pct'])
    lines=['# V8 TACTICAL — META GATE V5','',f'Status: **{verdict}**','',
           '## Bezpieczeństwo','- research_only = true','- deploy_block = true','- AUTO EXECUTION = OFF','- produkcyjny Tactical i Apps Script V9 pozostają nietknięte','',
           f'## Challenger: {name}',f'- reguła: {rule}','',
           '## Metoda','- łączy Challenger V3 + Regime Gate V4 + warstwę ryzyka','- historia: risk proxy z production status / FOMO / RSI / trend','- bieżąco: dodatkowo exit_risk, strefy i extreme_confluence z Tactical Engine','',
           '## Wynik historyczny challengera bez meta-gate',f"- n={ungated['n']} | 12h={ungated['mean12']:.3f}% | win={ungated['win12']:.2f}% | 24h={ungated['mean24']:.3f}%",'',
           '## Wyniki wg decyzji Meta Gate']
    for k in ['ALLOW','CAUTION','BLOCK','HOLD_CHALLENGER']:
        m=gm[k]
        if m['n']:
            lines.append(f"- {k}: n={m['n']} | 12h={m['mean12']:.3f}% | win={m['win12']:.2f}% | 24h={m['mean24']:.3f}% | LCB12={m['lcb12']:.3f}%")
        else: lines.append(f'- {k}: n=0')
    lines += ['', '## Bramki walidacyjne']
    for k,v in gates.items(): lines.append(f"- {k}: {'PASS' if v else 'FAIL'}")
    lines += ['', '## Bieżący Meta Gate',f"- reżim rynku: **{cur['regime_gate']}**",f"- ALLOW: {cur['counts']['ALLOW']}",f"- CAUTION: {cur['counts']['CAUTION']}",f"- BLOCK: {cur['counts']['BLOCK']}",f"- HOLD_CHALLENGER: {cur['counts']['HOLD_CHALLENGER']}",'']
    for r in cur['rows']:
        lines.append(f"- {r['symbol']}: {r['meta_decision']} | risk={r['risk_points']} | prod={r['production_status']} | {r['reasons']}")
    lines += ['', '## Decyzja',f'**{verdict}**','', 'Meta Gate V5 pozostaje warstwą badawczą. Nawet pozytywna walidacja nie zmienia produkcji automatycznie.']
    REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'rows':len(rows),'challenger':name,'verdict':verdict,'gates':pc,'current_counts':cur['counts'],'production_modified':False},ensure_ascii=False))

if __name__=='__main__': main()
