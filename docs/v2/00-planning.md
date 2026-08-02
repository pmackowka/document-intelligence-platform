# Etap 0 (V2) — Planowanie

## Cel

Domknąć fazę przedimplementacyjną Version 2 tym samym trybem, co V1: sesja sokratejska → PRD zatwierdzony → dopiero wtedy pierwszy etap implementacyjny. Ten plik **nie jest planem implementacji** — to jedyny etap, który istnieje, dopóki `docs/v2/prd.md` nie ma statusu „zatwierdzony".

Zalążek zakresu (do zweryfikowania/rozszerzenia w sesji sokratejskiej, nie do traktowania jako ustalone): projekt staje się serwerem MCP udostępniającym znormalizowane dane medyczne klientom (Claude Code, Claude Desktop, inne klienty MCP) — narzędzia typu `get_marker_trend`, `compare_markers` zamiast ręcznego czytania plików NDJSON z dysku. Pełny, zatwierdzony zakres: `docs/v2/prd.md`. Diagram: `README.md`, sekcja „Architektura — mapa wersji".

## Zakres / Definition of Done

- [x] Sesja sokratejska V2 (zakres, granice, kryteria sukcesu, wybór SDK/transportu MCP) — `/grill-with-docs`, ustalenia w `CONTEXT.md` i `docs/adr/0001`, `docs/adr/0002`
- [x] `docs/v2/prd.md` — pierwsza wersja (v2.0) spisana
- [x] Review PRD v2 (rundy jak przy V1 — `docs/v1/prd.md` miało 2 rundy przed zatwierdzeniem)
  - [x] Runda 1 — 4 luki rozstrzygnięte (weryfikacja serwera, reużycie kodu, logowanie, ciągłość workflow terminalowego); PRD → v2.1
  - [x] ~~Runda 2~~ — świadomie pominięta: operator uznał rundę 1 za wystarczającą i zatwierdził PRD bez niej
- [x] PRD v2 zatwierdzony → status „zatwierdzony" w nagłówku pliku
- [x] Pierwszy plik etapu implementacyjnego V2 (`docs/v2/01-...md`, płasko obok `prd.md` — bez podfolderu `stages/`, ta sama metodologia co V1) założony na podstawie zatwierdzonego PRD — `docs/v2/01-mcp-spike.md`

## Notatki

### Rundy review PRD — ten sam mechanizm co sesja sokratejska pierwotna

**Decyzja:** rundy review PRD (analogiczne do 2 rund V1) prowadzone tym samym skillem `grilling` co pierwotna sesja sokratejska, nie osobnym trybem „review" — z tą różnicą, że materiał do pytań pochodzi nie z pustego zakresu, tylko z luk, które sama zgłosiłam we wcześniejszej rundzie (self-critique jako wejście do kolejnej rundy).

**Dlaczego:** te same zasady (pytanie po pytaniu, rekomendacja, fakty z narzędzi a nie z pamięci, decyzje wyłącznie od operatora) mają zastosowanie niezależnie od tego, czy to pierwsza sesja, czy domykanie luk — nie ma powodu do osobnego trybu.

**Pułapki:** deklaracja w czacie, że runda się odbyła i PRD zaktualizowane, bez dotknięcia pliku etapu (`00-planning.md`) — nie liczy się jako wykonane, zgodnie z zasadą workflow z `CLAUDE.md` projektu. Złapane dopiero przez pytanie operatora, nie samodzielnie — do pilnowania przy każdej kolejnej rundzie.
