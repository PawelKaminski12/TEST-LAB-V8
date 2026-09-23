from pathlib import Path
import json
from datetime import datetime, timezone
import pandas as pd

BASE=Path('config/alt_zones.csv')
NEW=Path('config/alt_zones_screen_2026-09-23.csv')
MIG=Path('config/alt_zone_migration.csv')
AUD=Path('audit')
AUD.mkdir(exist_ok=True)
ASSETS=['ETH','SOL','LINK','ONDO','RENDER','FLOKI','PEPE','SPX6900','XRP','XLM','HBAR']
REPLACE=['XRP','XLM','RENDER','FLOKI','PEPE','SPX6900']
TFS=['1D','2D','3D','4D','5D','1T','2T']
COLS=['symbol','timeframe','side','from','to','source_status','source_note']

b=pd.read_csv(BASE)
n=pd.read_csv(NEW)
assert list(b.columns)==COLS and list(n.columns)==COLS
for df in (b,n):
    df['symbol']=df['symbol'].astype(str).str.upper()
    df['timeframe']=df['timeframe'].astype(str).str.upper()
    df['side']=df['side'].astype(str).str.upper()
    df['source_status']=df['source_status'].astype(str).str.upper()
assert set(n.symbol)==set(REPLACE)
assert (n.source_status=='CONFIRMED').all()
assert (n['from'].astype(float)<n['to'].astype(float)).all()
for sym in REPLACE:
    assert set(n.loc[n.symbol.eq(sym),'timeframe'])==set(TFS), f'{sym}: brak 7/7'

out=b[~b.symbol.isin(REPLACE)].copy()
out=pd.concat([out,n],ignore_index=True)
out.to_csv(BASE,index=False)

chk=pd.read_csv(BASE)
chk['symbol']=chk.symbol.astype(str).str.upper(); chk['timeframe']=chk.timeframe.astype(str).str.upper(); chk['source_status']=chk.source_status.astype(str).str.upper()
rows=[]
for sym in ASSETS:
    got=[tf for tf in TFS if len(chk[(chk.symbol.eq(sym))&(chk.timeframe.eq(tf))&(chk.source_status.eq('CONFIRMED'))])]
    rows.append({'symbol':sym,'got':len(got),'complete_7_of_7':len(got)==7,'timeframes':','.join(got)})
assert sum(r['got'] for r in rows)==77
assert all(r['complete_7_of_7'] for r in rows)

m=pd.read_csv(MIG)
mask=m.symbol.astype(str).str.upper().isin(REPLACE)
m.loc[mask,'source_found']=True
m.loc[mask,'numeric_ready']=True
m.loc[mask,'status_pl']='GOTOWE'
m.loc[mask,'source_note']='Screen użytkownika 2026-09-23 — komplet 7/7 zapisany liczbowo w V8'
m.to_csv(MIG,index=False)

pd.DataFrame(rows).to_csv(AUD/'V8_ZONE_FINAL_77_OF_77.csv',index=False)
payload={'generated_at_utc':datetime.now(timezone.utc).isoformat(),'ready_points':77,'total_points':77,'percent':100.0,'assets_complete':11,'assets_total':11,'rows':rows,'source':'MASTER + user screens 2026-09-23'}
(AUD/'V8_ZONE_FINAL_77_OF_77.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# V8 — STREFY 11 ALTÓW','', '**100% — 77/77 interwałów liczbowo zapisanych i potwierdzonych.**','', '**11/11 aktywów ma komplet 1D / 2D / 3D / 4D / 5D / 1T / 2T.**','']
for r in rows:
    lines.append(f"- **{r['symbol']}** — GOTOWE 7/7")
lines += ['', 'Źródła: wcześniejszy MASTER V7/V8 oraz pełne pakiety screenów użytkownika z 23.09.2026.', 'Nowe odczyty ze screenów są zaokrąglone do skali widocznej na osi wykresu.']
(AUD/'V8_ZONE_FINAL_77_OF_77.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('STREFY DOMKNIĘTE: 77/77 = 100%.')
