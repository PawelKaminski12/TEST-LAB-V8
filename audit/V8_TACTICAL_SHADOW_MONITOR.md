# V8 TACTICAL — SHADOW MONITOR KANDYDATA

Status: **AKTYWNY BADAWCZO — DEPLOY HOLD**

- Snapshot silnika: 2026-09-23T20:28:22.554038+00:00
- Alty monitorowane: 13
- Shadow PASS teraz: 3
- Produkcyjne pozytywne statusy teraz: 0
- Rozbieżności shadow vs produkcja: 3

## Kandydat
- score >= 6
- FOMO 1H i 4H <= 7
- trend 4H >= 3
- RSI 4H = 50–70

## Zabezpieczenia
- research_only = true
- deploy_block = true
- AUTO EXECUTION = OFF
- Produkcyjne progi Tactical nie są modyfikowane.
- Wyniki shadow są zapisywane osobno i służą tylko do dalszej walidacji.

## Bieżące sygnały shadow
- ETH: HOLD | prod=WATCH_SUPPLY | blokady: rsi4
- SOL: PASS | prod=WATCH_SUPPLY | warunki kandydata spełnione
- LINK: HOLD | prod=WATCH_SUPPLY | blokady: score,trend4,rsi4
- ONDO: HOLD | prod=NO_TRADE | blokady: score,rsi4
- RENDER: PASS | prod=WAIT | warunki kandydata spełnione
- FLOKI: HOLD | prod=WAIT | blokady: rsi4
- PEPE: HOLD | prod=WATCH_SUPPLY | blokady: rsi4
- SPX6900: HOLD | prod=NO_TRADE | blokady: score,trend4,rsi4
- XRP: HOLD | prod=WATCH_SUPPLY | blokady: rsi4
- XLM: HOLD | prod=WAIT | blokady: rsi4
- HBAR: PASS | prod=WATCH_SUPPLY | warunki kandydata spełnione
- AVAX: HOLD | prod=WATCH_SUPPLY | blokady: rsi4
- AWE: HOLD | prod=NO_TRADE | blokady: score,trend4,rsi4
