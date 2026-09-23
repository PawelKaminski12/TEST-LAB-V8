# V8 TACTICAL — VALIDATION FRAMEWORK 2.0

Status: **HOLD_RESEARCH**

## Kontrakt bezpieczeństwa
- research_only = true
- deploy_block = true
- AUTO EXECUTION = OFF
- brak automatycznej zmiany progów produkcyjnych
- dane historyczne bez projekcji bieżących stref wstecz

## Kandydat
- score >= 6
- FOMO 1H/4H <= 7
- trend 4H >= 3
- RSI 4H = 50–70

## Wynik łączny
- n = 325
- mean 12h = 0.232%
- win 12h = 49.85%
- mean 24h = 0.371%

## Stabilność per aktywo
- ETH: n=94 | 12h=0.086% | win=48.94% | 24h=-0.038%
- LINK: n=78 | 12h=0.232% | win=53.85% | 24h=0.349%
- ONDO: n=73 | 12h=0.165% | win=52.05% | 24h=0.231%
- SOL: n=80 | 12h=0.465% | win=45.00% | 24h=1.002%

## Reżimy rynku
- BULL: n=307 | 12h=0.213% | win=49.19% | 24h=0.295%
- MIXED: n=18 | 12h=0.559% | win=61.11% | 24h=1.669%

## Stabilność czasowa
- Q1: n=102 | 12h=-0.051% | win=46.08% | 24h=-0.205%
- Q2: n=79 | 12h=-0.167% | win=48.10% | 24h=0.065%
- Q3: n=69 | 12h=-0.565% | win=30.43% | 24h=-1.295%
- Q4: n=75 | 12h=1.770% | win=74.67% | 24h=3.011%

## Bramka promocji
- minimum_candidate_observations: PASS
- overall_mean12_positive: PASS
- overall_win12_min_53: FAIL
- overall_mean24_positive: PASS
- all_production_assets_positive_mean12: PASS
- temporal_blocks_stable: FAIL
- regime_coverage: PASS
- regime_stability: PASS
- production_baseline_comparison: PASS

## Decyzja
**HOLD_RESEARCH**

Nawet status PROMOTE_CANDIDATE nie może automatycznie zmienić produkcji. Wymagany jest osobny ręczny krok i ponowny audyt.
