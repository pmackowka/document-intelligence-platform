# Etap 2 (V2) — `src/storage.py`, wspólny moduł

## Cel

Wydzielić z `report.py` wspólny moduł logiki domenowej — `load_records()` i rozpoznawanie identyfikatora markera (kod kanoniczny lub polska etykieta z `marker_labels.yml`) — do `src/storage.py`. Zgodnie z PRD V2 (Tech Constraints, „Reużycie kodu"): serwer MCP nie może importować ze skryptu CLI, więc ta logika musi żyć w osobnym module, z którego korzystają oba kanały (`report.py` i przyszły `mcp_server.py`), zamiast duplikować się w dwóch miejscach.

To fundament pod etap 3 (właściwe narzędzia `get_marker_trend`, `compare_markers`) — bez wydzielonego i przetestowanego modułu budowanie tych narzędzi powtórzyłoby dokładnie ten błąd duplikacji, którego PRD świadomie unika. Rozpoznawanie po etykiecie (nie tylko po kodzie) to nowa logika względem tego, co dziś istnieje w `report.py` — tam mapowanie działa wyłącznie kod→etykieta (do nagłówków raportu), nigdy w drugą stronę.

## Zakres / Definition of Done

- [x] `src/storage.py`: `load_records(store_path=STORE)` — przeniesione z `report.py`, bez zmiany logiki; `report.py` zaimportowany z `storage` zamiast trzymać własną kopię, zweryfikowane (`report.load_records is storage.load_records`, 260 rekordów odczytanych z zaufanego magazynu bez błędu)
- [x] `src/storage.py`: `resolve_marker(identyfikator)` — rozpoznaje kod kanoniczny LUB polską etykietę (odwrotne mapowanie do `marker_labels.yml`, bez rozróżniania wielkości liter); nieznany identyfikator → `MarkerNotFound` z podpowiedzią najbliższych dopasowań (`difflib.get_close_matches`), nigdy cicha pusta lista. Przy okazji: `load_labels()` też przeniesione do `storage.py` (duplikat w `report.py` usunięty) — ta sama dana potrzebna obu
- [x] `src/storage.py`: `group_by_unit(records)` — reużycie logiki `real_units`/`sub_groups` z `report.py` jako samodzielna funkcja; `report.py` zaimportowany zamiast trzymać duplikat inline. Zweryfikowane na `HGB` (jedna jednostka, scalone) i `NEU` (dwie realne jednostki `%`/`tys/µl` + rekordy bez jednostki w osobnej grupie), oraz pełnym `build_report()` bez zapisu na dysk
- [x] `report.py` zrefaktoryzowany: importuje `load_records`, `load_labels`, `group_by_unit` z `storage.py` — żadnej duplikowanej logiki domenowej nie zostało, tylko formatowanie specyficzne dla raportu (`fmt_value`, `fmt_range`, `flag`, `trend_arrow`, `build_report`)
- [ ] Testy jednostkowe czystej logiki (PRD, warstwa 1 z 3 weryfikacji przed produkcją): identyfikacja po kodzie, po etykiecie, nieznany identyfikator; grupowanie po jednostce (przypadek jednej jednostki i wielu jednostek)
- [ ] Regresja: raport wygenerowany po refaktoryzacji identyczny z raportem sprzed zmiany, na tym samym zaufanym magazynie

## Notatki

### Wydzielenie `load_records` i `load_labels` do `storage.py`

**Decyzja:** obie funkcje przeniesione z `report.py` do `src/storage.py` bez zmiany logiki; `report.py` importuje je stamtąd zamiast trzymać własne kopie.

**Dlaczego:** PRD V2 (Tech Constraints, „Reużycie kodu") wymaga, żeby serwer MCP nie importował ze skryptu CLI — a `report.py` i przyszły `mcp_server.py` potrzebują dokładnie tej samej logiki odczytu magazynu i etykiet, więc musi żyć w jednym wspólnym miejscu.

**Jak działa:** `from storage import ...` działa bez pakietu czy `__init__.py`, bo Python przy uruchomieniu skryptu dodaje katalog tego skryptu (`src/`) do `sys.path[0]` — ten sam mechanizm, którego `structural_pipeline.py` już używa (`from ocr import ocr_markdown`).

**Pułapki:** weryfikacja zrobiona przez bezpośrednie wywołanie `load_records()`/`load_labels()`, nie przez `main()` z `report.py` — `main()` zapisuje raport do `data/reports/YYYY-MM-DD-trendy.md` i mogłoby nadpisać istniejący plik z tego dnia (realny incydent opisany w `CLAUDE.md` projektu). Pełna regresja przez porównanie wygenerowanych raportów to osobny, celowo odłożony checkbox — wymaga świadomej zgody przed uruchomieniem `report.py`.

### `resolve_marker` — rozpoznawanie po kodzie lub etykiecie

**Decyzja:** dopasowanie bez rozróżniania wielkości liter do kodu kanonicznego LUB polskiej etykiety z `marker_labels.yml` (mapowanie odwrotne do istniejącego kod→etykieta); przy braku dopasowania — `MarkerNotFound` z podpowiedzią najbliższych dopasowań (`difflib.get_close_matches`), nigdy cicha pusta lista.

**Dlaczego:** PRD wprost nazywa ryzyko mylenia literówki z brakiem danych — model wywołujący narzędzie MCP może podać zarówno kod (`HGB`), jak i polską nazwę (`Hemoglobina`), i oba muszą się rozstrzygać spójnie, z jawnym błędem zamiast domysłu.

**Jak działa:** funkcja buduje dwa zlowercase'owane słowniki (kod→kod, etykieta→kod), sprawdza dokładne dopasowanie w obu; przy braku trafienia woła `difflib.get_close_matches` (cutoff 0.6) na sumie kluczy z obu słowników i zwraca kody odpowiadające najbliższym dopasowaniom.

**Pułapki:** przed napisaniem fuzzy-matchingu sprawdzone programowo, że w `marker_labels.yml` (107 kodów) nie ma kolizji — żadna etykieta nie powtarza się dla dwóch różnych kodów, żaden kod nie jest jednocześnie cudzą etykietą poza samo-etykietowaniem (`MCV`→„MCV" itd.). Bez tej weryfikacji odwrotne mapowanie mogłoby cicho zgubić jeden z kodów przy kolizji kluczy.
