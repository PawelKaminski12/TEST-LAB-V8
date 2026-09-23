import csv
import json
from datetime import datetime, timezone
from pathlib import Path

OUT=Path('audit'); OUT.mkdir(exist_ok=True)
GS=Path('google_sheets'); GS.mkdir(exist_ok=True)
NOW=datetime.now(timezone.utc).isoformat()
ALTS=['ETH','SOL','LINK','ONDO','RENDER','FLOKI','PEPE','SPX6900','XRP','XLM','HBAR','AVAX','AWE']
TACT=['BTC']+ALTS


def load_json(path):
    p=Path(path)
    if not p.exists(): return {}
    return json.loads(p.read_text(encoding='utf-8'))

def exists(path): return Path(path).exists()

master=load_json('crypto_data_hub/ALT_ENGINE_MASTER_CHECKPOINT.json')
long_engine=load_json('crypto_data_hub/ALT_DECISION_ENGINE.json')
long_ready=load_json('crypto_data_hub/ALT_ENGINE_READINESS.json')
tactical=load_json('tactical_engine/TACTICAL_ENGINE.json')
tactical_ready=load_json('tactical_engine/TACTICAL_READINESS.json')
zones=load_json('audit/V8_ZONE_FINAL_91_OF_91.json')
etf=load_json('institutional_data_hub/ETF_BTC_ETH_STATUS.json')
lab=load_json('lab/LAB_STATUS.json')

long_ok=(
    master.get('engine')=='ALT_ENGINE_MASTER_CHECKPOINT_v1.0'
    and master.get('production_universe')==ALTS
    and master.get('production_assets_count')==13
    and master.get('production_assets_ready')==13
    and master.get('full_zone_map')=='91/91'
    and master.get('not_execution_connected') is True
    and long_engine.get('engine')=='ALT_DECISION_ENGINE_v1.0'
    and long_engine.get('universe')==ALTS
    and long_engine.get('asset_count')==13
    and (long_engine.get('rules') or {}).get('execution_connected') is False
    and (long_engine.get('rules') or {}).get('no_zone_guessing') is True
    and (long_ready.get('summary') or {}).get('production_data_ready')==13
    and (long_ready.get('summary') or {}).get('production_with_full_zones')==13
)

zones_ok=(
    zones.get('ready_points')==91 and zones.get('total_points')==91
    and zones.get('assets_complete')==13 and zones.get('assets_total')==13
    and zones.get('percent')==100.0
)

tactical_ok=(
    tactical.get('engine')=='V8_TACTICAL_ENGINE_v1.0'
    and tactical.get('universe')==TACT
    and tactical.get('asset_count')==14
    and tactical.get('stocks_included') is False
    and tactical.get('not_execution_connected') is True
    and tactical_ready.get('asset_count')==14
    and tactical_ready.get('all_assets_ready') is True
    and tactical_ready.get('execution_connected') is False
    and tactical_ready.get('tradingview_connected') is False
)

etf_assets=etf.get('assets') or {}
etf_ok=(
    set(etf_assets)=={'BTC','ETH'}
    and (etf.get('safety') or {}).get('same_day_etf_values_are_provisional') is True
    and (etf.get('safety') or {}).get('closed_day_values_drive_scores') is True
    and exists('institutional_data_hub/ETF_BTC_ETH_HISTORY.csv')
    and exists('institutional_data_hub/ETF_PRICE_DIVERGENCE_LATEST.md')
)

lab_ok=(
    lab.get('fast_mode_ready') is True
    and lab.get('deep_mode_ready') is True
    and lab.get('polish_user_language') is True
    and exists('lab/LAB_CHECKPOINTS.csv')
    and exists('lab/LAB_DEEP_REPORT.json')
)

onchain_ok=exists('crypto_data_hub/ONCHAIN_ACTIVITY.json') or exists('onchain_data/ONCHAIN_ACTIVITY.json')
panel_ok=exists('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL.txt') and exists('google_sheets/DUAL_PANEL.csv') and exists('google_sheets/DUAL_ENGINE_MACHINE_ROOM.csv')
alarms_ok=exists('tactical_engine/TACTICAL_MACD_EXTREMES.csv') and exists('tactical_engine/TACTICAL_EXTREME_CONFLUENCE.csv') and tactical_ok
validation_ok=exists('tactical_validation/TACTICAL_VALIDATION.json') and exists('tactical_validation/TACTICAL_THRESHOLD_LAB.json')
safety_ok=(long_ok and tactical_ok and (etf.get('safety') or {}).get('execution_connected') is False)

areas=[
 ('SILNIK LONG — 13 ALTÓW',15,long_ok,'13 altów ma technikę, decyzję i pełne strefy 7/7.'),
 ('STREFY LONG — 91/91',15,zones_ok,'13 altów × 7 interwałów: 1D/2D/3D/4D/5D/1T/2T.'),
 ('SILNIK TACTICAL — BTC + 13 ALTÓW',15,tactical_ok,'14 aktywów na 1H/4H/1D, bez spółek.'),
 ('ETF BTC + ETH',10,etf_ok,'Dane zamknięte oddzielone od danych bieżącego dnia.'),
 ('LAB + PUNKTY KONTROLNE',10,lab_ok,'Szybka analiza i głęboka obserwacja.'),
 ('ON-CHAIN / FLOW',10,onchain_ok,'Warstwa kontekstowa; brak danych dla pojedynczego alta nie blokuje silnika.'),
 ('PANEL GOOGLE SHEETS',10,panel_ok,'Most i pliki panelu są obecne.'),
 ('ALARMY EKSTREMÓW',5,alarms_ok,'RSI/MFI/MACD/FOMO i zbieżność ekstremów.'),
 ('BEZPIECZEŃSTWO',5,safety_ok,'Brak automatycznego wykonywania transakcji; brak zgadywania stref.'),
 ('WALIDACJA / QA',5,validation_ok,'Walidacja TACTICAL i laboratorium progów są obecne.'),
]
score=sum(w for _,w,ok,_ in areas if ok)
status='WSZYSTKIE USTALONE ELEMENTY DOPIĘTE' if score==100 else 'SYSTEM WYMAGA JESZCZE PRACY'
blockers=[n for n,_,ok,_ in areas if not ok]

payload={
 'generated_at_utc':NOW,
 'engine':'V8_FINAL_READINESS_v2.0',
 'readiness_percent':score,
 'status_pl':status,
 'active_long_alts':ALTS,
 'long_assets_count':13,
 'tactical_universe':TACT,
 'tactical_assets_count':14,
 'full_zone_map':'91/91' if zones_ok else 'NIEPEŁNE',
 'aave_status':'ARCHIWUM — NIEAKTYWNE',
 'sui_status':'NIE WCHODZI DO USTALONEGO ZAKRESU',
 'tradingview_status':'ODŁOŻONE CELOWO — NIE WLICZA SIĘ DO GOTOWOŚCI V8',
 'areas':[{'obszar':n,'waga_pkt':w,'gotowe':ok,'opis':d} for n,w,ok,d in areas],
 'blockers':blockers,
 'safety':{'execution_connected':False,'never_invent_user_zones':True,'v7_not_modified':True},
}
(OUT/'V8_FINAL_READINESS.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')

rows=[['OBSZAR','WAGA_PKT','STATUS','OPIS']]
for n,w,ok,d in areas: rows.append([n,w,'GOTOWE' if ok else 'WYMAGA POPRAWY',d])
rows.append(['CAŁOŚĆ',100,f'{score}%',status])
with (GS/'V8_FINAL_READINESS.csv').open('w',newline='',encoding='utf-8') as f: csv.writer(f).writerows(rows)

md=['# V8 — KOŃCOWA GOTOWOŚĆ','',f'**Gotowość całego projektu: {score}%**',f'**Status: {status}**','','## Zakres końcowy',f'- LONG: **13 altów** — {", ".join(ALTS)}.',f'- TACTICAL: **BTC + 13 altów = 14 aktywów**.','- Strefy LONG: **91/91**.' if zones_ok else '- Strefy LONG: **NIEPEŁNE**.','- AAVE: **archiwum, nieaktywne**.','- SUI: **nie wchodzi do ustalonego zakresu**.','- TradingView: **celowo odłożone na później i niewliczane do procentu gotowości**.','','## Główne obszary']
for n,w,ok,d in areas: md.append(f"- {'✅' if ok else '⚠️'} **{n}** — {w} pkt — {'GOTOWE' if ok else 'WYMAGA POPRAWY'}. {d}")
if blockers:
    md += ['','## Do poprawy']+[f'- {x}' for x in blockers]
md += ['','Brak automatycznego wykonywania transakcji. System nie tworzy sztucznych stref. V7 pozostaje nietknięty.']
(OUT/'V8_FINAL_READINESS_LATEST.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
print(json.dumps({'readiness_percent':score,'status_pl':status,'blockers':blockers},ensure_ascii=False,indent=2))
if score!=100: raise SystemExit('Końcowa gotowość nie osiągnęła 100% — patrz blockers.')
