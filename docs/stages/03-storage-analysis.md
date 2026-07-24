# Etap 3 — Magazyn NDJSON i analiza trendów

## Cel
Warstwa, dla której to wszystko powstało: magazyn z osią czasu (`data/store/structural-backfill.ndjson`, wyjście etapu 2) i odpytywanie trendów przez Claude Code w terminalu (S2), plus zgodność ze schematem BigQuery bez transformacji (S4).

To nie budowa silnika zapytań. PRD świadomie nie przewiduje dedykowanego narzędzia do trendów — konsumpcja to „Claude Code w terminalu czyta pliki; analiza przez prompt". Rola etapu: dowieść, że płaski, jednorodny schemat NDJSON wystarcza, żeby odpowiedzieć na pytanie o trend bez pośredniego kodu — a tam, gdzie kod jest realnie potrzebny (raport na wizytę, walidacja pod BigQuery), zbudować dokładnie tyle, ile trzeba. Jedyny realny artefakt kodu tego etapu to `src/report.py` (User Story 4 chce gotowego pliku Markdown „na wizytę").

## Zakres / Definition of Done
- [x] Kanoniczny NDJSON zwalidowany pod BigQuery — 114/114 rekordów to poprawny JSON z identycznym zestawem kluczy i spójnymi typami per pole (`value`/`reference_low`/`reference_high`: float|None; `unit`/`value_text`/`reference_note`: str|None; reszta: str). Rozszerzony do 12 kluczy (`reference_note`) po realnym loadzie — patrz Notatki
- [x] Trend dowolnego markera jednym promptem — zademonstrowane z NDJSON (hemoglobina: 2020→2023, 14.1→14.9 g/dl). Formalny próg S2 (≥3 pomiary) niezweryfikowany na tym wolumenie (14 dok., 3 daty) — pomiar właściwy dla etapu 4
- [x] Porównanie dwóch markerów na osi czasu — zademonstrowane (hemoglobina vs OB)
- [x] Ręczny load NDJSON do BigQuery bez błędów schematu (S4) — operator wykonał realny load przez konsolę GCP (11 kolumn), bez błędów. Schemat rozszerzony do 12 kolumn (`reference_note`) — instrukcja niżej
- [x] Raport Markdown „do lekarza": trendy markerów — `src/report.py`, realny raport z 114 rekordów: 10 paneli, 72 serie, strzałki kierunku; `reference_note` zamiast „—" gdy brak czystego zakresu

## Notatki

### Jeden marker, dwie jednostki — pułapka grupowania po samym kodzie

**Decyzja:** trendy i raport grupują po parze `(marker, unit)`, nie po samym `marker`. Klucz w `report.py::build_report` to `(r["marker"], r["unit"])`.

**Dlaczego:** różnicowanie morfologii (NEU/LYM/MONO/EOS/BASO) występuje w DWÓCH jednostkach pod tym samym kodem — raz jako odsetek (`%`), raz jako wartość bezwzględna (`tys/µl`). Naiwne grupowanie po samym `marker` zlałoby to w jeden „trend" (liczbowo bezsensowny ciąg „51.6 → 3.13 → 54.7"). Naiwny check policzył też „4 pomiary NEU" (niby próg S2 spełniony) — błędnie, bo to dwie serie po 2 punkty.

**Jak działa:** `structural_pipeline.py` zapisuje `unit` jako osobne pole per rekord — schemat już to rozróżnia, trzeba tylko użyć w grupowaniu.

**Pułapki:** pierwszy przypadek w projekcie, gdzie zliczanie „rekordów" dało inny wynik niż zliczanie „serii pomiarowych". Każde „ile pomiarów ma X" wymaga doprecyzowania — różnica bywa 2×.

### Próg S2 (≥3 pomiary) — mechanizm zbudowany, próg niezmierzony

**Decyzja:** trend/porównanie działają na realnych 2-punktowych seriach, ale formalne domknięcie S2 przesunięte do etapu 4.

**Dlaczego:** wolumen (14 dok., 3 daty) nie ma ani jednej serii marker+jednostka z 3 różnymi datami. To nie wada mechanizmu (zapytanie działa identycznie dla 2 i N punktów), tylko skutek małego wolumenu przed backfillem. Etap 4 ma własny punkt „Pomiar S1–S4" na realnych ~115–120 dok.

**Pułapki:** łatwo pomylić „mechanizm działa" z „kryterium spełnione" — pierwsze udowadnia się teraz kodem, drugie wymaga realnego wolumenu.

### Walidacja schematu pod BigQuery — co konkretnie sprawdzić

**Decyzja:** „gotowość pod BigQuery" = (1) każda linia to poprawny JSON, (2) każdy rekord ma ten sam zestaw kluczy, (3) każde pole ma spójny typ (właściwy typ + ewentualnie `None`, nigdy więcej).

**Dlaczego:** to dokładnie te trzy warunki, których złamanie wywala `bq load` — niespójna liczba kolumn albo pole raz-liczba-raz-tekst to najczęstsze przyczyny błędu schematu przy NEWLINE_DELIMITED_JSON. Sama „poprawność JSON" (za wąski test) tego nie łapie.

**Jak działa:** dla każdego pola zbiera się zbiór typów Pythona ze wszystkich rekordów (`{type(v).__name__ for v in ...}`) — wynik musi mieć rozmiar ≤2 (typ + `NoneType`). Dokładnie to, czego BigQuery oczekuje po polu `NULLABLE`.

**Pułapki:** load jest świadomie ręczny (PRD: „Automatyczny load do BigQuery" poza V1). Ten etap dostarcza walidację i pewność, że load się uda, nie wykonuje go za operatora.

### Instrukcja: ręczny load do BigQuery (konsola GCP) — procedura CYKLICZNA

**Decyzja:** load przez UI konsoli GCP (Create table → Upload), nie `bq` CLI — operator woli klikać i widzieć błędy w przeglądarce. Za każdym odświeżeniem danych — **zawsze pełny replace tabeli (Krok 0 + Krok 1), nigdy append**.

**Dlaczego replace, nie append:** `structural_pipeline.py` przy każdym uruchomieniu przetwarza WSZYSTKIE dokumenty od zera do migawki `data/store/YYYY-MM-DD-structural.ndjson` (nigdy wprost do zaufanego `structural-backfill.ndjson` — patrz notatka „Migawki datowane + scalenie ręczne" w `docs/stages/04-backfill.md`). Zaufany plik po scaleniu zawsze reprezentuje pełny stan magazynu, nie przyrost — więc append duplikowałby całą tabelę przy każdym cyklu. Replace jest bezpieczny, bo źródło prawdy to plik NDJSON, nie tabela w BigQuery.

**Jak działa:** pierwszy load (11 kolumn) przeszedł bez błędów. Schemat rozszerzony o `reference_note` (12. kolumna) — tabelę trzeba przeładować od zera (BigQuery nie dokłada kolumn przez UI uploadu). Ten sam Krok 0 + Krok 1 obowiązuje przy KAŻDYM odświeżeniu, nie tylko przy zmianie schematu.

**Krok 0 — usuń starą tabelę:** BigQuery Studio → nowe okno SQL query → uruchom (podmień nazwę):

```sql
DROP TABLE `projekt.dataset.structural_markers`;
```

Kasuje tabelę ze schematem i wierszami — nieodwracalne, ale bezpieczne (źródło prawdy to plik). Alternatywnie: Explorer → ⋮ → Delete.

**Krok 1 — załaduj od nowa:** ⋮ przy datasecie → Create table → Source „Upload" → plik `data/store/structural-backfill.ndjson` → File format `JSONL` → Table name jak poprzednio → Schema: odznacz „Auto detect", Edit as text, wklej (11 kolumn — `record_type` usunięty, zawsze był stałą „structural"):

```json
[
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

**Pułapki:** `exam_date` jako `DATE` (nie `STRING`) — format źródła zawsze `YYYY-MM-DD`, więc BigQuery przyjmie natywnie, bez rzutowania przy zapytaniach zakresowych.

### `reference_note` — surowa proza zamiast utraty progu referencyjnego

**Decyzja:** `parse_section_chunk` (Warstwa 2) zwraca 6. wartość — `note`. Wypełnia się WYŁĄCZNIE gdy `reference_low`/`reference_high` zostają puste, i tylko dla linii pasujących do wąskiego wzorca `^[≥≤<>]\s*=?\s*\d` (symbol porównania + cyfra).

**Dlaczego:** realny przypadek z lipidogramu — HDL/LDL wyrażają próg jako zdanie („≥ 40 mg/dl zgodnie z zaleceniami PTK"), czasem kilka progów zależnych od ryzyka pacjenta („<100 - bardzo duże ryzyko / <130 - duże"). Bez tego zdanie znikało — złamanie „nie gub po cichu". Świadomie NIE parsujemy tego na `low`/`high` — przy wielu progach wybór „tego właściwego" byłby zgadywaniem, gorszym niż `NULL`.

**Jak działa:** wzorzec łapie linię od symbolu porównania + cyfry niezależnie od reszty zdania. Świadomie NIE złapie stylu „Stężenie zalecane: powyżej 40 mg/dl" (inne sformułowanie, weryfikowane realnie). Wiele dopasowań w chunku łączy się przez „ / ".

**Pułapki:** (1) wzorzec musi być wąski — szerszy check „linia zawiera cyfrę" złapałby stopkę („Strona 1 z 2") jako fałszywy zakres (test na LDL potwierdził odrzucenie). (2) przypis „Wzór wg MDRD" przy eGFR nie ma cyfry na początku, więc nie trafia do `note` — sprawdzone testem. (3) efekt na 14 dok.: 12→9 rekordów bez żadnej informacji o zakresie; reszta to realny brak progu albo inne sformułowanie — świadomie zaakceptowane, nie gonimy każdego wariantu regexem.
