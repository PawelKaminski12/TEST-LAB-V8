# V8 DUAL ENGINE — GOOGLE SHEETS PANEL SPEC

## Cel
Jeden skoroszyt Google Sheets jako centrum dowodzenia dla dwóch niezależnych horyzontów:
- LONG PORTFEL / LONG ENGINE — średni i długi termin.
- TACTICAL PORTFEL / TACTICAL ENGINE — 1H / 4H / 1D.

Zasada nadrzędna: SILNIK = MASZYNOWNIA, PANEL = KRÓTKA DECYZJA. Warstwa V8 jest research / decision support only. Brak automatycznego wykonywania transakcji.

## Zakładki użytkowe
1. PANEL
2. PORTFEL_LONG
3. PORTFEL_TACTICAL
4. SILNIK_LONG
5. SILNIK_TACTICAL
6. PRZEPLYWY
7. ETF_BTC_ETH
8. ETF_HISTORIA
9. LAB_ANALIZA_AKTYWA
10. MARKET_READER
11. ALARMY_EKSTREMOW
12. HISTORIA
13. USTAWIENIA

## PANEL — kompaktowy widok po polsku
Panel pozostaje w układzie 7 kolumn:
- AKTYWO
- CENA
- LONG
- TACTICAL
- RYZYKO 0–10
- ZGODNOŚĆ
- ALERT

Nie dokładamy kolejnych kolumn do głównego PANELU. Kolumna ALERT pokazuje najważniejszy świeży alarm ekstremum / zgodność wielu TF oraz skrót centrum ryzyka Tactical. Szczegóły pozostają w maszynowni i ALARMY_EKSTREMOW.

## SILNIK_LONG
Źródło: `crypto_data_hub/ALT_ENGINE_MASTER_CHECKPOINT.json` + warstwy V8.
Rdzeń:
- jakość danych,
- strefy 1D / 2D / 3D / 4D / 5D / 1T / 2T,
- trend,
- FOMO,
- rotacja,
- faza rynku,
- FLOW LONG 0–10,
- ETF 5D / 20D / 30D, gdy dotyczy,
- DCA1 / DCA2 / DCA3,
- decyzja,
- blokady.

Strefy użytkownika są źródłem prawdy dla mapy DCA. System nie wymyśla brakujących stref.

## SILNIK_TACTICAL
Źródła: `tactical_engine/TACTICAL_ENGINE.json`, `TACTICAL_READINESS.json`, `CRYPTO_MARKET_PHASE.json`, `TACTICAL_CONFLUENCE.csv`.

Warstwy:
- 1H timing,
- 4H decision,
- 1D regime,
- MACD,
- RSI,
- MFI(14),
- wolumen,
- ATR,
- breakout / retest,
- FOMO,
- kontekst stref,
- Market Reader jako second-eye,
- exit risk,
- tactical score,
- tactical status,
- FLOW TACTICAL 0–5,
- ekstrema 1H / 4H / 1D,
- CENTRUM RYZYKA,
- POWÓD RYZYKA.

MFI nie jest samodzielnym sygnałem kupna / sprzedaży. Jest potwierdzeniem razem z RSI, MACD, FOMO, trendem i strefami.

## ALARMY_EKSTREMOW — logika finalna
Alarmy są informacyjne i nie wykonują transakcji.

### Źródła
- RSI,
- MFI,
- MACD względny do historii aktywa,
- FOMO.

### Interwały i hierarchia
- 1H — szybkie lokalne ekstrema; najniższa waga.
- 4H — główny interwał Tactical; wysoka waga.
- 1D — najwyższy kontekst.

Pojedyncze ostrzeżenie 1H pozostaje w zakładce alarmów i historii, ale nie zaśmieca głównego PANELU.

### Zbieżność w ramach jednego interwału
Dla jednego aktywa + interwału sygnały RSI / MFI / MACD / FOMO są grupowane w jeden alarm zbiorczy.
Priorytety:
- OSTRZEŻENIE,
- MOCNY,
- KRYTYCZNY.

1D ma wyższy kontekst niż 4H i 1H.

### Świeżość i wygaszanie
Domyślne maksymalne wieku danych:
- 1H: 3 godziny,
- 4H: 10 godzin,
- 1D: 36 godzin.

Stary alarm dostaje status STARY, nie trafia do głównego PANELU i nie wysyła powiadomienia. Brak poprawnego czasu danych daje BRAK CZASU i również blokuje alarm aktywny.

### Zgodność wielu interwałów
Świeże alarmy są łączone kierunkowo:
- PRZEGRZANIE,
- WYPRZEDANIE.

Reguły:
- 1H + 4H w tym samym kierunku → MOCNY,
- 4H + 1D → KRYTYCZNY,
- 1H + 4H + 1D → KRYTYCZNY WIELE TF.

Sygnały o przeciwnych kierunkach nie są sztucznie sumowane.

### Dynamika alarmu
System rozpoznaje zmianę stanu:
- NOWY,
- NASILA SIĘ,
- BEZ ZMIAN,
- SŁABNIE,
- WYGASŁ.

Powiadomienia są nastawione na nowe lub nasilające się zdarzenia. Stan BEZ ZMIAN nie powinien generować powtarzalnego hałasu.

### Zakładka ALARMY_EKSTREMOW
Aktualny widok obejmuje m.in.:
- AKTYWNY,
- AKTYWO,
- INTERWAŁ,
- ŚWIEŻOŚĆ,
- WIEK H,
- LIMIT H,
- ZBIEŻNOŚĆ,
- PRIORYTET,
- WAGA INTERWAŁU,
- KIERUNEK,
- STAN,
- POPRZ. PRIORYTET,
- SYGNAŁY,
- RSI,
- MFI,
- MACD %,
- MACD Z,
- FOMO,
- OPIS,
- CZAS DANYCH.

## CENTRUM RYZYKA TACTICAL
Centrum ryzyka nie zastępuje silnika Tactical. Jest warstwą podsumowującą ryzyko i kontekst.

Łączy:
- exit risk,
- maksymalne FOMO z 1H / 4H / 1D,
- strefę podaży / popytu,
- status Tactical,
- aktywne świeże ekstrema,
- zgodność wielu TF,
- kierunek PRZEGRZANIE / WYPRZEDANIE.

Stany użytkowe:
- 🟢 NORMALNIE,
- 🟠 UWAGA,
- 🔴 PODWYŻSZONE RYZYKO,
- 🛡️ OCHRONA KAPITAŁU.

Wielointerwałowe PRZEGRZANIE może mocno podnieść poziom ryzyka. Wielointerwałowe WYPRZEDANIE nie jest automatycznie traktowane jako sygnał ochrony kapitału.

W `SILNIK_TACTICAL` dodawane są kolumny:
- CENTRUM RYZYKA,
- POWÓD RYZYKA.

W głównym PANELU pojawia się wyłącznie skrót najważniejszego stanu, bez rozszerzania układu.

## USTAWIENIA alarmów
- ALARMY_EKSTREMOW = ON/OFF
- RSI_GORNY = 75
- RSI_DOLNY = 25
- FOMO_TWARDY = 8
- MFI_GORNY_OSTRZEZENIE = 80
- MFI_GORNY_SKRAJNY = 90
- MFI_DOLNY_OSTRZEZENIE = 20
- MFI_DOLNY_SKRAJNY = 10
- ALARM_MAX_WIEK_1H_H = 3
- ALARM_MAX_WIEK_4H_H = 10
- ALARM_MAX_WIEK_1D_H = 36
- EMAIL_ALERTY = ON/OFF
- EMAIL_DO = adres docelowy

## PRZEPLYWY
Warstwa potwierdzająca obejmuje m.in. ETH/BTC, dominacje, stablecoin liquidity, ETF BTC / ETH / SOL oraz FLOW LONG i FLOW TACTICAL. Nie jest samodzielnym triggerem wejścia.

## MARKET_READER
Zewnętrzny Market Reader jest second-eye. Nie może nadpisywać twardych blokad wewnętrznego silnika. Adapter może pozostawać w stanie oczekiwania, jeśli zewnętrzne źródło nie jest podłączone.

## ZGODNOŚĆ na PANELU
- 2/2 POZYTYWNE,
- TYLKO TACTICAL,
- TYLKO LONG,
- NEUTRALNIE,
- KONFLIKT.

To skrót informacyjny, nie sygnał wykonawczy.

## Odświeżanie
`ODŚWIEŻ_WSZYSTKO`:
1. pobiera LONG / TACTICAL / phase / ETF / LAB / Market Reader,
2. odświeża maszynownię,
3. buduje świeże alarmy ekstremów,
4. ocenia zbieżność jednego TF,
5. ocenia zgodność wielu TF,
6. wyznacza dynamikę alarmów,
7. wyznacza centrum ryzyka Tactical,
8. aktualizuje PANEL,
9. zapisuje istotne zmiany do HISTORIA,
10. wysyła opcjonalne powiadomienia,
11. aktualizuje LAST_REFRESH.

`SPRAWDŹ EKSTREMA` wykonuje warstwę alarmową bez pełnego odświeżania pozostałych danych.

## Zasady bezpieczeństwa
- AUTO_EXECUTION = OFF.
- V7_TOUCH = OFF.
- LONG i TACTICAL mają osobne pule kapitału.
- Brak synchronizacji ilości między portfelami.
- Alarmy, centrum ryzyka i FLOW są warstwami informacyjnymi.
- Market Reader nie nadpisuje hard guardów.
- System nie zgaduje stref użytkownika.
- RSI / MFI / MACD / FOMO ekstremum nie jest automatycznym sygnałem kupna lub sprzedaży.

## Status projektu
Warstwa Google Sheets dla LONG + TACTICAL jest funkcjonalnie domknięta: polski kompaktowy PANEL, oddzielne portfele, przepływy, ETF, LAB, alarmy ekstremów, świeżość, wiele TF, dynamika alarmów, historia oraz centrum ryzyka Tactical.

Kalibracja progów strategii Tactical pozostaje osobnym etapem badawczym. Nie wolno traktować obecnych progów jako zamrożonej strategii wykonawczej bez dalszej walidacji na danych poza próbką.
