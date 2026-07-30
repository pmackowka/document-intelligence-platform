# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stan projektu

Faza przed implementacją — repozytorium zawiera na razie wyłącznie dokumentację. **`docs/v1/prd.md` jest kontraktem: każdą sesję zaczynaj od jego przeczytania i działaj zgodnie z nim.** Każda zmiana zakresu wymaga aktualizacji `docs/v1/prd.md`, nie tylko kodu. `docs/roadmap.md` to backlog wersji V2–V5 — nie implementuj z niego niczego w ramach V1.

Dokumentacja etapowa żyje płasko pod `docs/<wersja>/` (`docs/v1/`, `docs/v2/`, ...) — każda wersja ma własny `prd.md` i pliki etapów `00`–`NN` bezpośrednio w tym folderze (bez pośredniego podfolderu `stages/` — za dużo klikania), zgodnie z regułą z `docs/roadmap.md` („każda wersja przed startem przechodzi własną sesję sokratejską i dostaje własny PRD"). `docs/v2/` istnieje na razie wyłącznie jako szkielet (`docs/v2/00-planning.md`) — sesja sokratejska i PRD V2 jeszcze się nie odbyły; sekcja „Praca etapami" poniżej opisuje workflow `docs/v1/`, bo to jedyny etap aktualnie w toku.

## Czym jest ten projekt

Lokalna platforma do przetwarzania osobistej dokumentacji medycznej (~390 plików: PDF, skany, zdjęcia) z analizą trendów w czasie. Jeden użytkownik (właściciel repo), zero UI — konsumpcja przez pliki i Claude Code w terminalu.

## Architektura V1 (z PRD — kluczowe decyzje)

Jeden pipeline — dane strukturalne (badania krwi/moczu): OCR → standaryzacja (dictionary mapping z `aliases.yml` → regex na wartości → weryfikacja LLM nieznanych nazw) → kanoniczny JSON z jednostkami i zakresami referencyjnymi.

Zasady przekrojowe:

- **Human-in-the-loop obowiązkowy**: propozycje aliasów trafiają do `pending/*.yml`; pipeline czyta wyłącznie zatwierdzone wpisy. Operator zatwierdza edytując pliki w Claude Code.
- **Reguła prywatności**: do API/LLM idzie wyłącznie nazwa markera (Warstwa 3, weryfikacja nieznanych nazw) — nigdy pełna treść dokumentu.
- **Magazyn danych**: katalog NDJSON, płaskie rekordy, schemat BigQuery-ready (ręczny load; bez SQLite, bez bazy). Zaufany plik: `data/store/structural-backfill.ndjson`. **Każdy przebieg `structural_pipeline.py` zapisuje osobną, datowaną migawkę (`data/store/YYYY-MM-DD-structural.ndjson`) — kod NIGDY nie nadpisuje `structural-backfill.ndjson` bezpośrednio.** Ten plik zmienia się wyłącznie przez ręczne scalenie (kopię) potwierdzonej migawki, na wyraźną prośbę operatora po jego weryfikacji raportu — nie automatycznie przy każdym uruchomieniu. Nie „upraszczaj" tego z powrotem do bezpośredniego zapisu — to świadoma bariera przed cichym dryfem już zweryfikowanych danych (PRD v1.3; pełne uzasadnienie i mechanizm: `docs/v1/04-backfill.md`, notatki „Migawki datowane + scalenie ręczne" i „Nazwa zaufanego pliku").
- **Pułapka raportów (realnie się zdarzyła, 2026-07-22)**: `report.py` zapisuje wynik zawsze pod `data/reports/YYYY-MM-DD-trendy.md`, NIEZALEŻNIE od tego, czy czytał zaufany magazyn (`structural-backfill.ndjson`) czy migawkę-kandydata — dwa uruchomienia tego samego dnia (raz z argumentem-kandydatem, raz bez argumentu) cicho nadpiszą się nawzajem, bez ostrzeżenia w kodzie. Realny incydent: raport bazowy z zaufanego magazynu został nadpisany raportem z kandydata, bo oba trafiły pod tę samą nazwę pliku tego samego dnia. **Terminal zawsze pokazuje tryb** (`Raport (KANDYDAT, źródło: ...)` vs `Raport (zaufany magazyn, źródło: ...)`) — sprawdź go PRZED każdym kolejnym uruchomieniem `report.py` tego samego dnia. To dziś wyłącznie dyscyplina proceduralna, nie zabezpieczenie w kodzie — jeśli operator poprosi o wygenerowanie obu raportów (kandydat + zaufany) jednego dnia, przenieś/zmień nazwę pierwszego, zanim uruchomisz drugi. Nie zmieniaj zachowania `report.py` bez wyraźnej prośby operatora — to nie jest miejsce na samodzielną inicjatywę (patrz zasada niżej o modyfikacji kodu tylko na wyraźną prośbę).
- **Modyfikacja kodu tylko na wyraźną prośbę operatora.** Jeśli podczas realizacji prośby (np. „uruchom pipeline i poczekaj na moją weryfikację") natrafisz na błąd w kodzie — **zatrzymaj się i zgłoś go w czacie**, nie naprawiaj go od razu. Operator sam decyduje, czy i kiedy naprawa ma się zacząć — nawet dobrze zdiagnozowana, realna poprawka bez pytania łamie zaufanie do „Ty weryfikujesz, ja wykonuję" (incydent 2026-07-22: naprawa bez pytania w trakcie prośby o samo uruchomienie pipeline'u).
- **Wiedza domenowa w YAML**, nie w kodzie: `aliases.yml` (panel-aware, pole `format: table|section`), `units.yml`, `marker_labels.yml` (kod kanoniczny → polska etykieta do raportów), `reference_ranges.yml`, `laboratories.yml`. Dodanie laboratorium/panelu nie może wymagać zmiany kodu.
- **Ścieżki artefaktów (reguła prywatności)**: wszystko, co zawiera treść medyczną — surowe dokumenty, `pending/` (propozycje aliasów/ustaleń), magazyn NDJSON — żyje pod `data/` (w `.gitignore`). Wersjonowane są wyłącznie `config/` (YAML domenowy bez PII), kod i docs. Nigdy nie twórz plików z treścią medyczną poza `data/`.

  | Ścieżka | Zawartość | Etap potoku | Git | Kiedy zapełniane |
  |---|---|---|---|---|
  | `config/` | YAML domenowy (`aliases`, `units`, `marker_labels`, `reference_ranges`, `laboratories`) | — | wersjonowany | etap 2 |
  | `src/` | kod Python (logika biznesowa) | — | wersjonowany | od etapu 0 |
  | `data/raw/structural/` | surowe dok. strukturalne (krew/mocz) | **surowy** | lokalnie | ingest (próbka: etap 1) |
  | `data/interim/` | wyjście pośrednie: OCR-owany MD/JSON | **pośredni** | lokalnie | etap 1 (OCR) |
  | `data/pending/` | propozycje aliasów do zatwierdzenia | kontrola (HITL) | lokalnie | etap 2 |
  | `data/store/` | migawki datowane (kandydaci) + `structural-backfill.ndjson` (zaufany, scalany ręcznie) | **finalny — dane** | lokalnie | etap 2, 4 |
  | `data/reports/` | **finalne** raporty Markdown (trendy, na wizytę) | **finalny — raport** | lokalnie | etap 3 |

  Podfoldery `data/` istnieją tylko lokalnie (git nie śledzi ignorowanych ścieżek) — kod pipeline'u tworzy je przy starcie (`mkdir -p`).

  Ingest ląduje w `data/raw/structural/` — operator dodaje pliki ręcznie i uruchamia pipeline z terminala, bez klasyfikacji (V1 obsługuje wyłącznie dokumenty strukturalne, nie ma czego routować). Brak konektora Google Drive (usunięty w PRD v1.1).

## Stack i ograniczenia techniczne

- **Python** — cała logika biznesowa (OCR, standaryzacja, zapis). Uruchamianie ręczne z terminala (`uv run python ...`); brak orkiestratora w V1 (n8n usunięty w PRD v1.2 — Apple Vision wymaga macOS, nie działa w kontenerze Docker).
- **OCR**: Docling (główny silnik) + Apple Vision jako backend dla zdjęć. Środowisko: lokalnie na macOS.
- **LLM: wyłącznie Claude przez abonament Pro — zero zakupu tokenów API.** Wywołania programistyczne przez Claude Code headless: `claude -p "<prompt>"` jako komenda shell z Pythona. Weryfikacja aliasów: Haiku (`--model`). Nie dodawaj kodu używającego kluczy API Anthropic ani SDK z rozliczeniem tokenowym.
- Kod i nazwy po angielsku, komentarze i docstringi po polsku.
- Diagramy Mermaid: etykiety węzłów zawsze w cudzysłowach (`A["..."]`), bez znaku `"` w treści etykiet — pełne reguły i historia incydentu na końcu `docs/roadmap.md`.

## Praca etapami — `docs/v1/`

Implementacja podzielona na etapy `00`–`04`; każdy plik w `docs/v1/` ma sekcje: **Cel**, **Zakres / Definition of Done** (checkboxy = kroki) i **Notatki**. Kolejność plików = kolejność pracy.

**Workflow obowiązkowy w każdej sesji implementacyjnej:**

1. Na starcie ustal bieżący etap: pierwszy plik w `docs/v1/` z nieodhaczonymi checkboxami. Przeczytaj go przed rozpoczęciem pracy.
2. **Natychmiast po wykonaniu akcji z checkboxa odhacz go** (z krótkim konkretem co zrobiono — bez dat i numerów commitów, chronologię trzyma git) — nie na końcu sesji, nie „w domyśle". Deklaracja w czacie, że coś zrobiono, bez edycji pliku etapu = zadanie niewykonane.
3. Wykonana praca spoza checkboxów, która domyka element etapu — dopisz jako nowy odhaczony checkbox.

**Sekcja `## Notatki` — jak ją prowadzić** (projekt służy też nauce właściciela; te notatki są materiałem do czytania i powtórki):

- **Grupuj po temacie, nie po dacie.** Każdy temat to nagłówek `### <czego dotyczy>` (zwykle krok z Zakresu lub użyte narzędzie), a pod nim samodzielna notatka do nauki.
- Pod tematem układ: **Decyzja** (co ustalono) → **Dlaczego** (uzasadnienie, trade-offy) → **Jak działa** (mechanizm narzędzia pod spodem — sedno wartości edukacyjnej) → **Pułapki** (co zaskoczyło). Nie każdy temat wymaga wszystkich czterech. **Każdy podpunkt w osobnym akapicie** (pusta linia między nimi) — inaczej markdown skleja je w jeden blok i notatka jest nieczytelna.
- **Etykiety akapitów to zbiór zamknięty: dokładnie `Decyzja` / `Dlaczego` / `Jak działa` / `Pułapki` (lub podzbiór).** Nie wymyślaj własnych etykiet (np. wiązanych z numerami DoD w stylu „Struktura przeżywa (punkt 3):") ani nie łącz dwóch w jedną („Jak działa / Pułapki:"). Ta sama struktura obowiązuje we **wszystkich** plikach `docs/v1/`; wzorzec = `docs/v1/00-setup.md`. Trzymaj ją stałą między sesjami — nie zmieniaj konwencji.
- **Bez dat** — chronologię trzyma git; notatka ma być czytelnym wyjaśnieniem, nie changelogiem.
- **Nie log czynności** („zrobiliśmy X, potem Y") — zapisuj tylko to, co nieoczywiste i użyteczne za miesiąc.
- Nie powielaj treści PRD — zakres i wymagania żyją w `docs/v1/prd.md`.

Etap skończony = wszystkie checkboxy odhaczone lub świadomie skreślone z adnotacją.

## Out of scope V1 (nie implementuj bez zmiany PRD)

Domeny inne niż medyczna; przetwarzanie dokumentów narracyjnych (USG/MRI/TK/kolonoskopia); orkiestracja przez n8n (usunięta w PRD v1.2 — uruchamianie ręczne z terminala); UI/dashboard/wykresy; automatyczny load do BigQuery; dziennik interwencji/stylu życia; FastAPI/Docker/Cloud Run, MCP server, agenci (to wersje V2–V4 z zarysu).

Jeśli przy okazji innej pracy natkniesz się na plik, fragment kodu lub dokumentu dotyczący **wyłącznie** przetwarzania danych narracyjnych — zgłoś operatorowi do potwierdzenia, nie usuwaj automatycznie. Nie skanuj repo proaktywnie w tym celu, tylko przy okazji.
