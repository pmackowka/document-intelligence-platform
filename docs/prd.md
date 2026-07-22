# PRD: Document Intelligence Platform — Version 1

> Status: **v1.3 — zatwierdzony** (v1.0: 2026-07-17, po sesji sokratejskiej i 2 rundach review). Wszystkie decyzje produktowe zamknięte.
> Kontrakt dla wszystkich sesji z agentem. Każda zmiana zakresu = aktualizacja tego pliku + commit.
>
> **v1.1 (2026-07-18):** ingest tylko ręczny — usunięty konektor Google Drive.
>
> **v1.2 (2026-07-21):** **n8n usunięty z V1.** Powód: architektoniczny rozjazd wykryty przy próbie realnego spięcia (etap 4) — n8n działa w kontenerze Docker (Linux), a silnik OCR to Apple Vision (natywny framework macOS, nie uruchomi się w kontenerze); do tego kontener nie ma dostępu do plików projektu. `Execute Command` z n8n fizycznie nie odpali pipeline'u. Orkiestracja w V1 = uruchomienie ręczne z terminala (`uv run python ...`), spójne z terminal-native charakterem projektu (zero UI). n8n jako narzędzie orkiestracji pozostaje kandydatem na przyszłość — patrz „Do rozważenia" w `docs/roadmap.md` (uruchomienie na VPS zamiast lokalnego Dockera obchodzi problem macOS/Apple Vision, o ile OCR zostanie tam zastąpiony silnikiem serwerowym).
>
> **v1.3 (2026-07-22):** **Magazyn: migawki datowane + scalenie ręczne, zamiast bezpośredniego nadpisania.** Powód: backfill ~40 dokumentów ujawnił cztery niezależne rundy błędów w tej samej partii (patrz `docs/stages/04-backfill.md`) — ryzyko, że przyszła poprawka regexa/aliasu przy okazji nowego dokumentu po cichu zmieni wartość w rekordzie już zweryfikowanym przez operatora, jest realne, bo pipeline zawsze przetwarza cały `data/raw/structural/` od zera. `structural_pipeline.py` zapisuje teraz każdy przebieg do osobnej migawki `data/store/YYYY-MM-DD-structural.ndjson`; zaufany `data/store/structural-backfill.ndjson` (używany przez BigQuery i dalszą analizę) zmienia się wyłącznie przez ręczne scalenie potwierdzonej migawki, nie automatycznie.

---

## Problem

Wieloletnia osobista dokumentacja medyczna (~390 plików, 603 MB: PDF, skany, zdjęcia) jest rozproszona i nieustrukturyzowana. Niemożliwe jest dziś:

1. zobaczenie trendu dowolnego markera (np. ferrytyny) na osi 5+ lat,
2. porównanie markerów między sobą (np. Fe vs CRP).

Wartość rośnie z każdym dokumentem — system gromadzi znormalizowaną historię zdrowia, a nie jednorazowo interpretuje pojedynczy wynik.

**Cel drugorzędny (podporządkowany):** nauka stacku AI Engineering (Docling, pipeline LLM, BigQuery). Gdy produkt i nauka wchodzą w konflikt, wygrywa produkt — kompletność i wiarygodność danych.

## User Persona

Jeden użytkownik = właściciel projektu. Senior Data Analyst, biegły SQL/BigQuery, Python średnio. Pracuje na Macu, w terminalu, z Claude Code. Nie potrzebuje UI — potrzebuje wiarygodnych, płaskich danych, które LLM i on sam mogą odpytywać.

**Anty-persona:** to nie jest produkt dla pacjentów, lekarzy ani organizacji. Zero multi-user, zero compliance klasy medycznej.

## Success Criteria (3 miesiące)

Progi zatwierdzone przez właściciela (runda review 1).

| # | Kryterium | Próg |
|---|-----------|------|
| S1 | Historyczne badania krwi/moczu (backfill) przetworzone do kanonicznego JSON | ≥ 95% dokumentów, 100% markerów zmapowanych lub świadomie odrzuconych |
| S2 | Trend dowolnego markera dostępny jednym promptem w Claude Code (terminal czyta JSON/Markdown) | działa dla każdego markera z ≥ 3 pomiarami |
| S3 | Nowy dokument przechodzi pipeline end-to-end | ≤ 15 min pracy operatora łącznie z zatwierdzeniami |
| S4 | Kanoniczny JSON ładuje się do BigQuery bez transformacji | ręczny load NDJSON przechodzi bez błędów schematu |

## Scope V1

### In scope (must have)

1. **Ingest ręczny:** operator sam dodaje pliki do `data/raw/structural/` (Finder/terminal) i uruchamia pipeline z terminala. Konektor Google Drive **usunięty z V1**. Formaty: PDF, skany (PDF/JPG/PNG), zdjęcia (HEIC/JPG).
2. **OCR / konwersja:** Docling (główny silnik) + Apple Vision jako backend OCR dla zdjęć. Wyjście pośrednie: Markdown + JSON.
3. **Pipeline strukturalny — standaryzacja:**
   - Warstwa 1: dictionary mapping (`aliases.yml`) → nazwa kanoniczna markera,
   - Warstwa 2: regex → ekstrakcja wartości liczbowej,
   - Warstwa 3: weryfikacja LLM dla nieznanych nazw → propozycja aliasu, **operator zatwierdza** przed dopisaniem do słownika (do API idzie wyłącznie nazwa markera — bez PII),
   - normalizacja jednostek (`units.yml`) i zakresów referencyjnych do `reference_low`/`reference_high`.
4. **Trwały magazyn wyników** z osią czasu — źródło prawdy: katalog **NDJSON**, płaskie rekordy. Każdy przebieg pipeline'u zapisuje datowaną migawkę (`YYYY-MM-DD-structural.ndjson`, nigdy nie nadpisywaną) — append-only na poziomie katalogu. Zaufany plik (`structural-backfill.ndjson`, czytany przez BigQuery i raport) zmienia się wyłącznie przez ręczne scalenie potwierdzonej migawki (decyzja: bez SQLite przy tej skali).
5. **Mechanika zatwierdzania (plikowa):** pipeline zapisuje propozycje aliasów do `pending/*.yml`; operator przegląda i zatwierdza w Claude Code (edycja pliku, przeniesienie do approved); pipeline czyta wyłącznie zatwierdzone wpisy. Bez UI.
6. **Wyjścia:**
   - kanoniczny **NDJSON** (płaskie rekordy, schemat BigQuery-ready),
   - konsumpcja: Claude Code w terminalu czyta pliki; analiza trendów/porównań markerów przez prompt.
7. **Konfiguracja domenowa w YAML** (`aliases.yml`, `units.yml`, `reference_ranges.yml`, `laboratories.yml`) — wiedza domenowa poza kodem.
8. **Backfill:** dokumenty strukturalne z archiwum ~390 plików — szacunkowo ~30%, czyli ok. 115–120 dokumentów (reszta to dokumenty narracyjne, poza zakresem V1); bieżąco 2–3 pliki/mies.

### Out of scope (not now)

- Domeny inne niż medyczna (legal, finance, HR, technical) — usunięte świadomie.
- **Przetwarzanie dokumentów narracyjnych** (USG, MRI, TK, kolonoskopia i podobne opisy) — wymaga ekstrakcji LLM i weryfikacji medycznej każdego rekordu, do której operator nie ma kompetencji; poza zakresem V1. Dokumenty pozostają w lokalnym archiwum, nieprzetwarzane.
- Dziennik interwencji/stylu życia (dieta, suplementy, leki) — korelacje z kontekstem życiowym tylko przez ręczne dopisanie w prompcie analizy. Kandydat na V1.1.
- Jakiekolwiek UI / dashboard / wykresy — konsumpcja wyłącznie plikowo + terminal.
- Automatyczny load do BigQuery (format ma być gotowy, load ręczny).
- Konektor Google Drive (auto-pull z folderu) — usunięty w v1.1; ingest wyłącznie ręczny.
- **Orkiestracja przez n8n** — usunięta w v1.2 (rozjazd Docker/Linux ↔ Apple Vision/macOS, patrz changelog). W V1 pipeline uruchamia operator z terminala. n8n jako kandydat na przyszłość (VPS) — `docs/roadmap.md`.
- MCP server (V2); FastAPI/Docker/Cloud Run (V3); agenci (V4) — patrz `docs/roadmap.md`.
- Interpretacja medyczna / rekomendacje zdrowotne jako feature — raporty LLM to materiał do rozmowy z lekarzem, nie diagnoza.
- Twarde gwarancje prywatności (patrz Threat Model).

## User Stories

1. Jako właściciel danych chcę wrzucić plik do folderu i uruchomić pipeline z terminala, aby system bez mojego dalszego udziału doprowadził go do postaci znormalizowanej i poprosił mnie wyłącznie o zatwierdzenia.
2. Jako analityk chcę zapytać w terminalu „pokaż trend ferrytyny od 2021", aby dostać wartości z datami, jednostką kanoniczną i zakresem referencyjnym.
3. Jako analityk chcę porównać dwa markery na osi czasu (Fe vs CRP), aby szukać zależności między nimi.
4. Jako pacjent przygotowujący się do wizyty chcę wygenerować raport Markdown z trendów markerów (np. ferrytyna spadająca od 2021 do 2025), aby omówić go z lekarzem.
5. Jako operator chcę zatwierdzać nowe aliasy w możliwie tanim interakcyjnie kroku, aby słownik rósł, a kod się nie zmieniał.
6. Jako analityk chcę załadować NDJSON ręcznie do BigQuery, aby liczyć statystyki SQL-em.

## Threat Model / Privacy (decyzja świadoma)

Wymóg prywatności jest **miękki** — to **nie** jest system klasy medycznej; wdrożenie produkcyjne wymagałoby self-hostingu (np. Mac mini) i twardych gwarancji, poza zakresem. Pipeline strukturalny **nigdy nie wysyła pełnej treści dokumentu do żadnego API** — jedyne wywołanie LLM (Warstwa 3, weryfikacja nieznanych markerów) dostaje wyłącznie samą nazwę markera, która nie jest PII. Dokumenty źródłowe pozostają lokalnie i na Google Drive.

## Tech Constraints

- **Środowisko:** lokalnie, MacBook (macOS). Bez chmury obliczeniowej w V1.
- **Uruchamianie:** ręczne z terminala (`uv run python ...`). Bez dedykowanego orkiestratora w V1 (n8n usunięty w v1.2 — Apple Vision wymaga macOS, nie działa w kontenerze Docker n8n).
- **Silnik:** Python (OCR, standaryzacja, zapis). Kod i nazwy po angielsku, komentarze po polsku.
- **OCR:** Docling + Apple Vision.
- **LLM:** wyłącznie Claude w ramach abonamentu Pro (Anthropic) — **zero zakupu tokenów API**. Wywołania programistyczne przez Claude Code w trybie headless (`claude -p "<prompt>"`), uruchamiane z Pythona jako komenda shell. Weryfikacja aliasów: Haiku (przez ten sam CLI, `--model`). Test lokalnego modelu (Ollama) — eksperyment poza zakresem V1.
- **Dane:** NDJSON płaski, BigQuery-ready; YAML dla wiedzy domenowej; migawki datowane append-only, zaufany plik scalany ręcznie (v1.3).
- **Skala:** ~115–120 dokumentów strukturalnych backfill + 2–3/mies. — wydajność nie jest constraintem; priorytet: poprawność i powtarzalność.

## Ryzyka (nazwane, zaakceptowane lub do mitygacji)

| Ryzyko | Mitygacja |
|---|---|
| LLM na N=kilkanaście pomiarów generuje przekonujące hipotezy, nie analizę | Raporty oznaczane jako hipotezy; JSON umożliwia własną weryfikację SQL-em |
| Jakość OCR na starych skanach/zdjęciach | Klasyfikacja jakości; dokumenty nieczytelne odrzucane świadomie (licznik do S1) |
| Zatwierdzanie ręczne zniechęci po backfillu | Front-load: słownik nasyca się na pierwszych ~50 dokumentach |
| Limity abonamentu Pro współdzielone z interaktywną pracą w Claude Code | Wolumen wywołań niski — Warstwa 3 pyta Haiku wyłącznie o nieznane nazwy markerów, a słownik nasyca się szybko (etap 2: 0 nieznanych na 14 dok.); przy wyczerpaniu limitu backfill po prostu zwalnia — świadomie zaakceptowane |
| Zakresy referencyjne różnią się między laboratoriami | Zakres zapisywany per pomiar (z dokumentu), nie globalnie |

### Rozstrzygnięte (runda review 1, 2026-07-17)

- Magazyn danych → katalog NDJSON (bez SQLite).
- Mechanika zatwierdzania → plikowa, `pending/*.yml` przeglądane w Claude Code.
- Progi Success Criteria S1–S4 → zatwierdzone bez zmian.
- Wybór LLM → wyłącznie Claude przez abonament Pro (Claude Code headless, `claude -p`), zero tokenów API; mały model do aliasów: Haiku; lokalny model: eksperyment poza V1. Konsekwencja: tempo backfillu ograniczone limitami abonamentu — zaakceptowane.
