# Etap 3 (V2) — narzędzia MCP: `get_marker_trend`, `compare_markers`

## Cel

Zastąpić trywialne narzędzie testowe (`ping`) w `src/mcp_server.py` właściwymi narzędziami z PRD V2: `get_marker_trend(identyfikator)` i `compare_markers(lista identyfikatorów)`, zbudowanymi na `resolve_marker`, `load_records` i `group_by_unit` z `src/storage.py` (etap 2). To domyka lukę produktową PRD — Claude Desktop i inni klienci MCP dostają dostęp do tych samych danych, które dziś czyta wyłącznie Claude Code w terminalu.

Etap 1 dowiódł, że transport stdio i realny klient (Claude Desktop) się dogadują. Etap 2 wydzielił i przetestował czystą logikę domenową. Ten etap składa oba fundamenty w działający produkt — i dopiero on liczy się jako dowód Success Criteria PRD (S1, S2): sama zielona odpowiedź techniczna narzędzia nie wystarcza, potrzebne jest realne zapytanie end-to-end z Desktopa (PRD, „V1 pokazało, że »mechanizm działa« i »kryterium spełnione« to różne stwierdzenia").

## Zakres / Definition of Done

- [x] `get_marker_trend(identyfikator)` w `mcp_server.py` — wywołuje `resolve_marker`, a rozpoznany kod przekazuje do nowej `marker_series(code, records)` w `storage.py` (buduje na `load_records` + `group_by_unit`); zwraca `{status, marker, series: [{unit, records: [...]}]}` z surowymi polami (`exam_date`, `value`, `value_text`, `unit`, `reference_low`, `reference_high`, `reference_note`, `source_file`), bez interpretacji. Nierozpoznany identyfikator → `{status: "not_found", identifier, suggestions}`. Zweryfikowane bezpośrednim wywołaniem: marker z jedną jednostką (FERR), z trzema (NEU: brak/`%`/`tys/µl`), kod vs etykieta case-insensitive, literówka z podpowiedzią, kompletnie nieznany identyfikator bez podpowiedzi
- [x] `compare_markers(lista identyfikatorów)` w `mcp_server.py` — `load_records()` wołane raz, potem `resolve_marker` + `marker_series` per identyfikator; zwraca `{results: [{status, identifier, marker, series}, ...]}`, N niezależnych serii, świadomie bez łączenia po dacie. Zweryfikowane: mieszanka znany/nieznany/literówka w jednym wywołaniu, lista pusta → `{results: []}`
- [x] Nierozpoznany identyfikator w obu narzędziach → `MarkerNotFound` przechwycony i zwrócony jako czytelny status „nie znaleziono" z podpowiedzią najbliższych dopasowań, nie surowy traceback — zrobione przy okazji implementacji obu narzędzi (`try/except` w `get_marker_trend` i w pętli `compare_markers`), zweryfikowane wcześniej testami literówki i kompletnie nieznanego identyfikatora
- [x] Zero logowania treści zapytań/odpowiedzi (identyfikator markera, wartości, daty) na dysk ani do stderr (PRD, Tech Constraints — Logowanie) — zweryfikowane przez grep na `print(`/`logging`/`stderr`/`stdout`/zapis w `mcp_server.py` i `storage.py`: jedyny `open()` to odczyt zaufanego magazynu w `load_records`, brak jakiegokolwiek printa czy loggera
- [x] Testy jednostkowe kontraktu narzędzi (PRD, warstwa 1 z 3 weryfikacji): `tests/test_mcp_server.py` — kształt wyjścia dla markera z jedną serią (HGB), z wieloma seriami/jednostkami (NEU: `%`/`tys/µl`), nierozpoznany identyfikator; `compare_markers` dla 2 znanych markerów i dla mieszanki znany/nieznany. `load_records` podmieniony (monkeypatch) na literały syntetyczne — testy niezależne od prywatnego magazynu; `resolve_marker` korzysta z realnego `marker_labels.yml` (plik domenowy, nie PII, już przetestowany osobno)
- [x] Weryfikacja przez MCP Inspector (warstwa 2 z 3) — ręczne wywołanie obu narzędzi bez konfigurowania Desktopa. Potwierdzone: `get_marker_trend("Ferrytyna")` → `ok`/`FERR` z serią; `get_marker_trend("xydd")` → `not_found` bez podpowiedzi; `compare_markers(["Hemoglobina", "OB"])` → dwie w pełni niezależne serie (HGB 4 pomiary, ESR/OB 3 pomiary, różne daty)
- [ ] Sign-off S1: realne zapytanie z Claude Desktop o trend markera z ≥3 pomiarami (np. „pokaż trend ferrytyny") — poprawna odpowiedź, bez ręcznego kroku pośredniego
- [ ] Sign-off S2: realne zapytanie z Claude Desktop porównujące ≥2 markery (np. „porównaj hemoglobinę i OB") — N niezależnych serii, bez ręcznego kroku pośredniego

## Notatki

### `get_marker_trend` i `marker_series` — kształt wyjścia

**Decyzja:** `get_marker_trend` samo tylko wywołuje `resolve_marker` i przechwytuje `MarkerNotFound`; dla rozpoznanego kodu buduje wyjście przez nową `marker_series(code, records)` w `storage.py`, nie inline w narzędziu MCP.

**Dlaczego:** ta sama logika (filtrowanie po kodzie, grupowanie po jednostce, spłaszczenie do surowych pól z PRD) jest potrzebna też `compare_markers` — wydzielenie do `storage.py` unika duplikacji między dwoma narzędziami, zgodnie z tą samą zasadą reużycia co przy `report.py` w etapie 2.

**Jak działa:** `marker_series` filtruje magazyn po `marker == code`, woła `group_by_unit`, i dla każdej grupy zwraca `{unit, records}`, gdzie każdy rekord ma dokładnie 8 pól z PRD (`exam_date`, `value`, `value_text`, `unit`, `reference_low`, `reference_high`, `reference_note`, `source_file`) — dodatkowe pola surowego rekordu (`panel`, `marker_raw`) odpadają. Serie posortowane po jednostce, rekordy w obrębie serii po dacie badania.

### `compare_markers` — N niezależnych serii

**Decyzja:** `load_records()` woła się raz na całe wywołanie (nie per identyfikator), a każdy identyfikator z listy przechodzi tę samą ścieżkę co `get_marker_trend` (resolve → `marker_series`), z wynikiem dopisywanym do wspólnej listy `results`.

**Dlaczego:** PRD wprost wymaga N niezależnych serii bez łączenia po dacie — różne markery badane są zwykle innego dnia, więc dopasowanie dat wymagałoby zgadywania, które pomiary „odpowiadają sobie".

**Jak działa:** pojedynczy nierozpoznany identyfikator nie przerywa całego wywołania — ląduje jako `{status: "not_found", ...}` w liście wyników, pętla idzie dalej (`continue`) do kolejnych identyfikatorów.

### Obsługa nieznanego identyfikatora — jawny status, nie traceback

**Decyzja:** oba narzędzia łapią `MarkerNotFound` w `try/except` i zwracają `{status: "not_found", identifier, suggestions}` zamiast pozwolić wyjątkowi propagować się jako surowy traceback do klienta MCP.

**Dlaczego:** model wywołujący narzędzie musi dostać czytelny sygnał „nie znaleziono" z podpowiedzią, nie nieprzetworzony błąd Pythona bez informacji, co zrobić dalej.

### Zero logowania treści zapytań — weryfikacja przez grep

**Decyzja:** weryfikacja zrobiona przez `grep` na `print(`/`logging`/`stderr`/`stdout`/`open(` w `mcp_server.py` i `storage.py`, nie przez czytanie kodu linijka po linijce.

**Jak działa:** jedyne trafienie to `store_path.open()` w `load_records` — odczyt zaufanego magazynu, nie zapis ani log. Narzędzia zwracają dane wyłącznie jako wynik funkcji (FastMCP serializuje go do odpowiedzi JSON-RPC) — nie ma osobnego kanału, którym treść zapytania mogłaby wyciec na dysk czy do stderr.

### Weryfikacja przez MCP Inspector

**Jak działa:** ten sam mechanizm co w etapie 1 (`uv run mcp dev src/mcp_server.py`), tym razem z trzema narzędziami na liście zamiast jednego.

Kroki do powtórzenia:

1. `cd /Users/p/Documents/dev/Document-Intelligence-Platform`
2. `uv run mcp dev src/mcp_server.py` — poczekać na link z tokenem
3. Otworzyć URL, karta serwera „uv" → toggle na „Connected"
4. Zakładka „Tools" — na liście: `ping`, `get_marker_trend`, `compare_markers`
5. `get_marker_trend`, pole `identyfikator` = `Ferrytyna` → „Execute Tool" → oczekiwane `status: "ok"`, `marker: "FERR"`, `series` z rekordami
6. `get_marker_trend`, pole `identyfikator` = nieznany identyfikator (np. `xyz123`) → oczekiwane `status: "not_found"` z `suggestions`
7. `compare_markers`, pole `identyfikatory` = lista np. `["Hemoglobina", "OB"]` → oczekiwane `results` z dwiema niezależnymi seriami
8. `Ctrl+C` zamyka Inspector

**Pułapki:** brak nowych — te same co w etapie 1 (Inspector to osobny proces webowy, trzeba go świadomie zatrzymać, inaczej zostaje w tle i trzyma port).
