# V8 TACTICAL — REGIME GATE V4

Status: **WATCH_REGIME_GATE**

## Kontrakt bezpieczeństwa
- research_only = true
- deploy_block = true
- AUTO EXECUTION = OFF
- produkcyjny Tactical i panel V9 pozostają nietknięte

## Challenger pod bramką: BALANCED_LOW_FOMO
- reguła: {'score_min': 6, 'fomo_max': 6, 'trend4_min': 3, 'rsi_lo': 45, 'rsi_hi': 68}

## Wynik bez bramki
- n=342 | 12h=0.143% | win=50.29% | 24h=0.224%

## Wyniki wg reżimu bramki
- ACTIVE: n=307 | 12h=0.140% | win=51.79% | 24h=0.267% | LCB12=0.014%
- CAUTION: n=17 | 12h=0.666% | win=41.18% | 24h=0.370% | LCB12=0.165%
- BLOCK: n=18 | 12h=-0.294% | win=33.33% | 24h=-0.637% | LCB12=-0.609%

## Bramki walidacyjne
- active_n_ge_100: PASS
- active_mean12_beats_ungated: FAIL
- active_win12_not_worse: PASS
- active_mean24_positive: PASS
- active_lcb12_positive: PASS
- block_underperforms_active: PASS
- active_temporal_no_deep_failure: FAIL

## Aktualny Gate
- status: **ACTIVE**
- breadth 1D: 100.00%
- breadth 4H: 76.92%
- FOMO>=8 share: 0.00%
- BTC trend 1D/4H: 4.0 / 4.0
- powód: breadth=ACTIVE; BTC potwierdza 1D+4H

## Aktualne wyniki gated shadow
- ETH: PASS_GATE_ACTIVE | challenger=PASS | prod=WATCH_SUPPLY
- SOL: PASS_GATE_ACTIVE | challenger=PASS | prod=WATCH_SUPPLY
- LINK: HOLD_CHALLENGER | challenger=HOLD | prod=WATCH_SUPPLY
- ONDO: HOLD_CHALLENGER | challenger=HOLD | prod=NO_TRADE
- RENDER: PASS_GATE_ACTIVE | challenger=PASS | prod=WAIT
- FLOKI: PASS_GATE_ACTIVE | challenger=PASS | prod=WAIT
- PEPE: PASS_GATE_ACTIVE | challenger=PASS | prod=WATCH_SUPPLY
- SPX6900: HOLD_CHALLENGER | challenger=HOLD | prod=NO_TRADE
- XRP: PASS_GATE_ACTIVE | challenger=PASS | prod=WATCH_SUPPLY
- XLM: PASS_GATE_ACTIVE | challenger=PASS | prod=WAIT
- HBAR: PASS_GATE_ACTIVE | challenger=PASS | prod=WATCH_SUPPLY
- AVAX: PASS_GATE_ACTIVE | challenger=PASS | prod=WATCH_SUPPLY
- AWE: HOLD_CHALLENGER | challenger=HOLD | prod=NO_TRADE

## Decyzja
**WATCH_REGIME_GATE**

Nawet pozytywna walidacja bramki nie wdraża jej do produkcji. Wymagany jest osobny ręczny krok i pełny audyt.
