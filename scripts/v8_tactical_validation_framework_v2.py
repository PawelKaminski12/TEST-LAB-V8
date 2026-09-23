#!/usr/bin/env python3
import csv, json, math, statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OBS = ROOT / 'tactical_validation' / 'TACTICAL_WALKFORWARD_OBSERVATIONS.csv'
LAB = ROOT / 'tactical_validation' / 'TACTICAL_THRESHOLD_LAB.json'
OUT = ROOT / 'tactical_validation'
AUDIT = ROOT / 'audit'

PROD_POSITIVE = {'LONG_SETUP_WATCH','LONG_SETUP_RETEST','WATCH_BREAKOUT'}
PRODUCTION_SYMBOLS = {'ETH','SOL','LINK','ONDO'}
MIN_BLOCK_N = 15


def f(v):
    try: return float(v)
    except Exception: return None


def mean(xs):
    return statistics.fmean(xs) if xs else None


def med(xs):
    return statistics.median(xs) if xs else None


def pct_pos(xs):
    return 100.0 * sum(x > 0 for x in xs) / len(xs) if xs else None


def fmt(x, digits=3):
    return 'n/a' if x is None else f'{x:.{digits}f}'


def candidate_pass(r, c):
    vals = [f(r.get('score')), f(r.get('fomo_1h')), f(r.get('fomo_4h')), f(r.get('trend_4h')), f(r.get('rsi_4h'))]
    if any(v is None for v in vals): return False
    score, f1, f4, t4, rsi = vals
    return score >= c['score_min'] and f1 <= c['fomo_max'] and f4 <= c['fomo_max'] and t4 >= c['trend4_min'] and c['rsi_lo'] <= rsi <= c['rsi_hi']


def regime(r):
    t1, t4 = f(r.get('trend_1d')), f(r.get('trend_4h'))
    if t1 is None or t4 is None: return 'UNKNOWN'
    if t1 >= 3 and t4 >= 3: return 'BULL'
    if t1 <= 1 and t4 <= 1: return 'WEAK'
    return 'MIXED'


def stats(rows):
    x12 = [f(r.get('fwd_3x4h_pct')) for r in rows]
    x24 = [f(r.get('fwd_6x4h_pct')) for r in rows]
    x12 = [x for x in x12 if x is not None]
    x24 = [x for x in x24 if x is not None]
    return {
        'n': len(x12), 'mean_12h': mean(x12), 'median_12h': med(x12), 'win_12h_pct': pct_pos(x12),
        'mean_24h': mean(x24), 'median_24h': med(x24), 'win_24h_pct': pct_pos(x24),
    }


def split_time(rows, parts=4):
    rows = sorted(rows, key=lambda r:r.get('decision_time_utc',''))
    n=len(rows); out=[]
    for i in range(parts):
        a=math.floor(i*n/parts); b=math.floor((i+1)*n/parts)
        out.append(rows[a:b])
    return out


def main():
    lab=json.loads(LAB.read_text(encoding='utf-8'))
    c=lab['candidate_for_next_validation']
    required=['score_min','fomo_max','trend4_min','rsi_lo','rsi_hi']
    c={k:c[k] for k in required}
    with OBS.open(encoding='utf-8',newline='') as fh:
        rows=list(csv.DictReader(fh))
    if not rows: raise SystemExit('Brak obserwacji walk-forward')

    # Strict no-lookahead evidence source: outcomes already prepared by the historical validation layer.
    for r in rows:
        r['_candidate']=candidate_pass(r,c)
        r['_prod_positive']=str(r.get('status','')) in PROD_POSITIVE
        r['_regime']=regime(r)

    prod=[r for r in rows if r.get('symbol') in PRODUCTION_SYMBOLS]
    cand=[r for r in prod if r['_candidate']]
    baseline=[r for r in prod if r['_prod_positive']]

    by_asset={}
    for s in sorted(PRODUCTION_SYMBOLS):
        rr=[r for r in cand if r.get('symbol')==s]
        by_asset[s]=stats(rr)

    by_regime={}
    for rg in ['BULL','MIXED','WEAK','UNKNOWN']:
        rr=[r for r in cand if r['_regime']==rg]
        if rr: by_regime[rg]=stats(rr)

    temporal=[]
    for i, block in enumerate(split_time(prod,4),1):
        bc=[r for r in block if r['_candidate']]
        temporal.append({'block':f'Q{i}','from':block[0].get('decision_time_utc') if block else None,'to':block[-1].get('decision_time_utc') if block else None,**stats(bc)})

    overall=stats(cand); prod_baseline=stats(baseline)
    eligible_assets=[v for v in by_asset.values() if v['n']>=MIN_BLOCK_N]
    eligible_time=[v for v in temporal if v['n']>=MIN_BLOCK_N]
    eligible_regimes=[v for v in by_regime.values() if v['n']>=MIN_BLOCK_N]

    checks={
      'minimum_candidate_observations': overall['n'] >= 80,
      'overall_mean12_positive': (overall['mean_12h'] or -999) > 0.20,
      'overall_win12_min_53': (overall['win_12h_pct'] or 0) >= 53,
      'overall_mean24_positive': (overall['mean_24h'] or -999) > 0.35,
      'all_production_assets_positive_mean12': bool(eligible_assets) and all((x['mean_12h'] or -999)>0 for x in eligible_assets),
      'temporal_blocks_stable': len(eligible_time)>=3 and sum((x['mean_12h'] or -999)>0 for x in eligible_time)>=3 and min((x['mean_12h'] or -999) for x in eligible_time)>-0.15,
      'regime_coverage': len(eligible_regimes)>=2,
      'regime_stability': len(eligible_regimes)>=2 and sum((x['mean_12h'] or -999)>0 for x in eligible_regimes)>=2,
      'production_baseline_comparison': (overall['mean_12h'] or -999) >= (prod_baseline['mean_12h'] or -999),
    }

    critical=['minimum_candidate_observations','overall_mean12_positive','overall_win12_min_53','overall_mean24_positive','all_production_assets_positive_mean12','temporal_blocks_stable','regime_coverage','regime_stability']
    promote=all(checks[k] for k in critical)
    reject=(overall['n']>=80 and (overall['mean_12h'] or 0)<0 and (overall['mean_24h'] or 0)<0)
    decision='PROMOTE_CANDIDATE' if promote else ('REJECT_CANDIDATE' if reject else 'HOLD_RESEARCH')

    payload={
      'generated_at_utc':datetime.now(timezone.utc).isoformat(),
      'engine':'V8_TACTICAL_VALIDATION_FRAMEWORK_v2.0',
      'research_only':True,'deploy_block':True,'auto_execution':False,
      'production_thresholds_modified':False,'no_lookahead_contract':True,
      'source':'TACTICAL_WALKFORWARD_OBSERVATIONS.csv',
      'candidate':c,'production_symbols':sorted(PRODUCTION_SYMBOLS),
      'overall_candidate':overall,'production_positive_baseline':prod_baseline,
      'by_asset':by_asset,'by_regime':by_regime,'temporal_quartiles':temporal,
      'promotion_checks':checks,'promotion_decision':decision,
      'promotion_allowed_automatically':False,
      'note':'PROMOTE_CANDIDATE, jeśli kiedykolwiek wystąpi, oznacza wyłącznie kwalifikację do ręcznego przeglądu; nigdy automatyczny deploy.'
    }
    (OUT/'TACTICAL_VALIDATION_FRAMEWORK_V2.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')

    with (OUT/'TACTICAL_VALIDATION_FRAMEWORK_V2_ASSETS.csv').open('w',encoding='utf-8',newline='') as fh:
        fields=['symbol','n','mean_12h','median_12h','win_12h_pct','mean_24h','median_24h','win_24h_pct']
        w=csv.DictWriter(fh,fieldnames=fields); w.writeheader()
        for s,v in by_asset.items(): w.writerow({'symbol':s,**v})

    with (OUT/'TACTICAL_VALIDATION_FRAMEWORK_V2_REGIMES.csv').open('w',encoding='utf-8',newline='') as fh:
        fields=['regime','n','mean_12h','median_12h','win_12h_pct','mean_24h','median_24h','win_24h_pct']
        w=csv.DictWriter(fh,fieldnames=fields); w.writeheader()
        for rg,v in by_regime.items(): w.writerow({'regime':rg,**v})

    md=['# V8 TACTICAL — VALIDATION FRAMEWORK 2.0','',f'Status: **{decision}**','',
        '## Kontrakt bezpieczeństwa','- research_only = true','- deploy_block = true','- AUTO EXECUTION = OFF','- brak automatycznej zmiany progów produkcyjnych','- dane historyczne bez projekcji bieżących stref wstecz','',
        '## Kandydat',f"- score >= {c['score_min']}",f"- FOMO 1H/4H <= {c['fomo_max']}",f"- trend 4H >= {c['trend4_min']}",f"- RSI 4H = {c['rsi_lo']}–{c['rsi_hi']}",'',
        '## Wynik łączny',f"- n = {overall['n']}",f"- mean 12h = {fmt(overall['mean_12h'])}%",f"- win 12h = {fmt(overall['win_12h_pct'],2)}%",f"- mean 24h = {fmt(overall['mean_24h'])}%",'',
        '## Stabilność per aktywo']
    for s,v in by_asset.items(): md.append(f"- {s}: n={v['n']} | 12h={fmt(v['mean_12h'])}% | win={fmt(v['win_12h_pct'],2)}% | 24h={fmt(v['mean_24h'])}%")
    md += ['', '## Reżimy rynku']
    for rg,v in by_regime.items(): md.append(f"- {rg}: n={v['n']} | 12h={fmt(v['mean_12h'])}% | win={fmt(v['win_12h_pct'],2)}% | 24h={fmt(v['mean_24h'])}%")
    md += ['', '## Stabilność czasowa']
    for v in temporal: md.append(f"- {v['block']}: n={v['n']} | 12h={fmt(v['mean_12h'])}% | win={fmt(v['win_12h_pct'],2)}% | 24h={fmt(v['mean_24h'])}%")
    md += ['', '## Bramka promocji']
    for k,v in checks.items(): md.append(f"- {k}: {'PASS' if v else 'FAIL'}")
    md += ['', '## Decyzja', f'**{decision}**', '', 'Nawet status PROMOTE_CANDIDATE nie może automatycznie zmienić produkcji. Wymagany jest osobny ręczny krok i ponowny audyt.']
    (AUDIT/'V8_TACTICAL_VALIDATION_FRAMEWORK_V2.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(json.dumps({'decision':decision,'overall':overall,'checks':checks},ensure_ascii=False))

if __name__=='__main__': main()
