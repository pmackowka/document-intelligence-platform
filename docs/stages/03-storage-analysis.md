# Etap 3 — Magazyn NDJSON i analiza trendów

## Cel
Warstwa, dla której to wszystko powstało: magazyn z osią czasu (`data/store/structural.ndjson`, wyjście etapu 2) i odpytywanie trendów przez Claude Code w terminalu (S2), plus zgodność ze schematem BigQuery bez transformacji (S4).

Sedno: to nie jest budowa silnika zapytań. PRD świadomie nie przewiduje dedykowanego narzędzia do trendów — Scope pkt 6 mówi wprost: konsumpcja to „Claude Code w terminalu czyta pliki; analiza trendów/porównań markerów przez prompt". Rola tego etapu to dowieść, że płaski, jednorodny schemat NDJSON (`marker`, `value`, `unit`, `exam_date`, `reference_low/high`) wystarcza, żeby odpowiedzieć na pytanie o trend bez pośredniego kodu zapytań — a tam, gdzie kod jest realnie potrzebny (raport na wizytę, walidacja pod BigQuery), zbudować dokładnie tyle, ile trzeba, nie więcej.

Trzy równoległe strumienie pracy: (1) walidacja, że magazyn z etapu 2 jest spójny na tyle, by bezbłędnie załadować się do BigQuery (typy i klucze pól, nie tylko poprawność JSON per linia); (2) dowód, że trend/porównanie działają „przez prompt", bez dedykowanego skryptu; (3) `src/report.py` — jedyny realny artefakt kodu tego etapu, bo User Story 4 z PRD chce gotowego pliku Markdown „na wizytę", nie tylko odpowiedzi w czacie.

## Zakres / Definition of Done
- [x] Kanoniczny NDJSON: płaskie rekordy, schemat pipeline'u strukturalnego zwalidowany — 114/114 rekordów to poprawny JSON z identycznym zestawem kluczy i spójnymi typami per pole (`value`/`reference_low`/`reference_high`: float|None; `unit`/`value_text`/`reference_note`: str|None; reszta: str) — gotowe pod BigQuery bez transformacji. Rozszerzony do 12 kluczy (`reference_note`) po realnym loadzie — patrz Notatki
- [x] Trend dowolnego markera jednym promptem w Claude Code — zademonstrowane bezpośrednio z NDJSON (hemoglobina: 2020-12-21 → 2023-01-23, 14.1 → 14.9 g/dl). Formalny próg S2 (marker z ≥3 pomiarami) niezweryfikowany na obecnym wolumenie (14 dok., 3 unikalne daty) — pomiar właściwy dla etapu 5 na realnym backfillu
- [x] Porównanie dwóch markerów na osi czasu — zademonstrowane (hemoglobina vs OB, lokalny analogon Fe vs CRP z PRD: marker niedokrwistości vs marker stanu zapalnego)
- [x] Ręczny load NDJSON do BigQuery bez błędów schematu (test S4) — operator wykonał realny load przez konsolę GCP (schemat 11 kolumn), przeszedł bez błędów. Schemat od tego czasu rozszerzony do 12 kolumn (`reference_note`) — tabela do przeładowania, instrukcja niżej
- [x] Raport Markdown „do lekarza": trendy markerów — `src/report.py`, realny raport z 114 rekordów: 10 paneli, 72 serie marker/jednostka, strzałki kierunku zmiany; `reference_note` wyświetlana zamiast „—" gdy brak czystego zakresu

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

**Jak działa:** pierwszy load (schemat 11 kolumn) przeszedł bez błędów. Schemat od tego czasu rozszerzony o `reference_note` (12. kolumna, patrz notatka „reference_note..." niżej) — tabelę trzeba przeładować od zera, BigQuery nie dokłada kolumn do istniejącej tabeli przez UI uploadu.

**Krok 0 — usuń starą tabelę (dane + schemat):** w konsoli GCP → **BigQuery Studio** → nowe okno **SQL query** → wklej i uruchom (podmień `projekt.dataset.tabela` na realną nazwę):

```sql
DROP TABLE `projekt.dataset.structural_markers`;
```

To kasuje tabelę razem ze schematem i wszystkimi wierszami — nieodwracalne, ale bezpieczne, bo źródło prawdy to `data/store/structural.ndjson`, nie sama tabela. Alternatywnie: w Explorerze kliknij ⋮ przy tabeli → **Delete** → potwierdź nazwą tabeli.

**Krok 1+ — załaduj od nowa:** ⋮ przy datasecie → **Create table** → Source „Upload" → plik `data/store/structural.ndjson` → **File format**: `JSONL (Newline delimited JSON)` → Table name jak poprzednio (np. `structural_markers`) → **Schema**: odznacz „Auto detect", **Edit as text**, wklej (12 kolumn — dodana `reference_note`):

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
  {"name": "reference_note", "type": "STRING", "mode": "NULLABLE"},
  {"name": "exam_date", "type": "DATE", "mode": "NULLABLE"},
  {"name": "source_file", "type": "STRING", "mode": "REQUIRED"}
]
```

**Pułapki:** `exam_date` jako `DATE` (nie `STRING`) — format źródła zawsze `YYYY-MM-DD` (`structural_pipeline.py::exam_date`), więc BigQuery przyjmie natywnie, bez rzutowania w SQL przy zapytaniach zakresowych.

### `reference_note` — surowa proza zamiast utraty progu referencyjnego

**Decyzja:** `parse_section_chunk` (Warstwa 2) dostał 6. wartość zwracaną — `note`. Wypełnia się WYŁĄCZNIE gdy `reference_low`/`reference_high` finalnie zostają puste, i tylko dla linii pasujących do wąskiego wzorca `^[≥≤<>]\s*=?\s*\d` (zaczyna się od symbolu porównania i cyfry).

**Dlaczego:** realny przypadek z lipidogramu — HDL/nie-HDL/LDL wyrażają próg jako zdanie z cytatem wytycznych („≥ 40 mg/dl zgodnie z zaleceniami PTK i PTDL"), czasem kilka progów zależnych od kategorii ryzyka pacjenta („<100 mg/dl - bardzo duże ryzyko / <130 - duże / <145 - zdrowi"). Bez tej zmiany zdanie znikało całkowicie — złamanie zasady „nie gub po cichu" z etapu 3(oryg.). Świadomie NIE próbowano sparsować tego na `reference_low`/`reference_high` — przy wielu progach zależnych od nieznanego kontekstu pacjenta wybór „tego jednego właściwego" byłby zgadywaniem, gorszym niż `NULL`.

**Jak działa:** wzorzec złapie linię zaczynającą się od symbolu porównania + cyfry, niezależnie od reszty zdania — działa dla „≥ 40 mg/dl zgodnie z..." i „<100 mg/dl - dla osób...", ale świadomie NIE złapie stylu „Stężenie zalecane: powyżej 40 mg/dl" (inne sformułowanie w innym dokumencie tego samego labu, weryfikowane realnie — patrz Pułapki). Wielokrotne dopasowania w jednym chunku (np. 3 progi ryzyka nie-HDL) łączą się przez „ / ".

**Pułapki:** (1) wzorzec musi być wąski — szerszy check typu „linia zawiera cyfrę" złapałby też stopkę strony („Strona: 1 z 2") jako fałszywy zakres referencyjny; test na LDL to potwierdził (stopka poprawnie odrzucona). (2) przypis metodologiczny przy eGFR („Wzór wg MDRD") nie zawiera cyfry na początku linii, więc nie trafia do `note` — sprawdzone jawnym testem, nie założeniem. (3) realny efekt na 14 dokumentach: 12→9 rekordów liczbowych bez żadnej informacji o zakresie; pozostałe 9 to albo naprawdę brak progu w źródle, albo inne sformułowanie w drugim dokumencie tego samego labu — świadomie zaakceptowane, nie gonimy każdego wariantu językowego regexem.

