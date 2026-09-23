# V8 DUAL ENGINE — GOOGLE SHEETS PANEL SPEC

## Cel
Jeden skoroszyt Google Sheets jako centrum dowodzenia dla dwóch niezależnych portfeli i dwóch niezależnych silników:

- LONG PORTFEL / LONG ENGINE — spokojne, średnio- i długoterminowe decyzje.
- TACTICAL PORTFEL / TACTICAL ENGINE — krótkie ruchy 1H / 4H / 1D.

Zasada nadrzędna: SILNIK = MASZYNOWNIA, PANEL = KRÓTKA DECYZJA.

## Zakładki
1. PANEL
2. PORTFEL_LONG
3. PORTFEL_TACTICAL
4. SILNIK_LONG
5. SILNIK_TACTICAL
6. MARKET_READER
7. HISTORIA
8. USTAWIENIA

## PANEL — minimalny widok
Kolumny:
- AKTYWO
- CENA
- LONG
- TACTICAL
- RYZYKO
- ZGODNOŚĆ
- ALERT

Nie pokazujemy w PANELU MACD, RSI, ATR, FOMO, stref, punktacji, przepływów, rotacji i szczegółów Market Reader. Te dane zostają w maszynowni.

### Przykład
| AKTYWO | CENA | LONG | TACTICAL | RYZYKO | ZGODNOŚĆ | ALERT |
|---|---:|---|---|---:|---|---|
| ETH |  | CZEKAJ | WAIT | 5/10 | NEUTRAL |  |
| SOL |  | CZEKAJ | LONG_SETUP_WATCH | 5/10 | TACTICAL ONLY |  |
| LINK |  | SPRAWDŹ | WAIT | 5/10 | NEUTRAL |  |
| ONDO |  | CZEKAJ | WAIT | 5/10 | NEUTRAL |  |

## PORTFEL_LONG
Tylko pozycje długoterminowe. Minimalne dane użytkowe:
- AKTYWO
- ILOŚĆ
- ŚR. CENA
- WARTOŚĆ
- ZYSK/STRATA
- DCA1
- DCA2
- DCA3
- STATUS LONG
- POTWIERDZONE WYKONANIE

## PORTFEL_TACTICAL
Osobna pula kapitału. Nie mieszać pozycji z LONG.
Kolumny:
- AKTYWO
- ILOŚĆ
- CENA WEJŚCIA
- WARTOŚĆ
- P&L
- STATUS TACTICAL
- RYZYKO 0–10
- PLAN WYJŚCIA
- WYKONANE

## SILNIK_LONG — maszynownia
Źródło: crypto_data_hub/ALT_ENGINE_MASTER_CHECKPOINT.json + warstwy V8.
Może zawierać dużą liczbę kolumn i danych pomocniczych.
Rdzeń widoczny wewnątrz:
- data quality
- strefy 1D–2T
- trend
- FOMO
- rotation
- market phase
- DCA1/2/3
- final decision
- blockers

## SILNIK_TACTICAL — maszynownia
Źródło: tactical_engine/TACTICAL_ENGINE.json + TACTICAL_READINESS.json + TACTICAL_CONFLUENCE.csv.
Warstwy:
- 1H timing
- 4H decision
- 1D regime
- MACD
- RSI
- wolumen
- ATR
- breakout/retest
- FOMO
- higher-timeframe zones context
- Market Reader second-eye
- exit risk
- tactical score
- tactical status

## MARKET_READER
Dane z zewnętrznego programu tylko jako potwierdzenie.
Nigdy nie nadpisują twardych blokad wewnętrznego silnika.

## ZGODNOŚĆ — logika na PANELU
- 2/2 POSITIVE — oba silniki wspierają dodawanie/pozycję w swoim horyzoncie.
- TACTICAL ONLY — tylko silnik krótkoterminowy widzi setup.
- LONG ONLY — tylko silnik długoterminowy widzi okazję.
- NEUTRAL — brak mocnego sygnału.
- CONFLICT — kierunki są rozbieżne i wymagają uwagi.

ZGODNOŚĆ nie jest sygnałem wykonawczym. To skrót informacyjny.

## Odświeżanie
Jeden przycisk ODŚWIEŻ_WSZYSTKO ma kolejno:
1. pobrać CORE/LONG,
2. pobrać TACTICAL,
3. pobrać MARKET_READER jeśli dostępny,
4. zaktualizować oba portfele,
5. przeliczyć PANEL,
6. dopisać jeden rekord do HISTORIA tylko po zmianie statusu lub na zamknięciu cyklu.

## Zasady bezpieczeństwa
- LONG i TACTICAL mają osobne pule kapitału.
- Brak automatycznych transakcji.
- Status silnika to status badawczy/decyzyjny, nie zlecenie giełdowe.
- Brak synchronizacji ilości między portfelami.
- V7 produkcyjny pozostaje nietknięty.
- Dane maszynowni nie rozrastają głównego PANELU.

## Status projektu
Specyfikacja integracji Google Sheets gotowa. Implementacja Apps Script następuje dopiero po zamrożeniu układu danych wejściowych obu silników.
