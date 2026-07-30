# Etap 0 (V4) — Planowanie

## Cel

Domknąć fazę przedimplementacyjną Version 4 tym samym trybem, co V1 i V2: sesja sokratejska → PRD zatwierdzony → dopiero wtedy pierwszy etap implementacyjny. Ten plik **nie jest planem implementacji** — to jedyny etap, który istnieje, dopóki `docs/v4/prd.md` nie ma statusu „zatwierdzony".

Zalążek zakresu (do zweryfikowania/rozszerzenia w sesji sokratejskiej, nie do traktowania jako ustalone): agent zdolny wyszukiwać dokumenty, analizować historię, wykonywać wieloetapowe zadania i planować kroki — zbudowany nad serwerem MCP z V2 (`get_marker_trend`, `compare_markers`), lokalnie, **bez przechodzenia przez V3** (przeniesienie do chmury świadomie pominięte na razie — koszt GCP/VPS nieuzasadniony na tym etapie, decyzja odnotowana w `docs/roadmap.md`, sekcja „Zasada kolejności"). Framework do wyboru w sesji sokratejskiej: LangGraph, OpenAI Agents SDK lub Claude Agent SDK (naturalny kandydat przy istniejącym stacku). Pełny opis i diagram: `docs/roadmap.md`, sekcja „Version 4 — Architektura agentowa".

## Zakres / Definition of Done

- [x] Sesja sokratejska V4 (zakres, granice, kryteria sukcesu, wybór frameworka agentowego) — skill `grilling`; ustalenia: Claude Agent SDK (potwierdzone spike'em na tej maszynie — zero klucza API, zużycie z puli subskrypcji Pro), zawężony toolset (tylko klient MCP), tryb jednorazowy, wyjście do `data/agent/`, S1/S2, wyłączone auto-memory
- [x] `docs/v4/prd.md` — pierwsza wersja (v4.0) spisana
- [x] Review PRD v4 — runda 1: trzy luki self-critique rozstrzygnięte i zweryfikowane empirycznie (spike na `ClaudeAgentOptions` — zawężenie toolsetu, wyłączenie auto-memory, naprawiony blok na uprawnieniach w trybie jednorazowym); nazewnictwo plików z ochroną przed nadpisaniem; trójwarstwowa strategia weryfikacji. PRD → v4.1
- [x] PRD v4 zatwierdzony → status „zatwierdzony" w nagłówku pliku. Operator uznał rundę 1 za wystarczającą i świadomie pominął rundę 2, analogicznie do PRD V2
- [x] Pierwszy plik etapu implementacyjnego V4 (`docs/v4/01-agent.md`, płasko obok `prd.md`, ta sama metodologia co V1/V2) założony na podstawie zatwierdzonego PRD

## Notatki

### Runda review z empiryczną weryfikacją, nie tylko pytaniami

**Decyzja:** dwie z trzech luk zgłoszonych w self-critique PRD v4.0 rozstrzygnięte przez realny spike (sprawdzenie pól `ClaudeAgentOptions` w kodzie SDK i uruchomienie testowych zapytań), nie przez samą rozmowę z operatorem.

**Dlaczego:** luka „czy `ClaudeAgentOptions` w ogóle pozwala zawęzić toolset i wyłączyć pamięć" to pytanie o fakt techniczny, nie o decyzję operatora — dokładnie taki fakt, który zgodnie z instrukcją skilla `grilling` należy sprawdzić w środowisku, a nie zgadywać ani pytać.

**Jak działa:** sprawdzenie `dataclasses.fields(ClaudeAgentOptions)` ujawniło dokładne nazwy i docstringi opcji (`tools`, `setting_sources`, `system_prompt.exclude_dynamic_sections`), a próbne wywołanie `query()` z tą konfiguracją na realnym serwerze MCP z V2 potwierdziło działanie end-to-end — w tym jedną przeszkodę (blokada na uprawnieniach w trybie jednorazowym), której sama lektura dokumentacji by nie ujawniła.

**Pułapki:** `allowed_tools=[]` brzmi jak „nic nie pozwól", ale wcale nie ogranicza dostępności narzędzi — to lista auto-zatwierdzania (pomija tylko prompt o uprawnienia). Właściwym polem do ograniczenia dostępnych narzędzi jest `tools` (pusta lista = brak wbudowanych narzędzi), nie `allowed_tools`. Dwa różne pola, łatwo pomylić po samych nazwach.
