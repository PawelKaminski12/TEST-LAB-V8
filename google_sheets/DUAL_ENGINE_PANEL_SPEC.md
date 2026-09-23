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
7. ALARMY_EKSTREMOW
8. HISTORIA
9. USTAWIENIA

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

Nie pokazujemy w PANELU MACD, RSI, MFI, ATR, FOMO, stref, punktacji, przepływów, rotacji i szczegółów Market Reader. Te dane zostają w maszynowni oraz w alarmach.

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
- DCA1/2/3
- decyzja końcowa
- blokady

## SILNIK_TACTICAL — maszynownia
Źródło: `tactical_engine/TACTICAL_ENGINE.json` + `TACTICAL_READINESS.json` + `TACTICAL_CONFLUENCE.csv`.

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

MFI nie jest samodzielnym sygnałem kupna/sprzedaży. Działa jako warstwa potwierdzenia i wykrywania skrajności razem z RSI, MACD, FOMO, trendem i strefami.

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
- FOMO,
- MACD pozostaje kontekstem kierunku/momentum w SILNIK_TACTICAL.

Domyślne progi RSI/FOMO:
- RSI wykupienie: RSI >= 75
- RSI wyprzedanie: RSI <= 25
- FOMO HARD BLOCK: FOMO >= 8

Domyślne progi MFI:
- ostrzeżenie górne: 80
- skrajne górne: 90
- ostrzeżenie dolne: 20
- skrajne dolne: 10

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
3. pobiera MARKET_READER jeśli dostępny,
4. odświeża maszynownię LONG i TACTICAL,
5. przelicza polski PANEL,
6. skanuje RSI / MFI / FOMO na 1H / 4H / 1D,
7. zapisuje nowe alarmy do HISTORIA,
8. opcjonalnie wysyła e-mail,
9. aktualizuje znacznik czasu.

Dodatkowa komenda `SPRAWDŹ EKSTREMA` wykonuje sam skan ekstremów bez pełnego odświeżania panelu.

## Zasady bezpieczeństwa
- LONG i TACTICAL mają osobne pule kapitału.
- Brak automatycznych transakcji.
- Status silnika to status badawczy/decyzyjny, nie zlecenie giełdowe.
- Brak synchronizacji ilości między portfelami.
- V7 produkcyjny pozostaje nietknięty.
- Market Reader nie może nadpisywać twardych blokad.
- RSI/MFI/FOMO ekstremum nie jest automatycznie sygnałem sprzedaży ani zakupu.
- Dane maszynowni nie rozrastają głównego PANELU.

## Status projektu
Warstwa panelu i integracji Google Sheets jest domknięta funkcjonalnie: LONG + TACTICAL, polski widok użytkownika, oddzielne portfele, historia oraz alarmy ekstremów RSI/MFI/FOMO 1H/4H/1D są zdefiniowane i zaimplementowane w `DUAL_ENGINE_APPS_SCRIPT_FULL.txt`.

Kalibracja progów strategii TACTICAL pozostaje osobnym etapem badawczym. Nie wolno oznaczać jej jako zamrożonej strategii wykonawczej wyłącznie na podstawie pojedynczego holdoutu.
