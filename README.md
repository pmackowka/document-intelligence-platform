# Document Intelligence Platform

Lokalna platforma do przetwarzania osobistej dokumentacji medycznej z analizą trendów w czasie. Projekt służy równolegle jako ścieżka nauki stacku AI Engineering.

## Dokumentacja

- **`docs/prd.md`** — kontrakt Version 1 (zakres, wymagania, kryteria sukcesu)
- **`docs/roadmap.md`** — backlog wersji V2–V4 z diagramami architektury
- **`docs/stages/`** — plan implementacji krok po kroku (etapy 00–04)
- **`CLAUDE.md`** — konwencje projektu dla sesji Claude Code

## Stack

Python (uv) · Docling · Apple Vision · BigQuery · Claude (abonament Pro)

## Uruchomienie

```bash
uv sync                 # odtworzenie środowiska z uv.lock
uv run python <skrypt>  # uruchomienie kodu w środowisku projektu
```

## Codzienny flow — dodawanie nowych wyników

Dwa gotowe prompty do wklejenia w Claude Code — resztę (pipeline, aliasy, raport) robi już on, nie Ty ręcznie w terminalu. Mechanizm w tle: każdy przebieg pipeline'u tworzy migawkę-kandydata (`data/store/YYYY-MM-DD-structural.ndjson`), nigdy nie nadpisuje zaufanego magazynu (`data/store/structural-backfill.ndjson`) — pełne uzasadnienie: `docs/prd.md` v1.3, `docs/stages/04-backfill.md`.

**1. Wrzuciłeś nowy plik do `data/raw/structural/` — wklej:**
```
Wrzuciłem nowy plik do data/raw/structural/: <nazwa>. Uruchom pipeline, obsłuż
nieznane markery jeśli się pojawią (zapytaj mnie o zatwierdzenie każdego),
wygeneruj raport z nowej migawki-kandydata i zaczekaj na moją weryfikację —
nie scalaj z zaufanym magazynem.
```

Dostaniesz ścieżki: migawka `data/store/<data>-structural.ndjson`, raport `data/reports/<data>-trendy.md`. Sprawdź kolumnę **„Źródło"** przy nowych wynikach względem oryginału.

**2. Dane poprawne — wklej (uzupełnij datę z kroku 1):**
```
Zweryfikowałem data/store/<data>-structural.ndjson (raport
data/reports/<data>-trendy.md) — dane poprawne. Scal z zaufanym magazynem
data/store/structural-backfill.ndjson.
```

Dopiero teraz dane liczą się „na serio" — BigQuery i dalsza analiza czytają wyłącznie zaufany magazyn. Procedura odświeżenia tabeli (zawsze replace, nigdy append): `docs/stages/03-storage-analysis.md`.

**Przykład:** wracasz z laboratorium z nowym wynikiem TSH, kopiujesz plik do `data/raw/structural/`, wklejasz prompt 1. Marker już w słowniku → od razu dostajesz migawkę i raport do sprawdzenia. Nowy marker/lab → Claude Code najpierw zapyta o zatwierdzenie proponowanego aliasu, dopiero potem wygeneruje raport. Po sprawdzeniu kolumny „Źródło" wklejasz prompt 2.

Dokument z nieczytelnym OCR (za mało wyciągniętego tekstu) nie wejdzie do wyników w ogóle — Claude Code to zgłosi w podsumowaniu; sprawdź skan ręcznie (kąt, ostrość, czy to na pewno badanie krwi/moczu).
