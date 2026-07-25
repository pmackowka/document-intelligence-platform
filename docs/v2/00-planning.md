# Etap 0 (V2) — Planowanie

## Cel

Domknąć fazę przedimplementacyjną Version 2 tym samym trybem, co V1: sesja sokratejska → PRD zatwierdzony → dopiero wtedy pierwszy etap implementacyjny. Ten plik **nie jest planem implementacji** — to jedyny etap, który istnieje, dopóki `docs/v2/prd.md` nie ma statusu „zatwierdzony".

Zalążek zakresu (do zweryfikowania/rozszerzenia w sesji sokratejskiej, nie do traktowania jako ustalone): projekt staje się serwerem MCP udostępniającym znormalizowane dane medyczne klientom (Claude Code, Claude Desktop, inne klienty MCP) — narzędzia typu `get_marker_trend`, `compare_markers` zamiast ręcznego czytania plików NDJSON z dysku. Pełny opis i diagram: `docs/roadmap.md`, sekcja „Version 2 — MCP server".

## Zakres / Definition of Done

- [ ] Sesja sokratejska V2 (zakres, granice, kryteria sukcesu, wybór SDK/transportu MCP)
- [ ] `docs/v2/prd.md` — pierwsza wersja (v2.0) spisana
- [ ] Review PRD v2 (rundy jak przy V1 — `docs/v1/prd.md` miało 2 rundy przed zatwierdzeniem)
- [ ] PRD v2 zatwierdzony → status „zatwierdzony" w nagłówku pliku
- [ ] Pierwszy plik etapu implementacyjnego V2 (`docs/v2/01-...md`, płasko obok `prd.md` — bez podfolderu `stages/`, ta sama metodologia co V1) założony na podstawie zatwierdzonego PRD

## Notatki

_(puste — notatki powstają w trakcie realizacji powyższych kroków, nie z góry)_
