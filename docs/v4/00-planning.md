# Etap 0 (V4) — Planowanie

## Cel

Domknąć fazę przedimplementacyjną Version 4 tym samym trybem, co V1 i V2: sesja sokratejska → PRD zatwierdzony → dopiero wtedy pierwszy etap implementacyjny. Ten plik **nie jest planem implementacji** — to jedyny etap, który istnieje, dopóki `docs/v4/prd.md` nie ma statusu „zatwierdzony".

Zalążek zakresu (do zweryfikowania/rozszerzenia w sesji sokratejskiej, nie do traktowania jako ustalone): agent zdolny wyszukiwać dokumenty, analizować historię, wykonywać wieloetapowe zadania i planować kroki — zbudowany nad serwerem MCP z V2 (`get_marker_trend`, `compare_markers`), lokalnie, **bez przechodzenia przez V3** (przeniesienie do chmury świadomie pominięte na razie — koszt GCP/VPS nieuzasadniony na tym etapie, decyzja odnotowana w `docs/roadmap.md`, sekcja „Zasada kolejności"). Framework do wyboru w sesji sokratejskiej: LangGraph, OpenAI Agents SDK lub Claude Agent SDK (naturalny kandydat przy istniejącym stacku). Pełny opis i diagram: `docs/roadmap.md`, sekcja „Version 4 — Architektura agentowa".

## Zakres / Definition of Done

- [ ] Sesja sokratejska V4 (zakres, granice, kryteria sukcesu, wybór frameworka agentowego) — skill `grilling` (`/grill-with-docs`), analogicznie do V1/V2
- [ ] `docs/v4/prd.md` — pierwsza wersja spisana
- [ ] Review PRD v4 (rundy jak przy V1/V2 — do ustalenia w trakcie, ile rund potrzeba)
- [ ] PRD v4 zatwierdzony → status „zatwierdzony" w nagłówku pliku
- [ ] Pierwszy plik etapu implementacyjnego V4 (`docs/v4/01-...md`, płasko obok `prd.md`, ta sama metodologia co V1/V2) założony na podstawie zatwierdzonego PRD

## Notatki

_(puste — notatki powstają w trakcie realizacji powyższych kroków, nie z góry)_
