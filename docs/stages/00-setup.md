# Etap 0 — Setup środowiska

## Cel
Działające fundamenty: repozytorium git, środowisko Python, lokalny n8n, smoke test `claude -p`.

## Zakres / Definition of Done
- [x] `git init` + pierwszy commit (PRD, CLAUDE.md, struktura docs) — 2026-07-17, commit `2e5e144`, remote github.com/pmackowka/Document-Intelligence-Platform
- [x] Struktura projektu (`config/`, `src/`, `data/{raw,pending,store,reports}`) — 2026-07-17; drzewo i reguła prywatności ścieżek w CLAUDE.md
- [x] Środowisko Python (uv) — 2026-07-18; uv 0.11.29 (brew), Python 3.11.4, `uv sync` → `.venv/` + `uv.lock`, weryfikacja `uv run python` OK
- [x] `data/` w `.gitignore` — dokumenty medyczne nigdy nie trafiają do repo — 2026-07-17, commit `2e5e144`; konwencja rozszerzona w `2b1d527`
- [x] n8n uruchomiony lokalnie (Docker Compose, v2.27.4) + dostęp Claude Code przez serwer MCP — 2026-07-18, scope local w `~/.claude.json`
- [ ] Pierwszy testowy workflow n8n (przez narzędzia n8n MCP — wymaga restartu sesji, by narzędzia się załadowały)
- [ ] Smoke test: wywołanie `claude -p "..."` z Pythona (subprocess), w tym `--model haiku`
- [ ] (osobno, po MCP) upgrade n8n z 2.27.4 do najnowszej — `docker compose pull && up -d`, re-test endpointu MCP

## Notatki

### Git i repozytorium zdalne
**Decyzja:** git od pierwszego dnia, z prywatnym remote na GitHubie.
**Dlaczego:** metoda „PRD jako living document" wymaga commitów przy każdej zmianie zakresu; dokumentacja zawiera realne informacje zdrowotne właściciela → repo musi zostać prywatne (publiczna wersja portfolio = osobny, zredagowany wariant).
**Jak działa:** weryfikacja prywatności repo bez `gh`: `curl -s -o /dev/null -w "%{http_code}" https://api.github.com/repos/<owner>/<repo>` — `404` bez autoryzacji oznacza repo prywatne (lub nieistniejące), `200` = publiczne.
**Pułapki:** `gh` CLI nie jest zainstalowane na tej maszynie — `brew install gh` przy domykaniu etapu.

### Struktura folderów i prywatność ścieżek
**Decyzja:** szkielet folderów utworzony z góry, przed kodem; `data/` ignorowane w `.gitignore` w całości (jeden wpis), nie per-plik.
**Dlaczego:** fizycznie istniejąca struktura egzekwuje regułę prywatności (`data/` = treść medyczna, poza gitem) lepiej niż sam zapis w CLAUDE.md — przyszła sesja nie wymyśli własnych ścieżek. Ignorowanie całego `data/` = „nowy artefakt medyczny automatycznie poza gitem" bez pamiętania o aktualizacji `.gitignore`. Pliki powstają dopiero w swoich etapach — bez stubów na zapas.
**Jak działa:** git nie śledzi pustych folderów → `.gitkeep` w `config/` i `src/`. Ścieżki ignorowane (`data/*`) nie istnieją w świeżym klonie w ogóle, więc kod pipeline'u musi tworzyć je przez `mkdir -p` przy starcie.

### Środowisko Python (uv)
**Decyzja:** `uv` zamiast `pip` + `venv` + `poetry`; instalacja przez Homebrew (nie skrypt curl). Zależności domenowe (Docling, Presidio, spaCy) **nie** instalowane teraz — dojdą w etapach 1 i 4.
**Dlaczego:** jedno narzędzie (środowisko, zależności, lockfile, wersja Pythona), znacznie szybsze przy ciężkim stacku; `uv.lock` w repo → reprodukowalne środowisko z klona jedną komendą. Homebrew: aktualizacje przez `brew upgrade` razem z resztą narzędzi. Etap 0 stawia tylko fundament (reguła „bez stubów na zapas").
**Jak działa:** `uv sync` czyta `pyproject.toml`, tworzy `.venv/` i zapisuje dokładne wersje do `uv.lock`. `uv run <komenda>` sam aktywuje `.venv` — bez ręcznego `source .venv/bin/activate` jak przy klasycznym `venv`.
**Pułapki:** `.venv/` jest w `.gitignore` (odtwarzalne z locka, duże) — do repo idą `pyproject.toml` + `uv.lock`, nie samo środowisko.

### Dostęp Claude Code do n8n (serwer MCP)
**Decyzja:** dostęp przez **wbudowany serwer MCP n8n** (nie zewnętrzny proces npx), zasięg **local** (per projekt), token reuse z projektu Learning-Plan.
**Dlaczego:** local zamiast global, bo to serwer HTTP — global oznaczałby próbę połączenia z `localhost:5678` w każdej sesji każdego projektu (szum, gdy n8n nie działa). Reuse tokenu: zweryfikowany, localhost, niskie ryzyko — dedykowany token dla niezależnego unieważniania opcjonalnie później.
**Jak działa:** MCP typu `http`, endpoint `http://localhost:5678/mcp-server/http`, autoryzacja nagłówkiem `Bearer <JWT>`. Serwer („n8n MCP Server" v1.1.0) wystawia `tools` + `resources` do budowania workflow przez n8n Workflow SDK. Dodanie: `claude mcp add n8n-mcp --scope local --transport http <url> --header "Authorization: Bearer <token>"`. Serwery MCP ładują się przy starcie sesji — po dodaniu potrzebny restart, by narzędzia `mcp__n8n-mcp__*` były dostępne.
**Pułapki:** token to sekret — konfiguracja trafia do `~/.claude.json` (poza repo), **nigdy** do `.mcp.json` w repo (byłby JWT w gicie, sprzeczne z „zero sekretów"). Weryfikacja połączenia: `claude mcp list` → status Connected.

### Dokumentacja i konwencje projektu
**Decyzja:** reguły przekrojowe (workflow etapów, Mermaid, ścieżki) w CLAUDE.md, szczegóły w docs.
**Dlaczego:** CLAUDE.md jest ładowany automatycznie do każdej sesji — to jedyne miejsce z gwarancją przeczytania.
**Jak działa:** CLAUDE.md vs docs = progressive disclosure — krótka reguła zawsze w kontekście, pełna instrukcja doczytywana na żądanie (ten sam mechanizm co skille w Claude Code).
**Pułapki:** deklaracja w czacie ≠ wykonanie — model raz napisał „git init odhaczony rzeczywistością", nie edytując pliku etapu; stąd obowiązkowy workflow (checkbox odhaczany od razu po akcji). Polskie cudzysłowy `„..."` w etykietach Mermaid łamią parser GitHuba (`got 'STR'`, incydent w diagramie V5) — etykiety w `["..."]`, zero `"` w treści.
