# Etap 0 — Setup środowiska

## Cel
Działające fundamenty: repozytorium git, środowisko Python, lokalny n8n, smoke test `claude -p`.

## Zakres / Definition of Done
- [x] `git init` + pierwszy commit (PRD, CLAUDE.md, struktura docs) — 2026-07-17, commit `2e5e144`, remote github.com/pmackowka/Document-Intelligence-Platform
- [x] Struktura projektu (`config/`, `src/`, `data/{raw,pending,store,reports}`) — 2026-07-17; drzewo i reguła prywatności ścieżek w CLAUDE.md
- [x] Środowisko Python (uv) — 2026-07-18; uv 0.11.29 (brew), Python 3.11.4, `uv sync` → `.venv/` + `uv.lock`, weryfikacja `uv run python` OK
- [x] `data/` w `.gitignore` — dokumenty medyczne nigdy nie trafiają do repo — 2026-07-17, commit `2e5e144`; konwencja rozszerzona w `2b1d527`
- [ ] n8n uruchomiony lokalnie, pierwszy testowy workflow
- [ ] Smoke test: wywołanie `claude -p "..."` z Pythona (subprocess), w tym `--model haiku`

## Decyzje i dlaczego

- **2026-07-17** — Git od pierwszego dnia, z prywatnym remote na GitHubie. Powód: metoda „PRD jako living document" wymaga commitów przy każdej zmianie zakresu, a dokumentacja zawiera realne informacje zdrowotne właściciela — repo musi pozostać prywatne (publiczna wersja portfolio = osobny, zredagowany wariant).
- **2026-07-17** — Szkielet folderów utworzony z góry, przed kodem. Powód: fizycznie istniejąca struktura egzekwuje regułę prywatności ścieżek (`data/` = treść medyczna, poza gitem) lepiej niż sam zapis w CLAUDE.md — przyszła sesja nie wymyśli własnych ścieżek. Pliki natomiast powstają dopiero w swoich etapach — bez pustych stubów na zapas.
- **2026-07-17** — `data/` ignorowane w całości (jeden wpis), nie per-plik. Powód: reguła „nowy artefakt medyczny = automatycznie poza gitem" bez pamiętania o aktualizacji `.gitignore`.
- **2026-07-17** — Reguły przekrojowe (workflow etapów, Mermaid, ścieżki) w CLAUDE.md, szczegóły w docs. Powód: CLAUDE.md jest ładowany automatycznie do każdej sesji — to jedyne miejsce z gwarancją przeczytania.
- **2026-07-18** — `uv` zamiast `pip`+`venv`+`poetry`. Powód: jedno narzędzie (środowisko, zależności, lockfile, wersja Pythona), znacznie szybsze przy ciężkim stacku (Docling, spaCy). `uv.lock` w repo → reprodukowalne środowisko z klona jedną komendą (`uv sync`).
- **2026-07-18** — Zależności domenowe (Docling, Presidio, spaCy) **nie** instalowane teraz — trafiają do środowiska w swoich etapach (1 i 4). Etap 0 stawia tylko działający fundament, zgodnie z regułą „bez stubów na zapas".
- **2026-07-18** — Instalacja `uv` przez Homebrew (nie skrypt curl). Powód: aktualizacje przez `brew upgrade` razem z resztą narzędzi, bez osobnego mechanizmu self-update.

## Jak to działa (mechanizmy narzędzi)

- **2026-07-17** — Git nie śledzi pustych folderów — stąd `.gitkeep` w `config/` i `src/`. Ścieżki ignorowane (`data/*`) nie istnieją w świeżym klonie w ogóle, więc kod pipeline'u musi robić `mkdir -p` przy starcie.
- **2026-07-17** — CLAUDE.md vs docs to progressive disclosure: krótka reguła zawsze w kontekście, pełna instrukcja doczytywana na żądanie — ten sam mechanizm co skille w Claude Code (opis w kontekście, treść ładowana przy użyciu).
- **2026-07-17** — Weryfikacja prywatności repo bez `gh`: `curl -s -o /dev/null -w "%{http_code}" https://api.github.com/repos/<owner>/<repo>` — `404` bez autoryzacji oznacza repo prywatne (lub nieistniejące), `200` = publiczne.
- **2026-07-18** — `uv run <komenda>` sam aktywuje `.venv` przed uruchomieniem — nie ma potrzeby ręcznego `source .venv/bin/activate` jak przy klasycznym `venv`. `uv sync` czyta `pyproject.toml`, tworzy `.venv/` i zapisuje dokładne wersje do `uv.lock`. `.venv/` jest w `.gitignore` (odtwarzalne z locka, duże) — wersjonujemy `pyproject.toml` + `uv.lock`.

## Gotchas / lekcje

- **2026-07-17** — Deklaracja w czacie ≠ wykonanie: model napisał „git init odhaczony rzeczywistością", nie edytując pliku etapu. Wykryte przez właściciela; skutek: obowiązkowy workflow w CLAUDE.md (checkbox natychmiast po akcji, z datą i commitem).
- **2026-07-17** — Polskie cudzysłowy `„..."` w etykietach Mermaid łamią parser GitHuba (`got 'STR'`) — incydent w diagramie V5, fix w commit `88e5dc2`. Reguła: etykiety w `["..."]`, zero `"` w treści.
- **2026-07-17** — `gh` CLI nie jest zainstalowane na tej maszynie — `brew install gh` przy domykaniu etapu 0.
