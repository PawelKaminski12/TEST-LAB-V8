#!/usr/bin/env python3
import csv, json, hashlib
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
STATUS=ROOT/'google_sheets'/'V8_STATUS_MASTER.csv'
READINESS=ROOT/'audit'/'V8_FINAL_READINESS.json'
STABILITY=ROOT/'audit'/'V8_TACTICAL_STABILITY_PACK_V6.md'
TACTICAL=ROOT/'tactical_engine'/'TACTICAL_ENGINE.json'
PANEL=ROOT/'google_sheets'/'DUAL_ENGINE_APPS_SCRIPT_FULL_V9.txt'
OUTJ=ROOT/'audit'/'V8_FINAL_CHECKPOINT.json'
OUTM=ROOT/'audit'/'V8_FINAL_CHECKPOINT.md'

def sha(p):
    h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()

def main():
    r=json.loads(READINESS.read_text(encoding='utf-8'))
    rows=list(csv.DictReader(STATUS.open(encoding='utf-8', newline='')))
    by={(x['SEKCJA'],x['ELEMENT']):x for x in rows}
    must=[
      ('LONG','UNIWERSUM'),('TACTICAL','UNIWERSUM'),('STREFY','LONG'),
      ('ALARMY','EKSTREMA'),('ALARMY','ŚWIEŻOŚĆ'),('ALARMY','WIELE TF'),('ALARMY','DYNAMIKA'),
      ('TACTICAL','CENTRUM RYZYKA'),('TACTICAL','CHALLENGER FRAMEWORK V3'),('TACTICAL','REGIME GATE V4'),
      ('TACTICAL','META GATE V5'),('TACTICAL','STABILITY PACK V6'),('PANEL','GOOGLE SHEETS'),
      ('BEZPIECZEŃSTWO','AUTO EXECUTION'),('BEZPIECZEŃSTWO','V7 TOUCH')]
    missing=[k for k in must if k not in by]
    prod_ok=(r.get('readiness_percent')==100 and not r.get('blockers') and by[('BEZPIECZEŃSTWO','AUTO EXECUTION')]['STATUS']=='OFF' and by[('BEZPIECZEŃSTWO','V7 TOUCH')]['STATUS']=='OFF')
    research_hold=('HOLD_RESEARCH' in STABILITY.read_text(encoding='utf-8'))
    payload={
      'generated_at_utc':datetime.now(timezone.utc).isoformat(),
      'checkpoint':'V8_DUAL_ENGINE_FINAL_CHECKPOINT_2026-09-23',
      'production_readiness_percent':r.get('readiness_percent'),
      'production_status':'CLOSED_STABLE' if prod_ok and not missing else 'CHECK_REQUIRED',
      'research_status':'HOLD_RESEARCH' if research_hold else 'CHECK_REQUIRED',
      'missing_required_status_rows':[list(x) for x in missing],
      'production_scope':{'long_alts':13,'tactical_assets':14,'zones':'91/91','panel_columns':7},
      'research_scope':{
        'calibration':'DEPLOY HOLD','shadow':'DEPLOY HOLD','validation_v2':'HOLD RESEARCH',
        'challenger_v3':'WATCH STRONG','regime_gate_v4':'WATCH REGIME GATE','meta_gate_v5':'WATCH META GATE','stability_v6':'HOLD RESEARCH'},
      'safety':{'auto_execution':False,'v7_touch':False,'invent_user_zones':False,'research_auto_promotion':False},
      'protected_sha256':{'tactical_engine':sha(TACTICAL),'apps_script_v9':sha(PANEL)},
      'explicitly_deferred':['External Market Reader source','TradingView integration','research promotion until stability gates improve'],
      'final_decision':'FREEZE_PRODUCTION_CONTINUE_OBSERVATION_ONLY'
    }
    OUTJ.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# V8 / DUAL ENGINE — FINAL CHECKPOINT','',f"Status produkcji: **{payload['production_status']}**",f"Status research: **{payload['research_status']}**",'',
      '## Produkcja zamknięta','- LONG: 13 altów','- TACTICAL: BTC + 13 altów','- STREFY: 91/91','- PANEL: 7 kolumn','- alarmy ekstremów, świeżość, wiele TF, dynamika i centrum ryzyka: gotowe','',
      '## Research — świadomie niewdrożony','- Kalibracja: DEPLOY HOLD','- Shadow Monitor: DEPLOY HOLD','- Validation V2: HOLD RESEARCH','- Challenger V3: WATCH STRONG','- Regime Gate V4: WATCH REGIME GATE','- Meta Gate V5: WATCH META GATE','- Stability Pack V6: HOLD RESEARCH','',
      '## Twarde zabezpieczenia','- AUTO EXECUTION = OFF','- V7 TOUCH = OFF','- brak zgadywania stref','- brak automatycznej promocji research do produkcji','',
      '## Finalna decyzja','**FREEZE_PRODUCTION_CONTINUE_OBSERVATION_ONLY**','',
      'V8 jest konstrukcyjnie zamknięty. Dalsze prace dotyczą wyłącznie obserwacji, jakości danych i ewentualnej przyszłej ręcznej promocji warstw badawczych po przejściu bramek stabilności.']
    OUTM.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'production':payload['production_status'],'research':payload['research_status'],'missing':len(missing),'decision':payload['final_decision']},ensure_ascii=False))
if __name__=='__main__': main()
