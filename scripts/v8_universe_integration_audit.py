import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

EXPECTED_TACTICAL=['BTC','ETH','SOL','LINK','ONDO','RENDER','FLOKI','PEPE','SPX6900','XRP','XLM','HBAR']
EXPECTED_LONG=['ETH','SOL','LINK','ONDO','RENDER','FLOKI','PEPE','SPX6900','XRP','XLM','HBAR']
REQ_TF=['1D','2D','3D','4D','5D','1T','2T']
OUT=Path('audit'); OUT.mkdir(exist_ok=True)


def loadj(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def main():
    tac=loadj('tactical_engine/TACTICAL_ENGINE.json')
    ready=loadj('tactical_engine/TACTICAL_READINESS.json')
    tech=loadj('crypto_data_hub/ALT_TECHNICAL_LAYER.json')
    long=loadj('crypto_data_hub/ALT_DECISION_ENGINE.json')
    tc=pd.read_csv('config/tactical_universe.csv')
    lc=pd.read_csv('config/alt_universe.csv')
    zones=pd.read_csv('config/alt_zones.csv')
    bridge=Path('google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL.txt').read_text(encoding='utf-8')

    tac_active=tc[tc['enabled'].astype(str).str.lower().eq('true')]['symbol'].astype(str).str.upper().tolist()
    long_active=lc[lc['enabled'].astype(str).str.lower().eq('true')]['symbol'].astype(str).str.upper().tolist()
    aave_tc=tc[tc['symbol'].astype(str).str.upper().eq('AAVE')]
    aave_lc=lc[lc['symbol'].astype(str).str.upper().eq('AAVE')]

    checks={}
    checks['tactical_universe_exact']=tac_active==EXPECTED_TACTICAL
    checks['long_universe_exact']=long_active==EXPECTED_TACTICAL
    checks['aave_archived_not_active']=(not aave_tc.empty and not aave_lc.empty and not aave_tc['enabled'].astype(str).str.lower().eq('true').any() and not aave_lc['enabled'].astype(str).str.lower().eq('true').any())
    checks['tactical_engine_v1']=tac.get('engine')=='V8_TACTICAL_ENGINE_v1.0'
    checks['tactical_12_ready']=(tac.get('asset_count')==12 and [a.get('symbol') for a in tac.get('assets',[])]==EXPECTED_TACTICAL and all(a.get('qa')=='PASS' for a in tac.get('assets',[])))
    checks['tactical_timeframes']=all(set((a.get('timeframes') or {}).keys())=={'1H','4H','1D'} for a in tac.get('assets',[]))
    checks['tactical_no_stocks']=tac.get('stocks_included') is False
    checks['tactical_no_execution']=tac.get('not_execution_connected') is True
    checks['tradingview_deferred']=tac.get('rules',{}).get('tradingview_connected') is False
    checks['readiness_12']=ready.get('all_assets_ready') is True and ready.get('asset_count')==12
    checks['long_technical_11']=(tech.get('engine')=='ALT_TECHNICAL_LAYER_v1.0' and tech.get('asset_count')==11 and [a.get('symbol') for a in tech.get('assets',[])]==EXPECTED_LONG and all(a.get('qa')=='PASS' for a in tech.get('assets',[])))
    checks['long_decisions_11']=(long.get('engine')=='ALT_DECISION_ENGINE_v1.0' and long.get('asset_count')==11 and long.get('universe')==EXPECTED_LONG and all(a.get('technical_ready') is True for a in long.get('assets',[])))
    checks['long_no_execution']=long.get('rules',{}).get('execution_connected') is False
    checks['no_buy_with_blocker']=all((not a.get('decision','').startswith('KUP')) or (not a.get('blockers') and not a.get('entry_blockers') and a.get('zones',{}).get('complete_7_of_7') is True) for a in long.get('assets',[]))

    alarm_tokens=['buildExtremeAlarms_','[\'1H\',\'4H\',\'1D\']','rsi14','mfi14','macd_hist_percentile','macd_hist_zscore','fomo_score_0_10','MailApp.sendEmail','EMAIL_ALERTY','EMAIL_DO']
    checks['sheet_alarm_and_email_support']=all(x in bridge for x in alarm_tokens)

    zones['symbol']=zones['symbol'].astype(str).str.upper(); zones['timeframe']=zones['timeframe'].astype(str).str.upper(); zones['source_status']=zones['source_status'].astype(str).str.upper()
    zone_status={}
    for sym in EXPECTED_LONG:
        z=zones[(zones['symbol']==sym)&(zones['source_status']=='CONFIRMED')]
        present=sorted(set(z['timeframe']))
        missing=[tf for tf in REQ_TF if tf not in present]
        zone_status[sym]={'complete_7_of_7':len(missing)==0,'confirmed_timeframes':present,'missing_timeframes':missing}

    core_pass=all(checks.values())
    missing_zone_assets=[s for s,v in zone_status.items() if not v['complete_7_of_7']]
    payload={
        'generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'engine':'V8_UNIVERSE_INTEGRATION_AUDIT_v1.0',
        'integration_status_pl':'OBA SILNIKI PODŁĄCZONE I SPRAWDZONE' if core_pass else 'INTEGRACJA WYMAGA POPRAWY',
        'core_checks_pass':core_pass,
        'checks':checks,
        'tactical':{'asset_count':12,'assets':EXPECTED_TACTICAL,'timeframes':['1H','4H','1D'],'stocks_included':False,'tradingview_connected':False,'execution_connected':False},
        'long':{'alt_count':11,'alts':EXPECTED_LONG,'btc_role':'REŻIM RYNKU','stocks_role':'OSOBNA CZĘŚĆ LONG','technical_assets_ready':11,'execution_connected':False},
        'alerts':{'google_sheets_panel':checks['sheet_alarm_and_email_support'],'email_supported_by_bridge':checks['sheet_alarm_and_email_support'],'tradingview':'PÓŹNIEJ'},
        'zones':zone_status,
        'assets_missing_full_user_zones':missing_zone_assets,
        'important_note_pl':'Brak stref nie wyłącza monitoringu wskaźników TACTICAL. W LONG blokuje pełną decyzję do czasu potwierdzenia mapy 7/7.',
        'aave':'ARCHIWUM — NIEAKTYWNY',
    }
    (OUT/'V8_UNIVERSE_INTEGRATION_AUDIT.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')

    md=[
        '# V8 — INTEGRACJA OBU SILNIKÓW','',
        f"**{payload['integration_status_pl']}**",'',
        '## TACTICAL',
        '- 12 aktywów: BTC + 11 altów.',
        '- Interwały: 1H / 4H / 1D.',
        '- Spółki: NIE.',
        '- RSI / MFI / MACD / FOMO: aktywne dla całej listy.',
        '- Alarm panelu + obsługa e-mail: GOTOWE po włączeniu ustawienia e-mail w arkuszu.',
        '- TradingView: później.','',
        '## LONG',
        '- BTC: reżim rynku.',
        '- 11 altów: podłączonych do techniki i warstwy decyzji.',
        '- Spółki: pozostają osobną częścią LONG.',
        '- Brak pełnych stref 7/7 nie usuwa aktywa, ale blokuje pełną decyzję LONG.','',
        '## STREFY'
    ]
    for s in EXPECTED_LONG:
        v=zone_status[s]
        md.append(f"- {s}: {'7/7 GOTOWE' if v['complete_7_of_7'] else 'BRAKUJE ' + ', '.join(v['missing_timeframes'])}")
    md += ['', 'AAVE: ARCHIWUM — NIEAKTYWNY.', 'Brak połączenia z wykonywaniem transakcji.']
    (OUT/'V8_UNIVERSE_INTEGRATION_LATEST.md').write_text('\n'.join(md),encoding='utf-8')
    if not core_pass:
        bad=[k for k,v in checks.items() if not v]
        raise SystemExit('Nieudane kontrole: '+', '.join(bad))
    print(json.dumps({'status':payload['integration_status_pl'],'checks':checks,'missing_zone_assets':missing_zone_assets},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
