# PRD: Document Intelligence Platform — Version 1

> Status: **v1.2 — zatwierdzony** (v1.0: 2026-07-17, po sesji sokratejskiej i 2 rundach review). Wszystkie decyzje produktowe zamknięte.
> Kontrakt dla wszystkich sesji z agentem. Każda zmiana zakresu = aktualizacja tego pliku + commit.
>
> **v1.1 (2026-07-18):** (1) ingest tylko ręczny upload przez n8n — usunięty konektor Google Drive; (2) klasyfikacja dokumentu = ręczna etykieta operatora przy uploadzie (human-in-the-loop), a nie klasyfikator automatyczny.
>
> **v1.2 (2026-07-19):** schemat narracyjny doprecyzowany po walidacji etapu 2 (Scope pkt 5): `status` = `prawidłowy`/`nieprawidłowy`/`nieobecny`; pojedynczy pomiar → lista `measurements`; jednostki normalizowane też w narracji; dedup rekordów po badaniu.

---

## Problem

Wieloletnia osobista dokumentacja medyczna (~390 plików, 603 MB: PDF, skany, zdjęcia) jest rozproszona i nieustrukturyzowana. Niemożliwe jest dziś:

1. zobaczenie trendu dowolnego markera (np. ferrytyny) na osi 5+ lat,
2. porównanie markerów między sobą (np. Fe vs CRP),
3. zestawienie wyników liczbowych z ustaleniami badań obrazowych (USG, MRI, TK, kolonoskopia) w jednym kontekście analizy LLM.

Wartość rośnie z każdym dokumentem — system gromadzi znormalizowaną historię zdrowia, a nie jednorazowo interpretuje pojedynczy wynik.

**Cel drugorzędny (podporządkowany):** nauka stacku AI Engineering (n8n, Docling, Presidio, pipeline LLM). Gdy produkt i nauka wchodzą w konflikt, wygrywa produkt — kompletność i wiarygodność danych.

## User Persona

Jeden użytkownik = właściciel projektu. Senior Data Analyst, biegły SQL/BigQuery, Python średnio. Pracuje na Macu, w terminalu, z Claude Code. Nie potrzebuje UI — potrzebuje wiarygodnych, płaskich danych, które LLM i on sam mogą odpytywać.

**Anty-persona:** to nie jest produkt dla pacjentów, lekarzy ani organizacji. Zero multi-user, zero compliance klasy medycznej.

## Success Criteria (3 miesiące)

Progi zatwierdzone przez właściciela (runda review 1):

| # | Kryterium | Próg |
|---|-----------|------|
| S1 | Historyczne badania krwi/moczu (backfill) przetworzone do kanonicznego JSON | ≥ 95% dokumentów, 100% markerów zmapowanych lub świadomie odrzuconych |
| S2 | Trend dowolnego markera dostępny jednym promptem w Claude Code (terminal czyta JSON/Markdown) | działa dla każdego markera z ≥ 3 pomiarami |
| S3 | Dokumenty narracyjne: ustalenia wyekstrahowane i zatwierdzone przez operatora | 100% dokumentów backfillu ma zapisany rekord ustaleń |
| S4 | Nowy dokument przechodzi pipeline end-to-end | ≤ 15 min pracy operatora łącznie z zatwierdzeniami |
| S5 | Kanoniczny JSON ładuje się do BigQuery bez transformacji | ręczny load NDJSON przechodzi bez błędów schematu |

## Scope V1

### In scope (must have)

1. **Ingest przez n8n:** wyłącznie ręczny upload przez n8n (operator dodaje pliki sam). Konektor Google Drive **usunięty z V1**. Formaty: PDF, skany (PDF/JPG/PNG), zdjęcia (HEIC/JPG).
2. **OCR / konwersja:** Docling (główny silnik) + Apple Vision jako backend OCR dla zdjęć. Wyjście pośrednie: Markdown + JSON.
3. **Klasyfikacja dokumentu** na jedną z dwóch klas — **etykieta nadawana ręcznie przez operatora przy uploadzie** (human-in-the-loop, nie klasyfikator automatyczny): operator wskazuje klasę, n8n routuje (Switch) do właściwego pipeline'u, plik ląduje w `data/raw/{structural,narrative}/`. Uzasadnienie: klasyfikacja automatyczna jest zawodna, a operator i tak jest w pętli — ręczna etykieta to najtańszy i najpewniejszy klasyfikator; usuwa z V1 komponent automatycznego klasyfikatora. Klasy:
   - **Strukturalne** (badania krwi, moczu — tabele marker/wartość/jednostka/zakres),
   - **Narracyjne** (opisy USG, MRI, TK, kolonoskopii i podobne).
4. **Pipeline strukturalny — standaryzacja:**
   - Warstwa 1: dictionary mapping (`aliases.yml`) → nazwa kanoniczna markera,
   - Warstwa 2: regex → ekstrakcja wartości liczbowej,
   - Warstwa 3: weryfikacja LLM dla nieznanych nazw → propozycja aliasu, **operator zatwierdza** przed dopisaniem do słownika (do API idzie wyłącznie nazwa markera — bez PII, więc krok może działać przed pełną anonimizacją dokumentu),
   - normalizacja jednostek (`units.yml`) i zakresów referencyjnych do `reference_low`/`reference_high`.
5. **Pipeline narracyjny — ekstrakcja ustaleń (LLM-based, best-effort):**
   - **uwaga na proporcje: ~70% backfillu to dokumenty narracyjne** — ten pipeline obsługuje większość danych i dostaje odpowiedni priorytet wysiłku,
   - frontier model ekstrahuje do schematu (**v1.2, doprecyzowany po walidacji etapu 2**): `finding`, `location`, `measurements` (lista `{value, unit, label}` — obsługuje pomiary wielowymiarowe, np. 22×23×37 mm + objętość), `status` (`prawidłowy` | `nieprawidłowy` | `nieobecny` = norma / patologia obecna / wykluczone), `exam_type`, `exam_date` — **wyłącznie na tekście po anonimizacji Presidio**,
   - **normalizacja jednostek również w narracji**: `units.yml` + domyślne domenowe dla jednostek dorozumianych (np. wymiary echo → mm),
   - **dedup po badaniu**: jedno badanie bywa w kilku plikach (opis + karta wizyty + histopatologia) — rekordy grupowane/deduplikowane po (`exam_type`, `exam_date`); operator rozstrzyga w pętli,
   - **operator zatwierdza każdy rekord** przed zapisem (human-in-the-loop obowiązkowy — model będzie pomijał i nadinterpretował),
   - pełny anonimizowany Markdown opisu zapisywany obok rekordów jako kontekst.
6. **Anonimizacja (Presidio):** nazwiska, adresy, telefony, PESEL, e-mail → pseudonimy. **Reguła twarda:** żaden tekst dokumentu nie trafia do zewnętrznego API przed Presidio; jedyny wyjątek to weryfikacja aliasów (sama nazwa markera, bez PII).
7. **Trwały magazyn wyników** z osią czasu — źródło prawdy: katalog **NDJSON**, płaskie rekordy, append-only (decyzja: bez SQLite przy tej skali).
8. **Mechanika zatwierdzania (plikowa):** pipeline zapisuje propozycje aliasów i ustaleń do `pending/*.yml`; operator przegląda i zatwierdza w Claude Code (edycja pliku, przeniesienie do approved); pipeline czyta wyłącznie zatwierdzone wpisy. Bez n8n forms, bez UI.
9. **Wyjścia:**
   - kanoniczny **NDJSON** (płaskie rekordy, schemat BigQuery-ready),
   - **Markdown** per dokument (do konsumpcji przez LLM),
   - konsumpcja: Claude Code w terminalu czyta pliki; analiza trendów/porównań markerów przez prompt.
10. **Konfiguracja domenowa w YAML** (`aliases.yml`, `units.yml`, `reference_ranges.yml`, `laboratories.yml`) — wiedza domenowa poza kodem.
11. **Backfill:** pierwsza partia ~250 z ~390 plików, potem reszta; bieżąco 2–3 pliki/mies. Struktura: ~70% dokumenty narracyjne, ~30% strukturalne.

### Out of scope (not now)

- Domeny inne niż medyczna (legal, finance, HR, technical) — usunięte świadomie.
- Dziennik interwencji/stylu życia (dieta, suplementy, leki) — korelacje z kontekstem życiowym tylko przez ręczne dopisanie w prompcie analizy. Kandydat na V1.1.
- Jakiekolwiek UI / dashboard / wykresy — konsumpcja wyłącznie plikowo + terminal.
- Automatyczny load do BigQuery (format ma być gotowy, load ręczny).
- Konektor Google Drive (auto-pull z folderu) — usunięty w v1.1; ingest wyłącznie przez ręczny upload w n8n.
- Automatyczny klasyfikator dokumentów — klasę nadaje operator ręcznie przy uploadzie (v1.1).
- RAG, wektorowa baza (V2); FastAPI/Docker/Cloud Run (V3); MCP server (V4); agenci (V5).
- Interpretacja medyczna / rekomendacje zdrowotne jako feature — raporty LLM to materiał do rozmowy z lekarzem, nie diagnoza.
- Twarde gwarancje prywatności (patrz Threat Model).

## User Stories

1. Jako właściciel danych chcę wrzucić plik przez n8n z ręczną etykietą klasy (strukturalne/narracyjne), aby system bez mojego dalszego udziału doprowadził go do postaci znormalizowanej i poprosił mnie wyłącznie o zatwierdzenia.
2. Jako analityk chcę zapytać w terminalu „pokaż trend ferrytyny od 2021", aby dostać wartości z datami, jednostką kanoniczną i zakresem referencyjnym.
3. Jako analityk chcę porównać dwa markery na osi czasu (Fe vs CRP), aby szukać zależności między nimi.
4. Jako pacjent przygotowujący się do wizyty chcę wygenerować raport Markdown z trendów + ustaleń narracyjnych (np. kamień nerkowy 6 mm w 2023 → 8 mm w 2025), aby omówić go z lekarzem.
5. Jako operator chcę zatwierdzać nowe aliasy i wyekstrahowane ustalenia w możliwie tanim interakcyjnie kroku, aby słownik rósł, a kod się nie zmieniał.
6. Jako analityk chcę załadować NDJSON ręcznie do BigQuery, aby liczyć statystyki SQL-em.

## Threat Model / Privacy (decyzja świadoma)

Wymóg prywatności jest **miękki**. Dokumenty źródłowe i tak przechowywane są na Google Drive; Presidio pełni dwie role: (1) kompetencja do nauczenia, (2) higiena — surowe dane osobowe nie trafiają do promptów API LLM. To **nie** jest system klasy medycznej; wdrożenie produkcyjne wymagałoby self-hostingu (np. Mac mini) i twardych gwarancji — poza zakresem.

## Tech Constraints

- **Środowisko:** lokalnie, MacBook (macOS). Bez chmury obliczeniowej w V1.
- **Orkiestracja:** n8n (wyłącznie orkiestracja — zero logiki biznesowej).
- **Silnik:** Python (OCR, standaryzacja, anonimizacja, zapis). Kod i nazwy po angielsku, komentarze po polsku.
- **OCR:** Docling + Apple Vision.
- **Anonimizacja:** Microsoft Presidio. Research (2026-07-17): wbudowany `PlPeselRecognizer` (encja `PL_PESEL`, walidacja sumy kontrolnej, od v2.2.352); NER dla polskich nazwisk/adresów wymaga skonfigurowania polskiego modelu spaCy (`pl_core_news_lg`) jako NLP engine; e-mail/telefon to recognizery wzorcowe, niezależne od języka. Jakość wykrywania adresów do zweryfikowania na próbce dokumentów w 1. tygodniu implementacji.
- **LLM:** wyłącznie Claude w ramach abonamentu Pro (Anthropic) — **zero zakupu tokenów API**. Wywołania programistyczne przez Claude Code w trybie headless (`claude -p "<prompt>"`), uruchamiane z Pythona/n8n jako komenda shell. Ekstrakcja narracyjna i analiza: model domyślny abonamentu; weryfikacja aliasów: Haiku (przez ten sam CLI, `--model`). Test lokalnego modelu (Ollama) — eksperyment poza zakresem V1.
- **Dane:** NDJSON płaski, BigQuery-ready; YAML dla wiedzy domenowej; append-only.
- **Skala:** ~390 dokumentów backfill + 2–3/mies. — wydajność nie jest constraintem; priorytet: poprawność i powtarzalność.

## Ryzyka (nazwane, zaakceptowane lub do mitygacji)

| Ryzyko | Mitygacja |
|---|---|
| LLM na N=kilkanaście pomiarów generuje przekonujące hipotezy, nie analizę | Raporty oznaczane jako hipotezy; JSON umożliwia własną weryfikację SQL-em |
| Ekstrakcja narracyjna gubi/zmyśla ustalenia | Human-in-the-loop na każdym rekordzie + pełny Markdown źródłowy obok |
| Jakość OCR na starych skanach/zdjęciach | Klasyfikacja jakości; dokumenty nieczytelne odrzucane świadomie (licznik do S1) |
| Zatwierdzanie ręczne zniechęci po backfillu | Front-load: słownik nasyca się na pierwszych ~50 dokumentach |
| Limity abonamentu Pro współdzielone z interaktywną pracą w Claude Code | Backfill narracyjny rozłożony w czasie (~3 dok./dzień wystarcza dla S3); przetwarzanie wsadowe poza godzinami własnej pracy; przy wyczerpaniu limitu backfill po prostu zwalnia — świadomie zaakceptowane |
| Zakresy referencyjne różnią się między laboratoriami | Zakres zapisywany per pomiar (z dokumentu), nie globalnie |

## Do weryfikacji w trakcie implementacji

1. **Kolejność implementacji (plan, nie wymaganie):** start od pipeline'u strukturalnego (szybka wygrana, S1/S2), ale walidacja ekstrakcji narracyjnej na 5–10 przykładowych opisach **przed** budową reszty modułu narracyjnego — potwierdzone przez właściciela.
2. **Weryfikacja adresów w Presidio pl:** jakość NER na realnych dokumentach do sprawdzenia na próbce w 1. tygodniu implementacji (PESEL/e-mail/telefon — wbudowane, ryzyko niskie).

### Rozstrzygnięte (runda review 1, 2026-07-17)

- Magazyn danych → katalog NDJSON (bez SQLite).
- Mechanika zatwierdzania → plikowa, `pending/*.yml` przeglądane w Claude Code.
- Struktura backfillu → ~70% narracyjne / ~30% strukturalne.
- Progi Success Criteria S1–S5 → zatwierdzone bez zmian.
- Kolejność anonimizacji → Presidio zawsze przed wysyłką tekstu dokumentu do API; wyjątek: weryfikacja aliasów (sama nazwa markera).
- Wybór LLM → wyłącznie Claude przez abonament Pro (Claude Code headless, `claude -p`), zero tokenów API; mały model do aliasów: Haiku; lokalny model: eksperyment poza V1. Konsekwencja: tempo backfillu ograniczone limitami abonamentu — zaakceptowane (przy ~3 dok./dzień S3 pozostaje osiągalne w 3 miesiące).
- Presidio pl_PL → research wykonany 2026-07-17: `PlPeselRecognizer` wbudowany, polski NER przez spaCy `pl_core_news_lg`; szczegóły w Tech Constraints.
