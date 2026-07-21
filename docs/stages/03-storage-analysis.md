# Etap 3 — Magazyn NDJSON i analiza trendów

## Cel
Warstwa, dla której to wszystko powstało: magazyn z osią czasu (`data/store/structural.ndjson`, wyjście etapu 2) i odpytywanie trendów przez Claude Code w terminalu (S2), plus zgodność ze schematem BigQuery bez transformacji (S4).

Sedno: to nie jest budowa silnika zapytań. PRD świadomie nie przewiduje dedykowanego narzędzia do trendów — Scope pkt 6 mówi wprost: konsumpcja to „Claude Code w terminalu czyta pliki; analiza trendów/porównań markerów przez prompt". Rola tego etapu to dowieść, że płaski, jednorodny schemat NDJSON (`marker`, `value`, `unit`, `exam_date`, `reference_low/high`) wystarcza, żeby odpowiedzieć na pytanie o trend bez pośredniego kodu zapytań — a tam, gdzie kod jest realnie potrzebny (raport na wizytę, walidacja pod BigQuery), zbudować dokładnie tyle, ile trzeba, nie więcej.

Trzy równoległe strumienie pracy: (1) walidacja, że magazyn z etapu 2 jest spójny na tyle, by bezbłędnie załadować się do BigQuery (typy i klucze pól, nie tylko poprawność JSON per linia); (2) dowód, że trend/porównanie działają „przez prompt", bez dedykowanego skryptu; (3) `src/report.py` — jedyny realny artefakt kodu tego etapu, bo User Story 4 z PRD chce gotowego pliku Markdown „na wizytę", nie tylko odpowiedzi w czacie.

## Zakres / Definition of Done
- [x] Kanoniczny NDJSON: płaskie rekordy, schemat pipeline'u strukturalnego zwalidowany — 114/114 rekordów to poprawny JSON z identycznym zestawem 11 kluczy i spójnymi typami per pole (`value`/`reference_low`/`reference_high`: float|None; `unit`/`value_text`: str|None; reszta: str) — gotowe pod BigQuery bez transformacji
- [x] Trend dowolnego markera jednym promptem w Claude Code — zademonstrowane bezpośrednio z NDJSON (hemoglobina: 2020-12-21 → 2023-01-23, 14.1 → 14.9 g/dl). Formalny próg S2 (marker z ≥3 pomiarami) niezweryfikowany na obecnym wolumenie (14 dok., 3 unikalne daty) — pomiar właściwy dla etapu 5 na realnym backfillu
- [x] Porównanie dwóch markerów na osi czasu — zademonstrowane (hemoglobina vs OB, lokalny analogon Fe vs CRP z PRD: marker niedokrwistości vs marker stanu zapalnego)
- [ ] Ręczny load NDJSON do BigQuery bez błędów schematu (test S4) — walidacja zgodności zrobiona (patrz wyżej); sam load wymaga projektu/kont GCP operatora — do wykonania przez właściciela
- [x] Raport Markdown „do lekarza": trendy markerów — `src/report.py`, realny raport z 114 rekordów: 10 paneli, 72 serie marker/jednostka, strzałki kierunku zmiany

## Notatki
<!-- Grupuj po temacie, nie po dacie (chronologię trzyma git). Każdy podpunkt
     w OSOBNYM akapicie (pusta linia między nimi). Dla każdego tematu:

### <Temat / czego dotyczy>

**Decyzja:** co ustalono.

**Dlaczego:** uzasadnienie, trade-offy.

**Jak działa:** mechanizm narzędzia pod spodem — sedno nauki.

**Pułapki:** co zaskoczyło, na co uważać.

Nie każdy temat wymaga wszystkich czterech podpunktów. To notatki do nauki, nie log czynności. -->

### Jeden marker, dwie jednostki — pułapka grupowania po samym kodzie

**Decyzja:** trendy i raport grupują po parze `(marker, unit)`, nie po samym `marker`. `src/report.py::build_report` klucz grupujący to `(r["marker"], r["unit"])`.

**Dlaczego:** różnicowanie morfologii (NEU/LYM/MONO/EOS/BASO) w realnym źródle występuje w DWÓCH jednostkach pod tym samym kodem kanonicznym — raz jako odsetek (`%`), raz jako wartość bezwzględna (`tys/µl`). Pierwszy, naiwny check policzył to jako „4 pomiary NEU" (sugerując, że próg S2 ≥3 jest już spełniony) — błędnie, bo to dwie różne serie po 2 punkty, nie jedna po 4. Naiwne grupowanie po samym `marker` zlałoby odsetek i wartość bezwzględną w jeden „trend", co dałoby liczbowo bezsensowny wynik (np. „51.6 → 3.13 → 54.7" jako jeden ciąg).

**Jak działa:** `structural_pipeline.py` zapisuje `unit` jako osobne pole per rekord (z `units.yml` albo wprost z dokumentu) — schemat już to rozróżnia, trzeba tylko go użyć w grupowaniu, nie zakładać „jeden kod = jedna seria".

**Pułapki:** to pierwszy realny przypadek w projekcie, gdzie zliczanie „surowych rekordów" dało inny (i mylący) wynik niż zliczanie „rzeczywistych serii pomiarowych". Każde pytanie w stylu „ile pomiarów ma X" wymaga doprecyzowania, czy liczymy rekordy, czy serie — różnica bywa 2x.

### Próg S2 (≥3 pomiary) — zbudowany mechanizm, niezmierzony próg

**Decyzja:** trend/porównanie działają i są zademonstrowane na realnych danych (2-punktowe serie), ale formalne domknięcie progu S2 („marker z ≥3 pomiarami") przesunięte do etapu 5.

**Dlaczego:** obecny wolumen (14 dok., 3 unikalne daty badań) nie ma ani jednej serii marker+jednostka z 3 różnymi datami — maksimum to 2. To nie wada mechanizmu (zapytanie o trend działa identycznie dla 2 i dla N punktów), tylko naturalny skutek małego wolumenu przed backfillem. Etap 5 i tak ma własny punkt DoD „Pomiar i zapis wyników S1–S4" — właściwe miejsce na formalny test tego konkretnego progu na realnych ~115–120 dokumentach.

**Pułapki:** łatwo pomylić „mechanizm zbudowany i działa" z „kryterium sukcesu spełnione" — to dwa różne twierdzenia. Pierwsze można udowodnić teraz (kodem, na małej próbce), drugie wymaga realnego wolumenu danych, którego jeszcze nie ma.

### Walidacja schematu pod BigQuery — co konkretnie sprawdzić

**Decyzja:** „gotowość pod BigQuery" sprawdzona jako: (1) każda linia to poprawny JSON, (2) każdy rekord ma dokładnie ten sam zestaw kluczy, (3) każde pole ma spójny typ Python (właściwy typ + ewentualnie `None`, nigdy więcej niż te dwa).

**Dlaczego:** to dokładnie te trzy warunki, których złamanie wywala `bq load` na realnym pliku — niespójna liczba kolumn albo pole raz-liczba-raz-tekst to najczęstsze przyczyny błędu schematu przy NEWLINE_DELIMITED_JSON. Sama „poprawność JSON" (częsty, za wąski test) tego nie łapie.

**Jak działa:** dla każdego pola zbiera się zbiór typów Pythona występujących we wszystkich 114 rekordach (`{type(v).__name__ for v in ...}`) — wynik musi mieć rozmiar ≤2 (typ + `NoneType`). Znaleziono: `value`/`reference_low`/`reference_high` → `float|None`, `unit`/`value_text` → `str|None`, reszta zawsze `str`. Dokładnie to, czego BigQuery oczekuje po polu `NULLABLE`.

**Pułapki:** sam load NDJSON do BigQuery jest świadomie ręczny (PRD: „Automatyczny load do BigQuery" poza zakresem V1) — wymaga projektu/kont GCP, których nie mam. Ten etap dostarcza walidację i pewność, że load się powinien udać, nie wykonuje go za operatora. Automatyzacja w n8n (V1.1+?) jest technicznie tania (gotowy node BigQuery), ale to zmiana zakresu — wymaga aktualizacji PRD, nie robimy tego po cichu.

### Instrukcja: ręczny load `structural.ndjson` do BigQuery (konsola GCP)

**Decyzja:** load przez UI konsoli GCP (Create table → Upload), nie `bq` CLI — operator woli klikać, ma pełną kontrolę nad każdym krokiem i widzi błędy bezpośrednio w przeglądarce.

**Jak działa:** krok po kroku —

1. Otwórz [console.cloud.google.com/bigquery](https://console.cloud.google.com/bigquery), wybierz właściwy projekt (górny pasek).
2. W panelu Explorer kliknij swój projekt → **View actions** (⋮) → **Create dataset**, jeśli jeszcze nie masz datasetu na dane zdrowotne (np. `health_data`). Lokalizacja dowolna, ale ustaw raz i trzymaj się jej dla kolejnych loadów.
3. Kliknij ⋮ przy datasecie → **Create table**.
4. **Source**: „Upload" → **Select file** → wskaż lokalnie `data/store/structural.ndjson` (ścieżka: `/Users/p/Documents/dev/Document-Intelligence-Platform/data/store/structural.ndjson`).
5. **File format**: `JSONL (Newline delimited JSON)` — NIE zwykły „JSON".
6. **Destination**: Table name np. `structural_markers`.
7. **Schema**: odznacz „Auto detect" i wybierz **Edit as text**, wklej schemat poniżej — bezpieczniejsze niż autodetekcja (np. `value` mogłoby zostać źle rozpoznane jako INTEGER, gdyby akurat wszystkie próbki w pliku były liczbami całkowitymi):

   ```json
   [
     {"name": "record_type", "type": "STRING", "mode": "REQUIRED"},
     {"name": "panel", "type": "STRING", "mode": "REQUIRED"},
     {"name": "marker", "type": "STRING", "mode": "REQUIRED"},
     {"name": "marker_raw", "type": "STRING", "mode": "REQUIRED"},
     {"name": "value", "type": "FLOAT", "mode": "NULLABLE"},
     {"name": "value_text", "type": "STRING", "mode": "NULLABLE"},
     {"name": "unit", "type": "STRING", "mode": "NULLABLE"},
     {"name": "reference_low", "type": "FLOAT", "mode": "NULLABLE"},
     {"name": "reference_high", "type": "FLOAT", "mode": "NULLABLE"},
     {"name": "exam_date", "type": "DATE", "mode": "NULLABLE"},
     {"name": "source_file", "type": "STRING", "mode": "REQUIRED"}
   ]
   ```

8. Sekcja **Advanced options** — zostaw domyślne (bez partycjonowania/klastrowania na tę skalę danych).
9. **Create table**. Po chwili sprawdź wynik: sukces = tabela pojawia się w Explorerze z 114 wierszami (Preview / Details → Table info → „Number of rows"). Błąd = czerwony komunikat na dole ekranu z dokładnym opisem (np. niezgodność typu w konkretnej linii) — wklej mi go, jeśli się pojawi.

**Pułapki:** `exam_date` w schemacie jako `DATE` (nie `STRING`) — pole ma zawsze format `YYYY-MM-DD` (patrz `structural_pipeline.py::exam_date`), więc BigQuery przyjmie je natywnie i od razu pozwoli na zapytania zakresowe po dacie, bez rzutowania w SQL. Jeśli kiedyś pojawi się rekord bez `exam_date`, `NULLABLE` to obsłuży bez błędu.

