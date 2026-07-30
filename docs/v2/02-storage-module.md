# Etap 2 (V2) — `src/storage.py`, wspólny moduł

## Cel

Wydzielić z `report.py` wspólny moduł logiki domenowej — `load_records()` i rozpoznawanie identyfikatora markera (kod kanoniczny lub polska etykieta z `marker_labels.yml`) — do `src/storage.py`. Zgodnie z PRD V2 (Tech Constraints, „Reużycie kodu"): serwer MCP nie może importować ze skryptu CLI, więc ta logika musi żyć w osobnym module, z którego korzystają oba kanały (`report.py` i przyszły `mcp_server.py`), zamiast duplikować się w dwóch miejscach.

To fundament pod etap 3 (właściwe narzędzia `get_marker_trend`, `compare_markers`) — bez wydzielonego i przetestowanego modułu budowanie tych narzędzi powtórzyłoby dokładnie ten błąd duplikacji, którego PRD świadomie unika. Rozpoznawanie po etykiecie (nie tylko po kodzie) to nowa logika względem tego, co dziś istnieje w `report.py` — tam mapowanie działa wyłącznie kod→etykieta (do nagłówków raportu), nigdy w drugą stronę.

## Zakres / Definition of Done

- [x] `src/storage.py`: `load_records(store_path=STORE)` — przeniesione z `report.py`, bez zmiany logiki; `report.py` zaimportowany z `storage` zamiast trzymać własną kopię, zweryfikowane (`report.load_records is storage.load_records`, 260 rekordów odczytanych z zaufanego magazynu bez błędu)
- [x] `src/storage.py`: `resolve_marker(identyfikator)` — rozpoznaje kod kanoniczny LUB polską etykietę (odwrotne mapowanie do `marker_labels.yml`, bez rozróżniania wielkości liter); nieznany identyfikator → `MarkerNotFound` z podpowiedzią najbliższych dopasowań (`difflib.get_close_matches`), nigdy cicha pusta lista. Przy okazji: `load_labels()` też przeniesione do `storage.py` (duplikat w `report.py` usunięty) — ta sama dana potrzebna obu
- [x] `src/storage.py`: `group_by_unit(records)` — reużycie logiki `real_units`/`sub_groups` z `report.py` jako samodzielna funkcja; `report.py` zaimportowany zamiast trzymać duplikat inline. Zweryfikowane na `HGB` (jedna jednostka, scalone) i `NEU` (dwie realne jednostki `%`/`tys/µl` + rekordy bez jednostki w osobnej grupie), oraz pełnym `build_report()` bez zapisu na dysk
- [x] `report.py` zrefaktoryzowany: importuje `load_records`, `load_labels`, `group_by_unit` z `storage.py` — żadnej duplikowanej logiki domenowej nie zostało, tylko formatowanie specyficzne dla raportu (`fmt_value`, `fmt_range`, `flag`, `trend_arrow`, `build_report`)
- [x] Testy jednostkowe czystej logiki (PRD, warstwa 1 z 3 weryfikacji przed produkcją): `tests/test_storage.py`, `pytest` jako dev-dependency — identyfikacja po kodzie, po etykiecie (oba case-insensitive), nieznany identyfikator z podpowiedzią i bez; grupowanie po jednostce (jedna jednostka, wiele jednostek). 8 testów, literały syntetyczne, niezależne od realnych plików — wszystkie przechodzą
- [x] Regresja: `report.py` sprzed refaktoryzacji (`git show a11fc8a:src/report.py`) i wersja bieżąca uruchomione w pamięci na tym samym zaufanym magazynie (260 rekordów) — wygenerowany tekst raportu identyczny znak w znak (30865 znaków). Bez zapisu do `data/reports/` w trakcie testu — porównanie przez bezpośrednie wywołanie `build_report()`, nie przez `main()`

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

### `group_by_unit` — grupowanie po jednostce

**Decyzja:** logika `real_units`/`sub_groups`, dotąd inline w pętli `build_report`, wydzielona jako samodzielna funkcja `group_by_unit(records)` w `storage.py`; `report.py` woła ją zamiast trzymać kopię.

**Dlaczego:** PRD V2 wymaga, żeby `get_marker_trend`/`compare_markers` (etap 3) zwracały serie markera pogrupowane po jednostce dokładnie tą samą regułą co dziś raport — bez wydzielenia funkcja musiałaby powstać drugi raz w `mcp_server.py`.

**Jak działa:** licząc unikalne, niepuste jednostki w rekordach markera — przy ≤1 realnej jednostce wszystkie rekordy (w tym te bez jednostki) trafiają do jednej grupy; przy ≥2 realnych jednostkach (np. NEU w `%` i `tys/µl`) rekordy dzielą się dokładnie po swojej jednostce, a te bez jednostki lądują w osobnej grupie z kluczem `None` zamiast zgadywania, do której skali należą.

### Regresja raportu bez dotykania `data/reports/`

**Decyzja:** porównanie „przed/po" zrobione przez dynamiczny import starej wersji `report.py` (`git show <commit>:src/report.py` do pliku w scratchpadzie, `importlib.util.spec_from_file_location`) i wywołanie `build_report()` obu wersji w pamięci na tych samych danych — zero uruchomienia `main()`, zero zapisu na dysk.

**Dlaczego:** `main()` zapisuje zawsze pod `data/reports/YYYY-MM-DD-trendy.md`, niezależnie od źródła — dokładnie ten mechanizm, który realnie nadpisał raport w incydencie opisanym w `CLAUDE.md` projektu. Regresja nie potrzebowała w ogóle dotykać tej ścieżki, więc ryzyko zniknęło przez wybór metody, nie przez ostrożność w jej użyciu.

**Jak działa:** stara wersja modułu, załadowana z pliku spoza `src/`, liczy swoje `ROOT`/`STORE` z `Path(__file__)` — a `__file__` wskazuje wtedy na scratchpad, nie na projekt. Sam atrybut modułu (`report_before.STORE`) da się podmienić po załadowaniu, ale **domyślna wartość argumentu** funkcji (`store_path: Path = STORE`) jest wiązana raz, w momencie zdefiniowania funkcji — podmiana atrybutu modułu już na nią nie działa. Rozwiązanie: przekazać poprawną ścieżkę jawnie jako argument (`load_records(STORE)`), zamiast polegać na wartości domyślnej.

**Pułapki:** `load_labels()` w starej wersji odczytuje `LABELS` jako zmienną globalną wewnątrz ciała funkcji (nie jako argument domyślny) — tam podmiana atrybutu modułu po załadowaniu zadziałała od razu. Dwie pozornie identyczne konstrukcje (argument domyślny vs odczyt globala w ciele funkcji) zachowują się różnie wobec podmiany atrybutu modułu po fakcie — różnica, która ujawniła się dopiero przy pierwszym uruchomieniu (0 rekordów zamiast 260), nie przy czytaniu kodu.

**Pułapki:** żadnych nowych — to dosłowne przeniesienie istniejącej, już sprawdzonej logiki (V1, `03-storage-analysis.md`), nie nowa reguła biznesowa.
