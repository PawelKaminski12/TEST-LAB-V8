# V8 TACTICAL — META GATE V5

Status: **WATCH_META_GATE**

## Bezpieczeństwo
- research_only = true
- deploy_block = true
- AUTO EXECUTION = OFF
- produkcyjny Tactical i Apps Script V9 pozostają nietknięte

## Challenger: BALANCED_LOW_FOMO
- reguła: {'score_min': 6, 'fomo_max': 6, 'trend4_min': 3, 'rsi_lo': 45, 'rsi_hi': 68}

## Metoda
- łączy Challenger V3 + Regime Gate V4 + warstwę ryzyka
- historia: risk proxy z production status / FOMO / RSI / trend
- bieżąco: dodatkowo exit_risk, strefy i extreme_confluence z Tactical Engine

## Wynik historyczny challengera bez meta-gate
- n=342 | 12h=0.143% | win=50.29% | 24h=0.224%

## Wyniki wg decyzji Meta Gate
- ALLOW: n=302 | 12h=0.140% | win=51.99% | 24h=0.285% | LCB12=0.013%
- CAUTION: n=22 | 12h=0.544% | win=40.91% | 24h=0.095% | LCB12=0.113%
- BLOCK: n=18 | 12h=-0.294% | win=33.33% | 24h=-0.637% | LCB12=-0.609%
- HOLD_CHALLENGER: n=426 | 12h=0.387% | win=54.93% | 24h=0.730% | LCB12=0.262%

## Bramki walidacyjne
- allow_n_ge_100: PASS
- allow_mean12_positive: PASS
- allow_mean24_positive: PASS
- allow_lcb12_positive: PASS
- allow_win_not_worse_than_ungated: PASS
- allow_mean12_beats_ungated: FAIL
- block_underperforms_allow: PASS
- allow_temporal_no_deep_failure: FAIL

## Bieżący Meta Gate
- reżim rynku: **ACTIVE**
- ALLOW: 0
- CAUTION: 5
- BLOCK: 4
- HOLD_CHALLENGER: 4

- ETH: CAUTION | risk=2 | prod=WATCH_SUPPLY | exit risk>=4; status SUPPLY
- SOL: CAUTION | risk=2 | prod=WATCH_SUPPLY | exit risk>=4; status SUPPLY
- LINK: HOLD_CHALLENGER | risk=2 | prod=WATCH_SUPPLY | exit risk>=4; status SUPPLY
- ONDO: HOLD_CHALLENGER | risk=6 | prod=NO_TRADE | exit risk>=4; status NO_TRADE; przegrzanie ekstremalne
- RENDER: BLOCK | risk=5 | prod=WAIT | exit risk>=4; FOMO>=6; przegrzanie ekstremalne
- FLOKI: CAUTION | risk=2 | prod=WAIT | exit risk>=4; FOMO>=6
- PEPE: BLOCK | risk=8 | prod=WATCH_SUPPLY | exit risk>=4; status SUPPLY; FOMO>=8; przegrzanie ekstremalne
- SPX6900: HOLD_CHALLENGER | risk=4 | prod=NO_TRADE | exit risk>=6; status NO_TRADE
- XRP: CAUTION | risk=2 | prod=WATCH_SUPPLY | exit risk>=4; status SUPPLY
- XLM: CAUTION | risk=1 | prod=WAIT | exit risk>=4
- HBAR: BLOCK | risk=8 | prod=WATCH_SUPPLY | exit risk>=4; status SUPPLY; FOMO>=8; przegrzanie ekstremalne
- AVAX: BLOCK | risk=8 | prod=WATCH_SUPPLY | exit risk>=4; status SUPPLY; FOMO>=8; przegrzanie ekstremalne
- AWE: HOLD_CHALLENGER | risk=3 | prod=NO_TRADE | exit risk>=4; status NO_TRADE

## Decyzja
**WATCH_META_GATE**

Meta Gate V5 pozostaje warstwą badawczą. Nawet pozytywna walidacja nie zmienia produkcji automatycznie.
