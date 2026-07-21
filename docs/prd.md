# PRD: Document Intelligence Platform — Version 1

> Status: **v1.3 — zatwierdzony** (v1.0: 2026-07-17, po sesji sokratejskiej i 2 rundach review). Wszystkie decyzje produktowe zamknięte.
> Kontrakt dla wszystkich sesji z agentem. Każda zmiana zakresu = aktualizacja tego pliku + commit.
>
> **v1.1 (2026-07-18):** (1) ingest tylko ręczny upload przez n8n — usunięty konektor Google Drive; (2) klasyfikacja dokumentu = ręczna etykieta operatora przy uploadzie (human-in-the-loop), a nie klasyfikator automatyczny.
>
> **v1.2 (2026-07-19):** schemat narracyjny doprecyzowany po walidacji etapu 2 (Scope pkt 5): `status` = `prawidłowy`/`nieprawidłowy`/`nieobecny`; pojedynczy pomiar → lista `measurements`; jednostki normalizowane też w narracji; dedup rekordów po badaniu.
>
> **v1.3 (2026-07-21):** zawężenie V1 **wyłącznie do pipeline'u strukturalnego** (dane tabelaryczne z badań krwi/moczu). Pipeline narracyjny (USG/MRI/TK/kolonoskopia: anonimizacja Presidio + ekstrakcja LLM ustaleń) usunięty z V1 całkowicie — kod, konfiguracja, opis w tym dokumencie. Powód: przy ręcznym przeglądzie pierwszych wyekstrahowanych ustaleń (etap 5) nakład HITL na weryfikację poprawności każdego rekordu okazał się nieproporcjonalny do wartości — operator nie ma kompetencji medycznej, by samodzielnie potwierdzić poprawność przyporządkowania parametru do ustalenia. Efekt uboczny decyzji: Presidio okazało się niepotrzebne również w pozostałym zakresie — Warstwa 3 (weryfikacja nieznanych markerów) nigdy nie wysyłała pełnej treści dokumentu do API, tylko samą nazwę markera, więc cały mechanizm anonimizacji stracił jedynego konsumenta.

---

## Problem

Wieloletnia osobista dokumentacja medyczna (~390 plików, 603 MB: PDF, skany, zdjęcia) jest rozproszona i nieustrukturyzowana. Niemożliwe jest dziś:

1. zobaczenie trendu dowolnego markera (np. ferrytyny) na osi 5+ lat,
2. porównanie markerów między sobą (np. Fe vs CRP).

Wartość rośnie z każdym dokumentem — system gromadzi znormalizowaną historię zdrowia, a nie jednorazowo interpretuje pojedynczy wynik.

**Cel drugorzędny (podporządkowany):** nauka stacku AI Engineering (n8n, Docling, pipeline LLM). Gdy produkt i nauka wchodzą w konflikt, wygrywa produkt — kompletność i wiarygodność danych.

## User Persona

Jeden użytkownik = właściciel projektu. Senior Data Analyst, biegły SQL/BigQuery, Python średnio. Pracuje na Macu, w terminalu, z Claude Code. Nie potrzebuje UI — potrzebuje wiarygodnych, płaskich danych, które LLM i on sam mogą odpytywać.

**Anty-persona:** to nie jest produkt dla pacjentów, lekarzy ani organizacji. Zero multi-user, zero compliance klasy medycznej.

## Success Criteria (3 miesiące)

Progi zatwierdzone przez właściciela (runda review 1); S3 (ustalenia narracyjne) usunięte i przenumerowane w v1.3.

| # | Kryterium | Próg |
|---|-----------|------|
| S1 | Historyczne badania krwi/moczu (backfill) przetworzone do kanonicznego JSON | ≥ 95% dokumentów, 100% markerów zmapowanych lub świadomie odrzuconych |
| S2 | Trend dowolnego markera dostępny jednym promptem w Claude Code (terminal czyta JSON/Markdown) | działa dla każdego markera z ≥ 3 pomiarami |
| S3 | Nowy dokument przechodzi pipeline end-to-end | ≤ 15 min pracy operatora łącznie z zatwierdzeniami |
| S4 | Kanoniczny JSON ładuje się do BigQuery bez transformacji | ręczny load NDJSON przechodzi bez błędów schematu |

## Scope V1

### In scope (must have)

1. **Ingest przez n8n:** wyłącznie ręczny upload przez n8n (operator dodaje pliki sam). Konektor Google Drive **usunięty z V1**. Formaty: PDF, skany (PDF/JPG/PNG), zdjęcia (HEIC/JPG).
2. **OCR / konwersja:** Docling (główny silnik) + Apple Vision jako backend OCR dla zdjęć. Wyjście pośrednie: Markdown + JSON.
3. **Pipeline strukturalny — standaryzacja:**
   - Warstwa 1: dictionary mapping (`aliases.yml`) → nazwa kanoniczna markera,
   - Warstwa 2: regex → ekstrakcja wartości liczbowej,
   - Warstwa 3: weryfikacja LLM dla nieznanych nazw → propozycja aliasu, **operator zatwierdza** przed dopisaniem do słownika (do API idzie wyłącznie nazwa markera — bez PII),
   - normalizacja jednostek (`units.yml`) i zakresów referencyjnych do `reference_low`/`reference_high`.
4. **Trwały magazyn wyników** z osią czasu — źródło prawdy: katalog **NDJSON**, płaskie rekordy, append-only (decyzja: bez SQLite przy tej skali).
5. **Mechanika zatwierdzania (plikowa):** pipeline zapisuje propozycje aliasów do `pending/*.yml`; operator przegląda i zatwierdza w Claude Code (edycja pliku, przeniesienie do approved); pipeline czyta wyłącznie zatwierdzone wpisy. Bez n8n forms, bez UI.
6. **Wyjścia:**
   - kanoniczny **NDJSON** (płaskie rekordy, schemat BigQuery-ready),
   - konsumpcja: Claude Code w terminalu czyta pliki; analiza trendów/porównań markerów przez prompt.
7. **Konfiguracja domenowa w YAML** (`aliases.yml`, `units.yml`, `reference_ranges.yml`, `laboratories.yml`) — wiedza domenowa poza kodem.
8. **Backfill:** dokumenty strukturalne z archiwum ~390 plików — szacunkowo ~30%, czyli ok. 115–120 dokumentów (reszta to dokumenty narracyjne, poza zakresem V1 po v1.3); bieżąco 2–3 pliki/mies.

### Out of scope (not now)

- Domeny inne niż medyczna (legal, finance, HR, technical) — usunięte świadomie.
- **Przetwarzanie dokumentów narracyjnych** (USG, MRI, TK, kolonoskopia i podobne opisy) — świadomie wycięte z V1 (zmiana zakresu v1.3): nakład HITL na weryfikację ustaleń uznany za nieproporcjonalny do wartości przy braku kompetencji medycznej operatora. Dokumenty pozostają w lokalnym archiwum, nieprzetwarzane.
- Dziennik interwencji/stylu życia (dieta, suplementy, leki) — korelacje z kontekstem życiowym tylko przez ręczne dopisanie w prompcie analizy. Kandydat na V1.1.
- Jakiekolwiek UI / dashboard / wykresy — konsumpcja wyłącznie plikowo + terminal.
- Automatyczny load do BigQuery (format ma być gotowy, load ręczny).
- Konektor Google Drive (auto-pull z folderu) — usunięty w v1.1; ingest wyłącznie przez ręczny upload w n8n.
- Klasyfikacja/routing dokumentów — zbędne przy jednej klasie dokumentów (v1.3); w V1.1 była to ręczna etykieta operatora, teraz nie ma czego etykietować.
- MCP server (V2); FastAPI/Docker/Cloud Run (V3); agenci (V4) — patrz `docs/roadmap.md`.
- Interpretacja medyczna / rekomendacje zdrowotne jako feature — raporty LLM to materiał do rozmowy z lekarzem, nie diagnoza.
- Twarde gwarancje prywatności (patrz Threat Model).

## User Stories

1. Jako właściciel danych chcę wrzucić plik przez n8n, aby system bez mojego dalszego udziału doprowadził go do postaci znormalizowanej i poprosił mnie wyłącznie o zatwierdzenia.
2. Jako analityk chcę zapytać w terminalu „pokaż trend ferrytyny od 2021", aby dostać wartości z datami, jednostką kanoniczną i zakresem referencyjnym.
3. Jako analityk chcę porównać dwa markery na osi czasu (Fe vs CRP), aby szukać zależności między nimi.
4. Jako pacjent przygotowujący się do wizyty chcę wygenerować raport Markdown z trendów markerów (np. ferrytyna spadająca od 2021 do 2025), aby omówić go z lekarzem.
5. Jako operator chcę zatwierdzać nowe aliasy w możliwie tanim interakcyjnie kroku, aby słownik rósł, a kod się nie zmieniał.
6. Jako analityk chcę załadować NDJSON ręcznie do BigQuery, aby liczyć statystyki SQL-em.

## Threat Model / Privacy (decyzja świadoma)

Wymóg prywatności jest **miękki** — to **nie** jest system klasy medycznej; wdrożenie produkcyjne wymagałoby self-hostingu (np. Mac mini) i twardych gwarancji, poza zakresem. Po v1.3 profil ryzyka jest prostszy niż zakładano pierwotnie: pipeline strukturalny **nigdy nie wysyła pełnej treści dokumentu do żadnego API** — jedyne wywołanie LLM (Warstwa 3, weryfikacja nieznanych markerów) dostaje wyłącznie samą nazwę markera, która nie jest PII. Anonimizacja przed wysyłką (Presidio) była potrzebna wyłącznie dla usuniętego pipeline'u narracyjnego i nie ma już zastosowania w V1. Dokumenty źródłowe pozostają lokalnie i na Google Drive.

## Tech Constraints

- **Środowisko:** lokalnie, MacBook (macOS). Bez chmury obliczeniowej w V1.
- **Orkiestracja:** n8n (wyłącznie orkiestracja — zero logiki biznesowej).
- **Silnik:** Python (OCR, standaryzacja, zapis). Kod i nazwy po angielsku, komentarze po polsku.
- **OCR:** Docling + Apple Vision.
- **LLM:** wyłącznie Claude w ramach abonamentu Pro (Anthropic) — **zero zakupu tokenów API**. Wywołania programistyczne przez Claude Code w trybie headless (`claude -p "<prompt>"`), uruchamiane z Pythona/n8n jako komenda shell. Weryfikacja aliasów: Haiku (przez ten sam CLI, `--model`). Test lokalnego modelu (Ollama) — eksperyment poza zakresem V1.
- **Dane:** NDJSON płaski, BigQuery-ready; YAML dla wiedzy domenowej; append-only.
- **Skala:** ~115–120 dokumentów strukturalnych backfill + 2–3/mies. — wydajność nie jest constraintem; priorytet: poprawność i powtarzalność.

## Ryzyka (nazwane, zaakceptowane lub do mitygacji)

| Ryzyko | Mitygacja |
|---|---|
| LLM na N=kilkanaście pomiarów generuje przekonujące hipotezy, nie analizę | Raporty oznaczane jako hipotezy; JSON umożliwia własną weryfikację SQL-em |
| Jakość OCR na starych skanach/zdjęciach | Klasyfikacja jakości; dokumenty nieczytelne odrzucane świadomie (licznik do S1) |
| Zatwierdzanie ręczne zniechęci po backfillu | Front-load: słownik nasyca się na pierwszych ~50 dokumentach |
| Limity abonamentu Pro współdzielone z interaktywną pracą w Claude Code | Po v1.3 wolumen wywołań niski — Warstwa 3 pyta Haiku wyłącznie o nieznane nazwy markerów, a słownik nasyca się szybko (etap 3: 0 nieznanych na 14 dok.); przy wyczerpaniu limitu backfill po prostu zwalnia — świadomie zaakceptowane |
| Zakresy referencyjne różnią się między laboratoriami | Zakres zapisywany per pomiar (z dokumentu), nie globalnie |

### Rozstrzygnięte (runda review 1, 2026-07-17)

> Historyczny log pierwszej rundy review — nie aktualizowany przy późniejszych zmianach zakresu (v1.1–v1.3); część punktów (Presidio, podział 70/30 narracyjne/strukturalne) dotyczy zakresu sprzed v1.3 i jest nieaktualna wobec bieżącego PRD.

- Magazyn danych → katalog NDJSON (bez SQLite).
- Mechanika zatwierdzania → plikowa, `pending/*.yml` przeglądane w Claude Code.
- Struktura backfillu → ~70% narracyjne / ~30% strukturalne.
- Progi Success Criteria S1–S5 → zatwierdzone bez zmian.
- Kolejność anonimizacji → Presidio zawsze przed wysyłką tekstu dokumentu do API; wyjątek: weryfikacja aliasów (sama nazwa markera).
- Wybór LLM → wyłącznie Claude przez abonament Pro (Claude Code headless, `claude -p`), zero tokenów API; mały model do aliasów: Haiku; lokalny model: eksperyment poza V1. Konsekwencja: tempo backfillu ograniczone limitami abonamentu — zaakceptowane.
- Presidio pl_PL → research wykonany 2026-07-17: `PlPeselRecognizer` wbudowany, polski NER przez spaCy `pl_core_news_lg`; szczegóły historyczne w etapie 4 (usunięty w v1.3).
