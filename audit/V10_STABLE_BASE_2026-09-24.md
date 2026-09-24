# V10 STABLE BASE — 2026-09-24

Status: **AKCEPTOWANA BAZA / PUNKT KONTROLNY**

Potwierdzone przez użytkownika po uruchomieniu Porannego Radaru:
- Poranny Radar działa i pokazuje komplet 13/13 aktywów.
- Ręczny wybór interwałów 1H / 2H / 4H oraz AUTO działa jako docelowy układ.
- Legenda kolorów po prawej zaakceptowana.
- Tło stonowane, jasnoniebiesko-szare zaakceptowane.
- Wspólny język sygnałów zaakceptowany:
  - GORĄCO = czerwony/różowy,
  - CHŁODNO = niebieski,
  - NEUTRALNIE = zielony,
  - UWAGA = żółty,
  - FOMO >= 8 = pomarańczowy,
  - MACD alert = szaro-niebieski.
- MACD:
  - EKSTREMUM + = górne granice,
  - UWAGA + = górne ostrzeżenie,
  - EKSTREMUM - = dolne granice,
  - UWAGA - = dolne ostrzeżenie.
- Zielony wiersz ma oznaczać faktyczny brak aktywnego ostrzeżenia; aktywny alert wskaźnika ma podnosić kolor wiersza co najmniej do UWAGA (żółty).
- V7 pozostaje nietknięty.
- Execution pozostaje OFF.

Bezpieczny build referencyjny:
- GitHub Actions run: `35983382098` — SUCCESS
- Wygenerowany V10: commit `c41239be64619fd4ab37b20331b7548c34e4567c`
- Repo: `PawelKaminski12/TEST-LAB-V8`
- Plik produkcyjny: `google_sheets/DUAL_ENGINE_APPS_SCRIPT_FULL_V10.txt`

Zasada dalszych zmian:
1. Nie przebudowywać od zera zaakceptowanego Porannego Radaru.
2. Każda kolejna zmiana ma być małym patchem na tej bazie.
3. Po zmianie wymagane: build SUCCESS + syntax check + test zachowania 13/13.
4. Jeśli nowa zmiana psuje dane lub układ, wracamy do tego punktu kontrolnego.

To jest baza referencyjna dla dalszej pracy nad V8.
