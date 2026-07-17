# Etap 0 — Setup środowiska

## Cel
Działające fundamenty: repozytorium git, środowisko Python, lokalny n8n, smoke test `claude -p`.

## Zakres / Definition of Done
- [x] `git init` + pierwszy commit (PRD, CLAUDE.md, struktura docs) — 2026-07-17, commit `2e5e144`, remote github.com/pmackowka/Document-Intelligence-Platform
- [x] Struktura projektu (`config/`, `src/`, `data/{raw,pending,store,reports}`) — 2026-07-17; drzewo i reguła prywatności ścieżek w CLAUDE.md
- [ ] Środowisko Python (uv)
- [x] `data/` w `.gitignore` — dokumenty medyczne nigdy nie trafiają do repo — 2026-07-17, commit `2e5e144`; konwencja rozszerzona w `2b1d527`
- [ ] n8n uruchomiony lokalnie, pierwszy testowy workflow
- [ ] Smoke test: wywołanie `claude -p "..."` z Pythona (subprocess), w tym `--model haiku`

## Decyzje i dlaczego
<!-- uzupełniane w trakcie pracy -->

## Jak to działa (mechanizmy narzędzi)
<!-- uzupełniane w trakcie pracy: notatki o mechanizmach, nie log czynności -->

## Gotchas / lekcje
<!-- uzupełniane w trakcie pracy -->
