#!/usr/bin/env python3
import csv, json, math, statistics
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OBS = ROOT / 'tactical_validation' / 'TACTICAL_WALKFORWARD_OBSERVATIONS.csv'
CHALLENGER = ROOT / 'tactical_validation' / 'TACTICAL_CHALLENGER_MATRIX_V3.json'
ENGINE = ROOT / 'tactical_engine' / 'TACTICAL_ENGINE.json'
OUT = ROOT / 'tactical_validation'
OUT_JSON = OUT / 'TACTICAL_REGIME_GATE_V4.json'
CURRENT_JSON = OUT / 'TACTICAL_REGIME_GATE_CURRENT.json'
CURRENT_CSV = OUT / 'TACTICAL_REGIME_GATED_SHADOW_CURRENT.csv'
REGIME_CSV = OUT / 'TACTICAL_REGIME_GATE_V4_HISTORY.csv'
REPORT = ROOT / 'audit' / 'V8_TACTICAL_REGIME_GATE_V4.md'

RESEARCH_ONLY = True
DEPLOY_BLOCK = True
AUTO_EXECUTION = False
PRODUCTION_MODIFIED = False

# Fixed before evaluation. These are market-breadth gates, not optimized per asset.
GATE = {
    'active': {'breadth_1d_min': 0.60, 'breadth_4h_min': 0.55, 'fomo8_share_max': 0.35},
    'block': {'breadth_1d_below': 0.40, 'breadth_4h_below': 0.35, 'fomo8_share_above': 0.50},
    'current_btc_active_trend_min': 3,
    'current_btc_block_trend_max': 2,
}


def f(v):
    try: return float(v)
    except Exception: return None


def read_obs():
    rows=[]
    with OBS.open(encoding='utf-8', newline='') as fh:
        for r in csv.DictReader(fh):
            if r.get('scope') != 'PRODUCTION':
                continue
            x=dict(r)
            for k in ['score','fomo_1h','fomo_4h','trend_1d','trend_4h','rsi_4h','fwd_3x4h_pct','fwd_6x4h_pct']:
                x[k]=f(r.get(k))
            req=['score','fomo_1h','fomo_4h','trend_1d','trend_4h','rsi_4h','fwd_3x4h_pct','fwd_6x4h_pct']
            if any(x[k] is None for k in req): continue
            rows.append(x)
    return rows


def challenger_rule():
    p=json.loads(CHALLENGER.read_text(encoding='utf-8'))
    top=p['top_challenger']
    for r in p['results']:
        if r['name']==top:
            return top, r['rule']
    raise RuntimeError('Nie znaleziono top_challenger w V3')


def hit(r, rule):
    return (r['score'] >= rule['score_min'] and r['fomo_1h'] <= rule['fomo_max'] and
            r['fomo_4h'] <= rule['fomo_max'] and r['trend_4h'] >= rule['trend4_min'] and
            rule['rsi_lo'] <= r['rsi_4h'] <= rule['rsi_hi'])


def regime_from_snapshot(rows):
    n=len(rows)
    if not n: return {'status':'NO_DATA','n':0}
    b1=sum(r['trend_1d']>=3 for r in rows)/n
    b4=sum(r['trend_4h']>=3 for r in rows)/n
    f8=sum(r['fomo_4h']>=8 for r in rows)/n
    if b1 >= GATE['active']['breadth_1d_min'] and b4 >= GATE['active']['breadth_4h_min'] and f8 <= GATE['active']['fomo8_share_max']:
        status='ACTIVE'
    elif b1 < GATE['block']['breadth_1d_below'] or b4 < GATE['block']['breadth_4h_below'] or f8 > GATE['block']['fomo8_share_above']:
        status='BLOCK'
    else:
        status='CAUTION'
    return {'status':status,'n':n,'breadth_1d':b1,'breadth_4h':b4,'fomo8_share':f8,
            'avg_score':statistics.mean(r['score'] for r in rows)}


def metric(rows):
    n=len(rows)
    if not n: return {'n':0,'mean12':None,'median12':None,'win12':None,'mean24':None,'lcb12':None}
    a=[r['fwd_3x4h_pct'] for r in rows]; b=[r['fwd_6x4h_pct'] for r in rows]
    m=statistics.mean(a); sd=statistics.stdev(a) if n>1 else 0.0; se=sd/math.sqrt(n)
    return {'n':n,'mean12':m,'median12':statistics.median(a),'win12':100*sum(v>0 for v in a)/n,
            'mean24':statistics.mean(b),'lcb12':m-se}


def historical(rows, rule):
    bytime={}
    for r in rows: bytime.setdefault(r['decision_time_utc'],[]).append(r)
    regimes={t:regime_from_snapshot(rs) for t,rs in bytime.items()}
    selected=[r for r in rows if hit(r,rule)]
    groups={'ACTIVE':[],'CAUTION':[],'BLOCK':[]}
    for r in selected:
        s=regimes[r['decision_time_utc']]['status']
        if s in groups: groups[s].append(r)
    overall=metric(selected)
    gm={k:metric(v) for k,v in groups.items()}
    # Time stability for ACTIVE only.
    times=sorted({r['decision_time_utc'] for r in selected})
    tidx={t:min(3,int(i*4/max(1,len(times)))) for i,t in enumerate(times)}
    quarters={}
    for i in range(4):
        rr=[r for r in groups['ACTIVE'] if tidx.get(r['decision_time_utc'])==i]
        quarters['Q'+str(i+1)]=metric(rr)
    active=gm['ACTIVE']; block=gm['BLOCK']
    gates={
        'active_n_ge_100': active['n']>=100,
        'active_mean12_beats_ungated': active['mean12'] is not None and overall['mean12'] is not None and active['mean12']>overall['mean12'],
        'active_win12_not_worse': active['win12'] is not None and overall['win12'] is not None and active['win12']>=overall['win12'],
        'active_mean24_positive': active['mean24'] is not None and active['mean24']>0,
        'active_lcb12_positive': active['lcb12'] is not None and active['lcb12']>0,
        'block_underperforms_active': block['mean12'] is None or (active['mean12'] is not None and block['mean12']<active['mean12']),
        'active_temporal_no_deep_failure': all(v['n']<15 or (v['mean12'] is not None and v['mean12']>=-0.50) for v in quarters.values()),
    }
    pc=sum(gates.values())
    verdict='REGIME_GATE_VALIDATED_RESEARCH' if pc==7 else ('WATCH_REGIME_GATE' if pc>=5 else 'HOLD_REGIME_GATE')
    history=[]
    for t in sorted(regimes): history.append({'decision_time_utc':t,**regimes[t]})
    return overall,gm,quarters,gates,pc,verdict,history


def current(rule):
    e=json.loads(ENGINE.read_text(encoding='utf-8'))
    assets=e.get('assets',[])
    btc=next((a for a in assets if a.get('symbol')=='BTC'),None)
    alts=[a for a in assets if a.get('symbol')!='BTC']
    rows=[]
    for a in alts:
        tf=a.get('timeframes') or {}; h1=tf.get('1H') or {}; h4=tf.get('4H') or {}; d1=tf.get('1D') or {}
        x={'symbol':a.get('symbol'),'score':f(a.get('tactical_score_0_10')),'fomo_1h':f(h1.get('fomo_score_0_10')),
           'fomo_4h':f(h4.get('fomo_score_0_10')),'trend_1d':f(d1.get('trend_score_0_4')),
           'trend_4h':f(h4.get('trend_score_0_4')),'rsi_4h':f(h4.get('rsi14')),'production_status':a.get('tactical_status','')}
        if all(x[k] is not None for k in ['score','fomo_1h','fomo_4h','trend_1d','trend_4h','rsi_4h']): rows.append(x)
    base=regime_from_snapshot(rows)
    btc1=btc4=None
    if btc:
        tf=btc.get('timeframes') or {}; btc1=f((tf.get('1D') or {}).get('trend_score_0_4')); btc4=f((tf.get('4H') or {}).get('trend_score_0_4'))
    status=base['status']
    reasons=[f"breadth={status}"]
    if btc1 is not None and btc4 is not None:
        if btc1 <= GATE['current_btc_block_trend_max'] and btc4 <= GATE['current_btc_block_trend_max']:
            status='BLOCK'; reasons.append('BTC 1D+4H defensywne')
        elif status=='ACTIVE' and not (btc1>=GATE['current_btc_active_trend_min'] and btc4>=GATE['current_btc_active_trend_min']):
            status='CAUTION'; reasons.append('BTC nie potwierdza ACTIVE na 1D+4H')
        elif status=='ACTIVE': reasons.append('BTC potwierdza 1D+4H')
    out=[]
    for r in rows:
        ch=hit(r,rule)
        if not ch: gs='HOLD_CHALLENGER'
        elif status=='ACTIVE': gs='PASS_GATE_ACTIVE'
        elif status=='CAUTION': gs='HOLD_GATE_CAUTION'
        else: gs='HOLD_GATE_BLOCK'
        out.append({**r,'challenger_hit':ch,'regime_gate':status,'gated_shadow_signal':gs})
    return {'engine_snapshot_utc':e.get('generated_at_utc'),'status':status,'breadth':base,
            'btc_trend_1d':btc1,'btc_trend_4h':btc4,'reasons':reasons,'rows':out}


def write_csv(path, rows, fields):
    with path.open('w',encoding='utf-8',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=fields); w.writeheader(); w.writerows([{k:r.get(k,'') for k in fields} for r in rows])


def main():
    rows=read_obs()
    if len(rows)<500: raise SystemExit(f'Za mało obserwacji: {len(rows)}')
    name,rule=challenger_rule()
    overall,gm,quarters,gates,pc,verdict,hist=historical(rows,rule)
    cur=current(rule)
    payload={'generated_at_utc':datetime.now(timezone.utc).isoformat(),'engine':'V8_TACTICAL_REGIME_GATE_v4.0',
             'research_only':RESEARCH_ONLY,'deploy_block':DEPLOY_BLOCK,'auto_execution':AUTO_EXECUTION,
             'production_modified':PRODUCTION_MODIFIED,'source_rows':len(rows),'challenger':name,'rule':rule,
             'gate_definition':GATE,'historical_ungated':overall,'historical_by_gate':gm,'active_quarters':quarters,
             'validation_gates':gates,'gate_pass_count':pc,'verdict':verdict,'current':{k:v for k,v in cur.items() if k!='rows'},
             'manual_promotion_only':True,'note':'Regime Gate steruje wyłącznie warstwą badawczą challengera; nie zmienia produkcyjnego Tactical.'}
    OUT_JSON.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    CURRENT_JSON.write_text(json.dumps({'generated_at_utc':datetime.now(timezone.utc).isoformat(),**cur,'research_only':True,'deploy_block':True},ensure_ascii=False,indent=2),encoding='utf-8')
    write_csv(CURRENT_CSV,cur['rows'],['symbol','score','fomo_1h','fomo_4h','trend_1d','trend_4h','rsi_4h','production_status','challenger_hit','regime_gate','gated_shadow_signal'])
    write_csv(REGIME_CSV,hist,['decision_time_utc','status','n','breadth_1d','breadth_4h','fomo8_share','avg_score'])
    lines=['# V8 TACTICAL — REGIME GATE V4','',f'Status: **{verdict}**','',
           '## Kontrakt bezpieczeństwa','- research_only = true','- deploy_block = true','- AUTO EXECUTION = OFF','- produkcyjny Tactical i panel V9 pozostają nietknięte','',
           f'## Challenger pod bramką: {name}',f'- reguła: {rule}','',
           '## Wynik bez bramki',f"- n={overall['n']} | 12h={overall['mean12']:.3f}% | win={overall['win12']:.2f}% | 24h={overall['mean24']:.3f}%",'',
           '## Wyniki wg reżimu bramki']
    for k in ['ACTIVE','CAUTION','BLOCK']:
        m=gm[k]
        if m['n']: lines.append(f"- {k}: n={m['n']} | 12h={m['mean12']:.3f}% | win={m['win12']:.2f}% | 24h={m['mean24']:.3f}% | LCB12={m['lcb12']:.3f}%")
        else: lines.append(f'- {k}: n=0')
    lines += ['', '## Bramki walidacyjne']
    for k,v in gates.items(): lines.append(f"- {k}: {'PASS' if v else 'FAIL'}")
    lines += ['', '## Aktualny Gate', f"- status: **{cur['status']}**", f"- breadth 1D: {cur['breadth'].get('breadth_1d',0):.2%}", f"- breadth 4H: {cur['breadth'].get('breadth_4h',0):.2%}", f"- FOMO>=8 share: {cur['breadth'].get('fomo8_share',0):.2%}", f"- BTC trend 1D/4H: {cur['btc_trend_1d']} / {cur['btc_trend_4h']}", f"- powód: {'; '.join(cur['reasons'])}", '', '## Aktualne wyniki gated shadow']
    for r in cur['rows']:
        lines.append(f"- {r['symbol']}: {r['gated_shadow_signal']} | challenger={'PASS' if r['challenger_hit'] else 'HOLD'} | prod={r['production_status']}")
    lines += ['', '## Decyzja',f'**{verdict}**','', 'Nawet pozytywna walidacja bramki nie wdraża jej do produkcji. Wymagany jest osobny ręczny krok i pełny audyt.']
    REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'rows':len(rows),'challenger':name,'verdict':verdict,'gates':pc,'current_gate':cur['status'],'production_modified':False},ensure_ascii=False))

if __name__=='__main__': main()
