# V8 — REJESTR DOWODÓW ODZYSKIWANIA STARYCH STREF

Cel: rozdzielić **strefę odnalezioną w starym systemie** od **strefy liczbowo gotowej do użycia w V8**. Niczego nie zgadujemy.

## RENDER

**Stan źródła: STARE STREFY POTWIERDZONE.**

W V7 funkcja `V273_5_DOKONCZ_RENDER_BEZ_REBUILD()` zawiera jawny zapis: `MASTER/STREFY już mają RENDER po udanym imporcie` i następnie wywołuje `V273_5_POLICZ_I_ZAPISZ_DCA_NOWEGO_KRYPTO_('RENDER')`.

Ta funkcja odrzuca aktywo, jeśli nie ma aktywnej `DEMAND 1D` albo aktywnej `DEMAND 1T`. Skoro ścieżka RENDER była domykana z istniejącego MASTER/STREFY, mamy twardy dowód, że co najmniej źródłowe strefy 1D i 1T istniały w V7.

**Nie wpisano jeszcze granic liczbowych do `config/alt_zones.csv`**, ponieważ w odzyskanych plikach nie znaleziono jeszcze samego pakietu JSON / wierszy MASTER z wartościami Od/Do.

## FLOKI

**Stan źródła: STARY PAKIET 7/7 POTWIERDZONY W HISTORII PRACY.**

FLOKI był testowany przez `DODAJ_PROJEKT` i pojawił się w `PORTFEL`, `DANE SILNIKA` oraz `STREFY`. W historii pracy zachowany jest fakt, że przygotowany pakiet stref obejmował pełny zestaw `1D, 2D, 3D, 4D, 5D, 1T, 2T`.

Liczbowo w V8 odzyskano obecnie tylko 1D i 1T. Pozostałych wartości nie wolno zastępować nowymi poziomami bez odnalezienia starego pakietu lub źródłowego screena.

## XLM

**Stan źródła: 1D i 1T twardo potwierdzone w MASTER_STREFY.**

V275.38 przy wznowieniu XLM bez ponownego UPSERT sprawdza istniejący `MASTER_AKTYWA + MASTER_STREFY` i wymaga aktywnej `DEMAND 1D` oraz `DEMAND 1T/1W`. To potwierdza istnienie tych stref przed wznowieniem importu.

Granice liczbowe nadal wymagają odzyskania ze starego MASTER-a / pakietu źródłowego.

## XRP

XRP był aktywnym projektem V7 i występuje w późniejszym audycie/fazie ruchu razem z XLM. Sam ten fakt nie wystarcza do odtworzenia liczb stref. Do V8 nie wpisujemy granic bez starego źródła.

## FLOKI / PEPE / SPX6900 — wyjaśnienie utraty części danych

W starszym V258 istniała funkcja usuwająca z arkusza STREFY rekordy `SPX6900`, `PEPE`, `FLOKI` jako stare projekty. To wyjaśnia, dlaczego historyczne poziomy mogły być wcześniej używane, a później nie występować w kanonicznym MASTER 17/17.

## ZASADA MIGRACJI

1. `source_found=true` oznacza, że potwierdziliśmy istnienie starego źródła / strefy.
2. `numeric_ready=true` oznacza dopiero, że konkretne poziomy Od/Do są zapisane w `config/alt_zones.csv` jako `CONFIRMED`.
3. Nie zamieniamy DCA na STREFY i nie rekonstruujemy granic na podstawie samego DCA.
4. Nie prosimy użytkownika o ponowne screeny, dopóki istnieje rozsądna ścieżka odzyskania starego źródła.
