#!/usr/bin/env python3
import csv, json, math, random, statistics
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
HIST=ROOT/'tactical_validation'/'TACTICAL_META_GATE_V5_HISTORY.csv'
OUT=ROOT/'tactical_validation'
OUT_JSON=OUT/'TACTICAL_STABILITY_PACK_V6.json'
OUT_CSV=OUT/'TACTICAL_STABILITY_PACK_V6_WINDOWS.csv'
REPORT=ROOT/'audit'/'V8_TACTICAL_STABILITY_PACK_V6.md'

RESEARCH_ONLY=True
DEPLOY_BLOCK=True
AUTO_EXECUTION=False
PRODUCTION_MODIFIED=False
SEED=20260923


def f(v):
    try:return float(v)
    except:return None

def load_rows():
    rows=[]
    with HIST.open(encoding='utf-8',newline='') as fh:
        for r in csv.DictReader(fh):
            if r.get('meta_decision')!='ALLOW':
                continue
            x=dict(r)
            x['ret12']=f(r.get('fwd_3x4h_pct')); x['ret24']=f(r.get('fwd_6x4h_pct'))
            if x['ret12'] is None or x['ret24'] is None: continue
            rows.append(x)
    rows.sort(key=lambda r:(r.get('decision_time_utc',''),r.get('symbol','')))
    return rows

def metric(rows):
    n=len(rows)
    if not n:return {'n':0,'mean12':None,'median12':None,'win12':None,'mean24':None,'lcb12':None}
    a=[r['ret12'] for r in rows]; b=[r['ret24'] for r in rows]
    m=statistics.mean(a); sd=statistics.stdev(a) if n>1 else 0.0; se=sd/math.sqrt(n)
    return {'n':n,'mean12':m,'median12':statistics.median(a),'win12':100*sum(v>0 for v in a)/n,'mean24':statistics.mean(b),'lcb12':m-1.28*se}

def rolling_windows(rows,parts=8):
    times=sorted({r['decision_time_utc'] for r in rows})
    out=[]
    for i in range(parts):
        lo=int(len(times)*i/parts); hi=int(len(times)*(i+1)/parts)
        tset=set(times[lo:hi]); rr=[r for r in rows if r['decision_time_utc'] in tset]
        out.append({'window':f'W{i+1}',**metric(rr)})
    return out

def expanding_folds(rows):
    times=sorted({r['decision_time_utc'] for r in rows})
    folds=[]
    cuts=[0.45,0.60,0.75,0.90,1.00]
    for i in range(3):
        tr_end=int(len(times)*cuts[i+1]); te_end=int(len(times)*cuts[i+2])
        test=set(times[tr_end:te_end]); rr=[r for r in rows if r['decision_time_utc'] in test]
        folds.append({'fold':i+1,**metric(rr)})
    return folds

def bootstrap(rows,nboot=2000):
    rng=random.Random(SEED)
    vals=[r['ret12'] for r in rows]
    means=[]
    for _ in range(nboot):
        sample=[vals[rng.randrange(len(vals))] for _ in vals]
        means.append(statistics.mean(sample))
    means.sort()
    return {'samples':nboot,'p05':means[int(.05*nboot)],'p50':means[int(.50*nboot)],'p95':means[int(.95*nboot)],'prob_mean_positive':sum(v>0 for v in means)/nboot}

def leave_one_asset_out(rows):
    syms=sorted({r['symbol'] for r in rows}); out=[]
    for s in syms:
        rr=[r for r in rows if r['symbol']!=s]
        out.append({'excluded':s,**metric(rr)})
    return out

def main():
    rows=load_rows()
    if len(rows)<200: raise SystemExit(f'Za mało ALLOW do testu stabilności: {len(rows)}')
    overall=metric(rows); wins=rolling_windows(rows,8); folds=expanding_folds(rows); boot=bootstrap(rows); loo=leave_one_asset_out(rows)
    valid_w=[w for w in wins if w['n']>=15]
    pos_windows=sum((w['mean12'] or -999)>0 for w in valid_w)
    deep_fail=sum((w['mean12'] or 0)<-0.50 for w in valid_w)
    fold_pos=sum((x['mean12'] or -999)>0 for x in folds)
    loo_bad=sum((x['mean12'] or 0)<=0 for x in loo)
    gates={
      'sample_ge_250':overall['n']>=250,
      'overall_mean12_positive':overall['mean12']>0,
      'overall_mean24_positive':overall['mean24']>0,
      'bootstrap_p05_positive':boot['p05']>0,
      'bootstrap_prob_positive_ge_90pct':boot['prob_mean_positive']>=0.90,
      'rolling_positive_6of8':pos_windows>=6,
      'rolling_no_deep_failure':deep_fail==0,
      'expanding_folds_positive_2of3':fold_pos>=2,
      'leave_one_asset_out_all_positive':loo_bad==0,
    }
    pc=sum(gates.values())
    if pc==9: verdict='KEEP_STRONG_RESEARCH'
    elif pc>=7: verdict='KEEP_WATCH_RESEARCH'
    elif pc>=5: verdict='HOLD_RESEARCH'
    else: verdict='REJECT_META_GATE_RESEARCH'
    payload={'generated_at_utc':datetime.now(timezone.utc).isoformat(),'engine':'V8_TACTICAL_STABILITY_PACK_v6.0','research_only':True,'deploy_block':True,'auto_execution':False,'production_modified':False,'source_allow_rows':len(rows),'overall':overall,'bootstrap':boot,'rolling_windows':wins,'expanding_folds':folds,'leave_one_asset_out':loo,'validation_gates':gates,'gate_pass_count':pc,'verdict':verdict,'manual_promotion_only':True}
    OUT_JSON.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    fields=['window','n','mean12','median12','win12','mean24','lcb12']
    with OUT_CSV.open('w',encoding='utf-8',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=fields);w.writeheader();w.writerows([{k:x.get(k,'') for k in fields} for x in wins])
    lines=['# V8 TACTICAL — STABILITY PACK V6','',f'Status: **{verdict}**','',
      '## Bezpieczeństwo','- research_only = true','- deploy_block = true','- AUTO EXECUTION = OFF','- produkcja nietknięta','',
      '## Overall ALLOW',f"- n={overall['n']} | 12h={overall['mean12']:.3f}% | win={overall['win12']:.2f}% | 24h={overall['mean24']:.3f}% | LCB={overall['lcb12']:.3f}%",'',
      '## Bootstrap 2000',f"- p05={boot['p05']:.3f}% | p50={boot['p50']:.3f}% | p95={boot['p95']:.3f}% | P(mean>0)={boot['prob_mean_positive']:.1%}",'',
      '## Rolling 8 okien']
    for x in wins: lines.append(f"- {x['window']}: n={x['n']} | 12h={x['mean12'] if x['mean12'] is not None else 'n/a'} | win={x['win12'] if x['win12'] is not None else 'n/a'} | 24h={x['mean24'] if x['mean24'] is not None else 'n/a'}")
    lines += ['', '## Expanding folds']
    for x in folds: lines.append(f"- F{x['fold']}: n={x['n']} | 12h={x['mean12'] if x['mean12'] is not None else 'n/a'} | win={x['win12'] if x['win12'] is not None else 'n/a'}")
    lines += ['', '## Bramki']
    for k,v in gates.items(): lines.append(f"- {k}: {'PASS' if v else 'FAIL'}")
    lines += ['', '## Decyzja',f'**{verdict}**','', 'Pakiet ocenia odporność Meta Gate V5. Nie wdraża niczego do produkcji.']
    REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'n':len(rows),'verdict':verdict,'gates':pc,'bootstrap_p05':boot['p05'],'production_modified':False},ensure_ascii=False))

if __name__=='__main__':main()
