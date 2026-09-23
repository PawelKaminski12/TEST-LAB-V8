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
6. PRZEPLYWY
7. MARKET_READER
8. ALARMY_EKSTREMOW
9. HISTORIA
10. USTAWIENIA

## PANEL — minimalny widok po polsku
Kolumny:
- AKTYWO
- CENA
- LONG
- TACTICAL
- RYZYKO 0–10
- ZGODNOŚĆ
- ALERT

Panel użytkownika ma pokazywać statusy po polsku. Wewnętrzne statusy repozytorium mogą pozostać techniczne/angielskie.

Przykładowe tłumaczenia TACTICAL:
- WAIT → CZEKAJ
- NO_TRADE → NIE GRAJ
- NO_TRADE_FOMO → NIE GRAJ — FOMO
- WATCH_SUPPLY → OBSERWUJ PODAŻ
- WATCH_BREAKOUT → OBSERWUJ WYBICIE
- LONG_SETUP_WATCH → LONG — OBSERWUJ SETUP
- LONG_SETUP_RETEST → LONG — RETEST
- TAKE_PROFIT_WATCH → OBSERWUJ REALIZACJĘ ZYSKU
- EXIT_RISK_HIGH → WYSOKIE RYZYKO WYJŚCIA

Główny PANEL pozostaje kompaktowy. MACD, RSI, MFI, ATR, FOMO, strefy, punktacja, przepływy, rotacja i szczegóły Market Reader są dostępne w maszynowni, PRZEPLYWY oraz alarmach.

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
Źródło: `crypto_data_hub/ALT_ENGINE_MASTER_CHECKPOINT.json` + warstwy V8.
Rdzeń:
- jakość danych
- strefy 1D–2T
- trend
- FOMO
- rotacja
- faza rynku
- FLOW LONG 0–10
- ocena przepływu
- bezpośredni ETF 5D / 20D / 30D, jeśli istnieje dla danego aktywa
- DCA1/2/3
- decyzja końcowa
- blokady

FLOW LONG ma horyzont 20D / 30D i mierzy trwałość kapitału. Jest warstwą potwierdzającą, nie samodzielnym sygnałem KUP.

## SILNIK_TACTICAL — maszynownia
Źródło: `tactical_engine/TACTICAL_ENGINE.json` + `TACTICAL_READINESS.json` + `CRYPTO_MARKET_PHASE.json` + `TACTICAL_CONFLUENCE.csv`.

Warstwy:
- 1H timing
- 4H decision
- 1D regime
- MACD
- RSI
- MFI(14)
- wolumen
- ATR
- breakout/retest
- FOMO
- kontekst stref wyższego interwału
- Market Reader jako second-eye
- exit risk
- tactical score
- tactical status
- ekstrema 1H / 4H / 1D
- FLOW TACTICAL 0–5

FLOW TACTICAL ma horyzont 1D / 5D / 7D i ma pokazywać przyspieszenie przepływu. Jest potwierdzeniem, nie triggerem wejścia.

MFI nie jest samodzielnym sygnałem kupna/sprzedaży. Działa jako warstwa potwierdzenia i wykrywania skrajności razem z RSI, MACD, FOMO, trendem i strefami.

## PRZEPLYWY
Widoczna zakładka użytkowa dla przepływów i rotacji kapitału.

Pokazuje:
- ETH/BTC — zmiana 5D i 20D,
- BTC.D — poziom oraz zmianę, gdy historia jest dojrzała,
- ETH.D,
- OTHERS/BTC EQ — trend 5D / 20D po zbudowaniu odpowiedniej historii,
- stablecoin liquidity — 7D / 14D / 30D,
- BTC ETF — 5D / 20D / 30D,
- ETH ETF — 5D / 20D / 30D,
- SOL ETF — 5D / 20D / 30D,
- LONG FLOW score,
- TACTICAL FLOW score.

Źródła danych:
- Binance Vision — ceny i relacje ETH/BTC oraz ALT/BTC/ETH,
- CoinGecko — dominacje i odpowiedniki TOTAL3 / OTHERS,
- DefiLlama — płynność stablecoinów,
- Farside Investors przez operacyjny mirror — ETF flows.

Ważne ograniczenie: `V8_TOTAL3_EQ` i `V8_OTHERS_BTC_EQ` są odpowiednikami liczonymi z CoinGecko i nie są jeszcze certyfikowane jako 1:1 z TradingView TOTAL3/OTHERS.

## MFI — zatwierdzona logika ekstremów
MFI liczymy automatycznie na zamkniętych świecach dla 1H / 4H / 1D.

Poziomy:
- 80–90 → wykupienie / ostrzeżenie
- >= 90 → skrajne wykupienie
- 10–20 → wyprzedanie / ostrzeżenie
- <= 10 → skrajne wyprzedanie

Znaczenie interwałów:
- 1H — szybkie lokalne przegrzanie/wyprzedanie; najniższa waga,
- 4H — główny interwał decyzji TACTICAL; wysoka waga,
- 1D — rzadsze, ale najważniejsze skrajności; najwyższy kontekst.

## ALARMY_EKSTREMOW
Osobna zakładka użytkowa. Alarm jest informacyjny i nie wykonuje transakcji.

Źródła alarmów:
- RSI,
- MFI,
- MACD względny do własnej historii aktywa,
- FOMO.

Domyślne progi RSI/FOMO:
- RSI wykupienie: RSI >= 75
- RSI wyprzedanie: RSI <= 25
- FOMO HARD BLOCK: FOMO >= 8

Domyślne progi MFI:
- ostrzeżenie górne: 80
- skrajne górne: 90
- ostrzeżenie dolne: 20
- skrajne dolne: 10

MACD jest oceniany względnie do własnej historii aktywa, a nie przez jeden surowy próg wspólny dla ETH/SOL/LINK/ONDO.

Interwały:
- 1H
- 4H
- 1D

Kolumny:
- AKTYWNY
- AKTYWO
- INTERWAŁ
- TYP
- RSI
- MFI
- MACD %
- MACD Z
- FOMO
- WAGA
- CZAS DANYCH

Nowy alarm jest dopisywany do HISTORIA. Przy odświeżeniu pojawia się toast w Google Sheets. Opcjonalny e-mail może zostać aktywowany w USTAWIENIA.

## USTAWIENIA alarmów
- ALARMY_EKSTREMOW = ON/OFF
- RSI_GORNY = 75
- RSI_DOLNY = 25
- FOMO_TWARDY = 8
- MFI_GORNY_OSTRZEZENIE = 80
- MFI_GORNY_SKRAJNY = 90
- MFI_DOLNY_OSTRZEZENIE = 20
- MFI_DOLNY_SKRAJNY = 10
- EMAIL_ALERTY = ON/OFF
- EMAIL_DO = adres docelowy

## MARKET_READER
Dane z zewnętrznego programu tylko jako potwierdzenie.
Nigdy nie nadpisują twardych blokad wewnętrznego silnika.

## ZGODNOŚĆ — logika na PANELU
- 2/2 POZYTYWNE — oba silniki wspierają pozycję w swoim horyzoncie.
- TYLKO TACTICAL — tylko silnik krótkoterminowy widzi setup.
- TYLKO LONG — tylko silnik długoterminowy widzi okazję.
- NEUTRALNIE — brak mocnego sygnału.
- KONFLIKT — kierunki są rozbieżne i wymagają uwagi.

ZGODNOŚĆ nie jest sygnałem wykonawczym. To skrót informacyjny.

## Odświeżanie
Jeden przycisk `ODŚWIEŻ_WSZYSTKO` kolejno:
1. pobiera CORE/LONG,
2. pobiera TACTICAL,
3. pobiera MARKET PHASE + ETF / stablecoin / rotację,
4. pobiera MARKET_READER jeśli dostępny,
5. odświeża maszynownię LONG i TACTICAL,
6. odświeża PRZEPLYWY,
7. przelicza polski PANEL,
8. skanuje RSI / MFI / MACD / FOMO na 1H / 4H / 1D,
9. zapisuje nowe alarmy do HISTORIA,
10. opcjonalnie wysyła e-mail,
11. aktualizuje znacznik czasu.

Dodatkowa komenda `SPRAWDŹ EKSTREMA` wykonuje sam skan ekstremów bez pełnego odświeżania panelu.

## Zasady bezpieczeństwa
- LONG i TACTICAL mają osobne pule kapitału.
- Brak automatycznych transakcji.
- Status silnika to status badawczy/decyzyjny, nie zlecenie giełdowe.
- Brak synchronizacji ilości między portfelami.
- V7 produkcyjny pozostaje nietknięty.
- Market Reader nie może nadpisywać twardych blokad.
- ETF / stablecoin / ETH-BTC / OTHERS-BTC są warstwą potwierdzającą, nie automatycznym sygnałem KUP.
- RSI/MFI/MACD/FOMO ekstremum nie jest automatycznie sygnałem sprzedaży ani zakupu.
- Dane maszynowni nie rozrastają głównego PANELU.

## Status projektu
Warstwa panelu i integracji Google Sheets jest domknięta funkcjonalnie dla: LONG + TACTICAL, polskiego widoku użytkownika, oddzielnych portfeli, historii, alarmów ekstremów RSI/MFI/MACD/FOMO oraz osobnej zakładki PRZEPLYWY z ETF / stablecoin / ETH-BTC / OTHERS-BTC.

Kalibracja progów strategii TACTICAL pozostaje osobnym etapem badawczym. Nie wolno oznaczać jej jako zamrożonej strategii wykonawczej wyłącznie na podstawie pojedynczego holdoutu.
