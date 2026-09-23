#!/usr/bin/env python3
import csv, json, math, statistics
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'tactical_validation' / 'TACTICAL_WALKFORWARD_OBSERVATIONS.csv'
LAB = ROOT / 'tactical_validation' / 'TACTICAL_THRESHOLD_LAB.json'
OUT_JSON = ROOT / 'tactical_validation' / 'TACTICAL_CHALLENGER_MATRIX_V3.json'
OUT_CSV = ROOT / 'tactical_validation' / 'TACTICAL_CHALLENGER_MATRIX_V3.csv'
REPORT = ROOT / 'audit' / 'V8_TACTICAL_CHALLENGER_V3.md'

RESEARCH_ONLY = True
DEPLOY_BLOCK = True
AUTO_EXECUTION = False


def f(v):
    try:
        return float(v)
    except Exception:
        return None


def load_rows():
    rows=[]
    with DATA.open(encoding='utf-8', newline='') as fh:
        for r in csv.DictReader(fh):
            if r.get('scope') != 'PRODUCTION':
                continue
            row = dict(r)
            for k in ['score','fomo_1h','fomo_4h','trend_1d','trend_4h','rsi_4h','fwd_3x4h_pct','fwd_6x4h_pct']:
                row[k]=f(r.get(k))
            if None in [row['score'],row['fomo_1h'],row['fomo_4h'],row['trend_1d'],row['trend_4h'],row['rsi_4h'],row['fwd_3x4h_pct'],row['fwd_6x4h_pct']]:
                continue
            rows.append(row)
    rows.sort(key=lambda x:(x.get('decision_time_utc',''),x.get('symbol','')))
    return rows


def regime(r):
    t1,t4=r['trend_1d'],r['trend_4h']
    if t1 >= 3 and t4 >= 3: return 'BULL'
    if t1 <= 2 and t4 <= 2: return 'DEFENSIVE'
    return 'MIXED'


def hit(r, rule):
    return (
        r['score'] >= rule['score_min'] and
        r['fomo_1h'] <= rule['fomo_max'] and
        r['fomo_4h'] <= rule['fomo_max'] and
        r['trend_4h'] >= rule['trend4_min'] and
        rule['rsi_lo'] <= r['rsi_4h'] <= rule['rsi_hi']
    )


def metric(rows, rule):
    sel=[r for r in rows if hit(r,rule)]
    n=len(sel)
    vals12=[r['fwd_3x4h_pct'] for r in sel]
    vals24=[r['fwd_6x4h_pct'] for r in sel]
    if not vals12:
        return {'n':0,'mean12':None,'median12':None,'win12':None,'mean24':None,'lcb12':None}
    mean12=statistics.mean(vals12)
    sd12=statistics.stdev(vals12) if n>1 else 0.0
    se=sd12/math.sqrt(n) if n else 0.0
    return {
        'n':n,
        'mean12':mean12,
        'median12':statistics.median(vals12),
        'win12':100*sum(v>0 for v in vals12)/n,
        'mean24':statistics.mean(vals24),
        'lcb12':mean12-1.0*se,
    }


def by_group(rows, rule, keyfn):
    groups={}
    for r in rows:
        groups.setdefault(keyfn(r),[]).append(r)
    return {k:metric(v,rule) for k,v in sorted(groups.items())}


def fold_slices(rows):
    times=sorted({r.get('decision_time_utc','') for r in rows})
    n=len(times)
    cuts=[int(n*0.40),int(n*0.55),int(n*0.70),int(n*0.85),n]
    folds=[]
    for i in range(1,4):
        train_end=cuts[i]
        test_end=cuts[i+1]
        train_times=set(times[:train_end]); test_times=set(times[train_end:test_end])
        folds.append((i,[r for r in rows if r.get('decision_time_utc','') in train_times],[r for r in rows if r.get('decision_time_utc','') in test_times]))
    return folds


def evaluate_rule(rows, name, rule, baseline_rule):
    overall=metric(rows,rule)
    assets=by_group(rows,rule,lambda r:r['symbol'])
    regimes=by_group(rows,rule,regime)
    times=sorted({r.get('decision_time_utc','') for r in rows})
    tindex={t:min(3,int(i*4/len(times))) for i,t in enumerate(times)} if times else {}
    quarters=by_group(rows,rule,lambda r:'Q'+str(tindex[r.get('decision_time_utc','')]+1)) if times else {}
    wf=[]
    beat=0
    for i,tr,te in fold_slices(rows):
        m=metric(te,rule); b=metric(te,baseline_rule)
        delta=None
        if m['mean12'] is not None and b['mean12'] is not None:
            delta=m['mean12']-b['mean12']
            if delta>0: beat+=1
        wf.append({'fold':i,'test':m,'baseline_test':b,'delta_mean12':delta})
    asset_means=[x['mean12'] for x in assets.values() if x['mean12'] is not None]
    quarter_means=[x['mean12'] for x in quarters.values() if x['mean12'] is not None and x['n']>=15]
    gates={
        'n_ge_200': overall['n']>=200,
        'mean12_positive': overall['mean12'] is not None and overall['mean12']>0,
        'mean24_positive': overall['mean24'] is not None and overall['mean24']>0,
        'win12_ge_52': overall['win12'] is not None and overall['win12']>=52,
        'lcb12_positive': overall['lcb12'] is not None and overall['lcb12']>0,
        'all_assets_not_bad': bool(asset_means) and min(asset_means)>=-0.10,
        'temporal_no_deep_failure': bool(quarter_means) and min(quarter_means)>=-0.50,
        'walkforward_beats_baseline_2of3': beat>=2,
    }
    strong=sum(gates.values())
    if all(gates.values()): verdict='PROMOTE_CANDIDATE_MANUAL_ONLY'
    elif strong>=6: verdict='WATCH_STRONG'
    elif strong>=4: verdict='HOLD_RESEARCH'
    else: verdict='REJECT_CHALLENGER'
    return {'name':name,'rule':rule,'overall':overall,'assets':assets,'regimes':regimes,'quarters':quarters,'walkforward':wf,'gates':gates,'gate_pass_count':strong,'verdict':verdict}


def main():
    rows=load_rows()
    if len(rows)<500:
        raise SystemExit(f'Za mało danych walidacyjnych: {len(rows)}')
    lab=json.loads(LAB.read_text(encoding='utf-8'))
    base=lab.get('candidate_for_next_validation') or {}
    base_rule={k:base[k] for k in ['score_min','fomo_max','trend4_min','rsi_lo','rsi_hi']}
    rules={
        'BASE_CANDIDATE':base_rule,
        'STRICT_QUALITY':{'score_min':7,'fomo_max':6,'trend4_min':3,'rsi_lo':48,'rsi_hi':68},
        'MOMENTUM_4H':{'score_min':7,'fomo_max':7,'trend4_min':4,'rsi_lo':50,'rsi_hi':72},
        'BALANCED_LOW_FOMO':{'score_min':6,'fomo_max':6,'trend4_min':3,'rsi_lo':45,'rsi_hi':68},
        'CONSERVATIVE_RSI':{'score_min':6,'fomo_max':6,'trend4_min':3,'rsi_lo':50,'rsi_hi':65},
    }
    results=[evaluate_rule(rows,n,r,base_rule) for n,r in rules.items()]
    rank=sorted(results,key=lambda x:(x['gate_pass_count'], x['overall']['lcb12'] if x['overall']['lcb12'] is not None else -999, x['overall']['mean12'] if x['overall']['mean12'] is not None else -999),reverse=True)
    top=rank[0]
    manual_promote=top['verdict']=='PROMOTE_CANDIDATE_MANUAL_ONLY'
    payload={
        'generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'engine':'V8_TACTICAL_CHALLENGER_FRAMEWORK_v3.0',
        'research_only':RESEARCH_ONLY,
        'deploy_block':DEPLOY_BLOCK,
        'auto_execution':AUTO_EXECUTION,
        'production_modified':False,
        'source_rows':len(rows),
        'production_assets':sorted({r['symbol'] for r in rows}),
        'method':'fixed challenger matrix + regime slices + temporal quartiles + 3-fold expanding walk-forward',
        'selection_policy':'No grid search. Fixed challengers reduce overfitting risk. Promotion can only be manual after all gates pass.',
        'top_challenger':top['name'],
        'top_verdict':top['verdict'],
        'manual_promotion_candidate':manual_promote,
        'results':results,
    }
    OUT_JSON.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    fields=['name','verdict','gate_pass_count','n','mean12','median12','win12','mean24','lcb12','score_min','fomo_max','trend4_min','rsi_lo','rsi_hi']
    with OUT_CSV.open('w',encoding='utf-8',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=fields); w.writeheader()
        for x in rank:
            o=x['overall']; r=x['rule']
            w.writerow({'name':x['name'],'verdict':x['verdict'],'gate_pass_count':x['gate_pass_count'],'n':o['n'],'mean12':o['mean12'],'median12':o['median12'],'win12':o['win12'],'mean24':o['mean24'],'lcb12':o['lcb12'],**r})
    lines=['# V8 TACTICAL — CHALLENGER FRAMEWORK V3','',f"Status: **{top['verdict']}**",'',
           '## Bezpieczeństwo','- research_only = true','- deploy_block = true','- AUTO EXECUTION = OFF','- brak automatycznej zmiany produkcji','',
           f"## Najwyżej oceniony challenger: {top['name']}",
           f"- reguła: {top['rule']}",
           f"- n = {top['overall']['n']}",
           f"- mean 12h = {top['overall']['mean12']:.3f}%" if top['overall']['mean12'] is not None else '- mean 12h = n/a',
           f"- win 12h = {top['overall']['win12']:.2f}%" if top['overall']['win12'] is not None else '- win 12h = n/a',
           f"- mean 24h = {top['overall']['mean24']:.3f}%" if top['overall']['mean24'] is not None else '- mean 24h = n/a',
           f"- LCB 12h = {top['overall']['lcb12']:.3f}%" if top['overall']['lcb12'] is not None else '- LCB 12h = n/a','',
           '## Bramki']
    for k,v in top['gates'].items(): lines.append(f"- {k}: {'PASS' if v else 'FAIL'}")
    lines += ['', '## Ranking challengerów']
    for x in rank:
        o=x['overall']; lines.append(f"- {x['name']}: {x['verdict']} | gates={x['gate_pass_count']}/8 | n={o['n']} | 12h={o['mean12']:.3f}% | win={o['win12']:.2f}% | 24h={o['mean24']:.3f}%")
    lines += ['', '## Reżimy najlepszego challengera']
    for k,v in top['regimes'].items():
        lines.append(f"- {k}: n={v['n']} | 12h={v['mean12'] if v['mean12'] is not None else 'n/a'} | win={v['win12'] if v['win12'] is not None else 'n/a'} | 24h={v['mean24'] if v['mean24'] is not None else 'n/a'}")
    lines += ['', '## Stabilność czasowa najlepszego challengera']
    for k,v in top['quarters'].items():
        lines.append(f"- {k}: n={v['n']} | 12h={v['mean12'] if v['mean12'] is not None else 'n/a'} | win={v['win12'] if v['win12'] is not None else 'n/a'} | 24h={v['mean24'] if v['mean24'] is not None else 'n/a'}")
    lines += ['', '## Decyzja', f"**{top['verdict']}**", '', 'Nawet PROMOTE_CANDIDATE_MANUAL_ONLY nie wdraża nic automatycznie. Wdrożenie wymaga osobnego ręcznego kroku, pełnego audytu oraz jawnej decyzji użytkownika.']
    REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'rows':len(rows),'top':top['name'],'verdict':top['verdict'],'gates':top['gate_pass_count'],'production_modified':False},ensure_ascii=False))

if __name__=='__main__':
    main()
