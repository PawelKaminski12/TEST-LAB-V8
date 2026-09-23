# V8 TACTICAL — BRAMKA KALIBRACJI

Status: **PASS_DO_BADAN_DALSZYCH__DEPLOY_HOLD**

## Wynik
- QA danych: PASS
- Minimalna liczba obserwacji: PASS
- TRAIN: FAIL
- HOLDOUT: PASS
- Spójność między aktywami produkcyjnymi: FAIL
- Flaga niestabilności reżimu: TAK

## Kandydat badawczy
- score_min = 6
- fomo_max = 7
- trend4_min = 3
- RSI = 50–70
- TRAIN mean 12h = -0.1879% | win = 44.35%
- HOLDOUT mean 12h = 1.2534% | win = 61.54%

## Decyzja
**NIE ZMIENIAĆ PRODUKCYJNYCH PROGÓW**

Powody:
- Próbka TRAIN nie spełnia minimalnego dodatniego profilu
- Wynik HOLDOUT jest dodatni przy ujemnym TRAIN — ryzyko niestabilności reżimu / selekcji próbki
- Spójność między aktywami produkcyjnymi jest niewystarczająca

Ta bramka nie modyfikuje SILNIK_TACTICAL, panelu, progów produkcyjnych ani AUTO EXECUTION.
