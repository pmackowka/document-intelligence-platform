# Etap 3 (V2) — narzędzia MCP: `get_marker_trend`, `compare_markers`

## Cel

Zastąpić trywialne narzędzie testowe (`ping`) w `src/mcp_server.py` właściwymi narzędziami z PRD V2: `get_marker_trend(identyfikator)` i `compare_markers(lista identyfikatorów)`, zbudowanymi na `resolve_marker`, `load_records` i `group_by_unit` z `src/storage.py` (etap 2). To domyka lukę produktową PRD — Claude Desktop i inni klienci MCP dostają dostęp do tych samych danych, które dziś czyta wyłącznie Claude Code w terminalu.

Etap 1 dowiódł, że transport stdio i realny klient (Claude Desktop) się dogadują. Etap 2 wydzielił i przetestował czystą logikę domenową. Ten etap składa oba fundamenty w działający produkt — i dopiero on liczy się jako dowód Success Criteria PRD (S1, S2): sama zielona odpowiedź techniczna narzędzia nie wystarcza, potrzebne jest realne zapytanie end-to-end z Desktopa (PRD, „V1 pokazało, że »mechanizm działa« i »kryterium spełnione« to różne stwierdzenia").

## Zakres / Definition of Done

- [x] `get_marker_trend(identyfikator)` w `mcp_server.py` — wywołuje `resolve_marker`, a rozpoznany kod przekazuje do nowej `marker_series(code, records)` w `storage.py` (buduje na `load_records` + `group_by_unit`); zwraca `{status, marker, series: [{unit, records: [...]}]}` z surowymi polami (`exam_date`, `value`, `value_text`, `unit`, `reference_low`, `reference_high`, `reference_note`, `source_file`), bez interpretacji. Nierozpoznany identyfikator → `{status: "not_found", identifier, suggestions}`. Zweryfikowane bezpośrednim wywołaniem: marker z jedną jednostką (FERR), z trzema (NEU: brak/`%`/`tys/µl`), kod vs etykieta case-insensitive, literówka z podpowiedzią, kompletnie nieznany identyfikator bez podpowiedzi
- [ ] `compare_markers(lista identyfikatorów)` w `mcp_server.py` — ta sama logika identyfikacji/jednostek/braku interpretacji zastosowana do N markerów; zwraca N niezależnych serii, świadomie bez łączenia po dacie badania
- [ ] Nierozpoznany identyfikator w obu narzędziach → `MarkerNotFound` przechwycony i zwrócony jako czytelny status „nie znaleziono" z podpowiedzią najbliższych dopasowań, nie surowy traceback
- [ ] Zero logowania treści zapytań/odpowiedzi (identyfikator markera, wartości, daty) na dysk ani do stderr (PRD, Tech Constraints — Logowanie)
- [ ] Testy jednostkowe kontraktu narzędzi (PRD, warstwa 1 z 3 weryfikacji): kształt wyjścia dla markera z jedną serią, z wieloma seriami/jednostkami, nierozpoznany identyfikator; `compare_markers` dla ≥2 markerów
- [ ] Weryfikacja przez MCP Inspector (warstwa 2 z 3) — ręczne wywołanie obu narzędzi bez konfigurowania Desktopa
- [ ] Sign-off S1: realne zapytanie z Claude Desktop o trend markera z ≥3 pomiarami (np. „pokaż trend ferrytyny") — poprawna odpowiedź, bez ręcznego kroku pośredniego
- [ ] Sign-off S2: realne zapytanie z Claude Desktop porównujące ≥2 markery (np. „porównaj hemoglobinę i OB") — N niezależnych serii, bez ręcznego kroku pośredniego

## Notatki

_(puste — notatki powstają w trakcie realizacji powyższych kroków, nie z góry)_
