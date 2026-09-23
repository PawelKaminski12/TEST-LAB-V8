import csv
import json
from datetime import datetime, timezone
from pathlib import Path

REQ_TF = ['1D','2D','3D','4D','5D','1T','2T']
REQ_ASSETS = ['AAVE','HBAR']
PENDING = Path('config/alt_zones_user_pending.csv')
MASTER = Path('config/alt_zones.csv')
OUT = Path('audit')
OUT.mkdir(exist_ok=True)


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def valid_number(v):
    try:
        return float(v)
    except Exception:
        return None


def normalize(r):
    return {
        'symbol': str(r.get('symbol','')).strip().upper(),
        'timeframe': str(r.get('timeframe','')).strip().upper(),
        'side': str(r.get('side','')).strip().upper(),
        'from': str(r.get('from','')).strip(),
        'to': str(r.get('to','')).strip(),
        'source_status': str(r.get('source_status','')).strip().upper(),
        'source_note': str(r.get('source_note','')).strip(),
    }


def main():
    pending=[normalize(r) for r in read_csv(PENDING)]
    master=[normalize(r) for r in read_csv(MASTER)]
    status={'generated_at_utc':datetime.now(timezone.utc).isoformat(),'engine':'V8_USER_ZONE_GATE_v1.0','assets':{},'merge_ready':False,'merged':False,'safety':{'never_invent_zones':True,'only_confirmed_rows_can_merge':True,'requires_all_7_timeframes_per_asset':True,'execution_connected':False}}

    accepted=[]
    for sym in REQ_ASSETS:
        rows=[r for r in pending if r['symbol']==sym]
        confirmed=[]; errors=[]
        for r in rows:
            if r['source_status']!='CONFIRMED':
                continue
            if r['timeframe'] not in REQ_TF:
                errors.append(f"NIEPRAWIDŁOWY INTERWAŁ {r['timeframe']}")
                continue
            if r['side'] not in {'DEMAND','SUPPLY','FVG'}:
                errors.append(f"NIEPRAWIDŁOWA STRONA {r['timeframe']}: {r['side']}")
                continue
            lo=valid_number(r['from']); hi=valid_number(r['to'])
            if lo is None or hi is None or lo>=hi:
                errors.append(f"BŁĘDNY ZAKRES {r['timeframe']}: {r['from']}–{r['to']}")
                continue
            if not r['source_note']:
                errors.append(f"BRAK OPISU ŹRÓDŁA {r['timeframe']}")
                continue
            confirmed.append(r)
        tfs=sorted({r['timeframe'] for r in confirmed}, key=lambda x: REQ_TF.index(x) if x in REQ_TF else 99)
        missing=[tf for tf in REQ_TF if tf not in tfs]
        complete=not missing and not errors
        status['assets'][sym]={'confirmed_rows':len(confirmed),'confirmed_timeframes':tfs,'missing_timeframes':missing,'errors':errors,'complete':complete,'status_pl':'GOTOWE DO SCALENIA' if complete else 'CZEKA NA POTWIERDZONE STREFY UŻYTKOWNIKA'}
        if complete:
            accepted.extend(confirmed)

    status['merge_ready']=all(status['assets'][s]['complete'] for s in REQ_ASSETS)

    if status['merge_ready']:
        clean=[r for r in master if r['symbol'] not in REQ_ASSETS]
        merged=clean+accepted
        fields=['symbol','timeframe','side','from','to','source_status','source_note']
        with MASTER.open('w',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields)
            w.writeheader(); w.writerows(merged)
        status['merged']=True
        status['status_pl']='STREFY AAVE I HBAR ZOSTAŁY BEZPIECZNIE SCALONE Z MASTEREM'
    else:
        status['status_pl']='BRAK SCALENIA — CZEKAJĄ NA POTWIERDZONE STREFY AAVE I HBAR'

    (OUT/'V8_USER_ZONE_GATE.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# V8 — BRAMKA STREF AAVE / HBAR','',f"**{status['status_pl']}**",'']
    for sym in REQ_ASSETS:
        a=status['assets'][sym]
        lines.append(f"## {sym}")
        lines.append(f"- Status: **{a['status_pl']}**")
        lines.append(f"- Potwierdzone interwały: {', '.join(a['confirmed_timeframes']) if a['confirmed_timeframes'] else 'brak'}")
        lines.append(f"- Brakuje: {', '.join(a['missing_timeframes']) if a['missing_timeframes'] else 'nic'}")
        if a['errors']:
            lines.append(f"- Błędy: {'; '.join(a['errors'])}")
        lines.append('')
    lines += ['Scalenie nastąpi dopiero, gdy oba aktywa mają komplet 1D/2D/3D/4D/5D/1T/2T z oznaczeniem CONFIRMED i poprawnymi zakresami.','System nie tworzy sztucznych stref.']
    (OUT/'V8_USER_ZONE_GATE_LATEST.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(status,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
