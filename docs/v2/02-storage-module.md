# Etap 2 (V2) — `src/storage.py`, wspólny moduł

## Cel

Wydzielić z `report.py` wspólny moduł logiki domenowej — `load_records()` i rozpoznawanie identyfikatora markera (kod kanoniczny lub polska etykieta z `marker_labels.yml`) — do `src/storage.py`. Zgodnie z PRD V2 (Tech Constraints, „Reużycie kodu"): serwer MCP nie może importować ze skryptu CLI, więc ta logika musi żyć w osobnym module, z którego korzystają oba kanały (`report.py` i przyszły `mcp_server.py`), zamiast duplikować się w dwóch miejscach.

To fundament pod etap 3 (właściwe narzędzia `get_marker_trend`, `compare_markers`) — bez wydzielonego i przetestowanego modułu budowanie tych narzędzi powtórzyłoby dokładnie ten błąd duplikacji, którego PRD świadomie unika. Rozpoznawanie po etykiecie (nie tylko po kodzie) to nowa logika względem tego, co dziś istnieje w `report.py` — tam mapowanie działa wyłącznie kod→etykieta (do nagłówków raportu), nigdy w drugą stronę.

## Zakres / Definition of Done

- [ ] `src/storage.py`: `load_records(store_path=STORE)` — przeniesione z `report.py`, bez zmiany logiki
- [ ] `src/storage.py`: `resolve_marker(identyfikator)` — rozpoznaje kod kanoniczny LUB polską etykietę (odwrotne mapowanie do `marker_labels.yml`); nieznany identyfikator → jawny błąd/`None`, nigdy cicha pusta lista (PRD, tabela ryzyk — mylenie literówki z brakiem danych)
- [ ] `src/storage.py`: grupowanie rekordów markera po jednostce — reużycie logiki `real_units`/`sub_groups` już istniejącej w `report.py`, jako samodzielna funkcja
- [ ] `report.py` zrefaktoryzowany: importuje `load_records` (i pozostałą reużywalną logikę) z `storage.py` zamiast trzymać własną kopię
- [ ] Testy jednostkowe czystej logiki (PRD, warstwa 1 z 3 weryfikacji przed produkcją): identyfikacja po kodzie, po etykiecie, nieznany identyfikator; grupowanie po jednostce (przypadek jednej jednostki i wielu jednostek)
- [ ] Regresja: raport wygenerowany po refaktoryzacji identyczny z raportem sprzed zmiany, na tym samym zaufanym magazynie

## Notatki

_(puste — notatki powstają w trakcie realizacji powyższych kroków, nie z góry)_
