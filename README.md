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

## Codzienny flow — dodawanie nowych wyników (po zakończeniu backfillu)

Docelowe tempo z PRD: 2–3 nowe dokumenty/mies. Za każdym razem te same kroki:

**1. Wrzuć plik(i)** — skan/zdjęcie/PDF nowego wyniku do `data/raw/structural/` (Finder albo terminal, bez znaczenia).

**2. Uruchom pipeline:**
```bash
cd /Users/p/Documents/dev/Document-Intelligence-Platform
PYTHONPATH=src uv run python src/structural_pipeline.py
```
Co się dzieje: OCR (tylko dla nowych plików — stare są w cache, więc szybko) → dopasowanie markerów do słownika `config/aliases.yml` → wyciągnięcie wartości/jednostki/zakresu → zapis **wszystkich** dokumentów (starych + nowych) do `data/store/structural.ndjson`. Jeśli trafi na nazwę markera, której słownik nie zna — pyta Haiku o propozycję kodu, ale **nie ufa jej automatycznie**.

**3. Przeczytaj podsumowanie w terminalu** — ostatnie linie mówią wprost, czy coś wymaga Twojej uwagi:
- `Brak nieznanych markerów — wszystkie zmapowane.` → gotowe, przejdź do kroku 5.
- `Warstwa 3: N nieznanych nazw -> Haiku proponuje aliasy...` → przejdź do kroku 4.
- `Odrzuconych (nieczytelny OCR): N/M` → ten plik nie wszedł do wyników w ogóle; sprawdź skan ręcznie (kąt, ostrość, czy to na pewno badanie krwi/moczu).

**4. Jeśli były nieznane markery — zajrzyj do `data/pending/aliases.yml`.** To propozycje Haiku, nie zatwierdzony słownik — pipeline ich jeszcze nie używa. **Dlaczego to musisz zrobić ręcznie:** zły kod nadany raz (np. „Kreatynina" pomylona z „Kreatynina w moczu") zostałby na stałe, cicho psując każdy przyszły wynik z tą nazwą — nie ma tu miejsca na automatyczne zaufanie. Popraw kod jeśli trzeba, potem **przenieś wpis do `config/aliases.yml`** (właściwy panel, sekcja `markers`) i usuń go z `pending/`.

**5. Jeśli zatwierdzałeś aliasy w kroku 4 — uruchom pipeline drugi raz** (ta sama komenda z kroku 2). Teraz nowo zatwierdzone markery zostaną poprawnie rozpoznane, nie wpadną do „nieznanych".

**6. Opcjonalnie — świeży raport na wizytę:**
```bash
PYTHONPATH=src uv run python src/report.py
```
Zapisuje `data/reports/<data>-trendy.md` ze wszystkimi trendami do tej pory.

**7. Opcjonalnie — odśwież tabelę w BigQuery.** `structural.ndjson` jest nadpisywany od zera przy każdym uruchomieniu (nie doklejany) — więc load do BigQuery też musi być **replace całej tabeli, nigdy append** (inaczej duplikaty starych rekordów przy każdym cyklu). Pełna instrukcja (DROP TABLE + Create table → Upload, schemat do wklejenia): `docs/stages/03-storage-analysis.md`, sekcja „Instrukcja: ręczny load".

### Przykład

Wracasz z laboratorium z 3 nowymi wynikami (morfologia, lipidogram, TSH). Kopiujesz 3 pliki do `data/raw/structural/`, odpalasz komendę z kroku 2.

- **Wariant A (typowy po ustabilizowaniu słownika):** `Brak nieznanych markerów — wszystkie zmapowane.` Gotowe — `data/store/structural.ndjson` ma już nowe rekordy, można pytać o trend w Claude Code.
- **Wariant B (nowe laboratorium albo marker, którego dotąd nie było):** `Warstwa 3: 2 nieznanych nazw -> Haiku proponuje aliasy...`. Otwierasz `pending/aliases.yml`, widzisz np. `Witamina D: VITAMIN_D`. Sprawdzasz, że kod ma sens, przenosisz wpis do `config/aliases.yml` pod właściwym panelem, usuwasz z `pending/`, uruchamiasz pipeline jeszcze raz — teraz Witamina D wchodzi do wyników poprawnie, a przy kolejnym wyniku z tym markerem krok 4 już się nie pojawi.
