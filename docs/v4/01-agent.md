# Etap 1 (V4) — agent nad serwerem MCP z V2

## Cel

Zbudować `src/agent.py` — pierwszy realny skrypt używający Claude Agent SDK do orkiestracji dwóch istniejących narzędzi MCP z V2 (`get_marker_trend`, `compare_markers`), zgodnie z konfiguracją `ClaudeAgentOptions` już zweryfikowaną empirycznie podczas rundy review PRD (`docs/v4/prd.md`, notatka w `docs/v4/00-planning.md`).

Najtrudniejsze niewiadome — czy framework w ogóle działa wyłącznie na subskrypcji Claude Pro (bez klucza API), i czy da się zawęzić toolset agenta oraz wyłączyć auto-memory — są już rozstrzygnięte spike'em wykonanym w trakcie sesji sokratejskiej i rundy review. Ten etap formalizuje tamten ad-hoc test w stały moduł projektu i dowodzi obu kryteriów sukcesu (S1, S2) z PRD na realnych danych — dopiero to liczy się jako spełnienie kryteriów, nie sama zielona odpowiedź techniczna.

## Zakres / Definition of Done

- [ ] `src/agent.py`: konfiguracja `ClaudeAgentOptions` (`tools=[]`, `mcp_servers` wskazujący na `src/mcp_server.py`, `allowed_tools` dla `get_marker_trend`/`compare_markers`, `setting_sources=[]`, `system_prompt` z `exclude_dynamic_sections=True`) — przeniesiona z ad-hoc testu w rundzie review do stałego modułu projektu, tryb jednorazowy (`query()`)
- [ ] Generowanie nazwy pliku wyjściowego: slug z treści zapytania + ochrona przed nadpisaniem (licznik `-2`, `-3`... przy kolizji tego samego dnia) — zapis do `data/agent/YYYY-MM-DD-<temat>.md`
- [ ] Testy jednostkowe (warstwa 1 z 3 weryfikacji z PRD): generowanie slugów, ochrona przed kolizją nazw plików, kształt konfiguracji `ClaudeAgentOptions`
- [ ] Izolowana weryfikacja konfiguracji agenta (warstwa 2 z 3): potwierdzenie, że dostępne narzędzia to dokładnie te trzy z serwera V2 i że wywołanie nie blokuje się na prośbie o uprawnienia — częściowo już zrobione ad-hoc w rundzie review PRD, do powtórzenia jako formalny krok na `src/agent.py`
- [ ] Sign-off S1: realne zapytanie o jeden marker bez wskazania narzędzia (np. „jak wygląda mój poziom ferrytyny w czasie") — agent sam wybiera narzędzie, poprawnie identyfikuje marker, zwraca sensowną odpowiedź na realnych danych
- [ ] Sign-off S2: realne, otwarte zapytanie wymagające planowania wieloetapowego (np. „przygotuj mnie do wizyty u nefrologa") — agent planuje potrzebne markery, wywołuje oba narzędzia, syntetyzuje wynik w raport zapisany do `data/agent/` z realnymi danymi i pytaniami do lekarza

## Notatki

_(puste — notatki powstają w trakcie realizacji powyższych kroków, nie z góry)_
