# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stan projektu

Faza przed implementacją — repozytorium zawiera na razie wyłącznie dokumentację. **`docs/prd.md` jest kontraktem: każdą sesję zaczynaj od jego przeczytania i działaj zgodnie z nim.** Każda zmiana zakresu wymaga aktualizacji `docs/prd.md`, nie tylko kodu. `docs/roadmap.md` to backlog wersji V2–V5 — nie implementuj z niego niczego w ramach V1.

## Czym jest ten projekt

Lokalna platforma do przetwarzania osobistej dokumentacji medycznej (~390 plików: PDF, skany, zdjęcia) z analizą trendów w czasie. Jeden użytkownik (właściciel repo), zero UI — konsumpcja przez pliki i Claude Code w terminalu.

## Architektura V1 (z PRD — kluczowe decyzje)

Dwie klasy dokumentów, dwa pipeline'y:

- **Strukturalne** (badania krwi/moczu, ~30% wolumenu): OCR → standaryzacja (dictionary mapping z `aliases.yml` → regex na wartości → weryfikacja LLM nieznanych nazw) → kanoniczny JSON z jednostkami i zakresami referencyjnymi.
- **Narracyjne** (opisy USG/MRI/TK, ~70% wolumenu): OCR → anonimizacja → ekstrakcja ustaleń przez LLM do schematu (`finding`, `location`, `measurement_value`, `measurement_unit`, `status`, `exam_type`, `exam_date`).

Zasady przekrojowe:

- **Human-in-the-loop obowiązkowy**: propozycje aliasów i wyekstrahowanych ustaleń trafiają do `pending/*.yml`; pipeline czyta wyłącznie zatwierdzone wpisy. Operator zatwierdza edytując pliki w Claude Code.
- **Kolejność anonimizacji (reguła twarda)**: żaden tekst dokumentu nie trafia do zewnętrznego API przed Presidio. Jedyny wyjątek: weryfikacja aliasów (sama nazwa markera, bez PII).
- **Magazyn danych**: katalog NDJSON, płaskie rekordy append-only, schemat BigQuery-ready (ręczny load; bez SQLite, bez bazy).
- **Wiedza domenowa w YAML**, nie w kodzie: `aliases.yml`, `units.yml`, `reference_ranges.yml`, `laboratories.yml`. Dodanie laboratorium nie może wymagać zmiany kodu.
- **Ścieżki artefaktów (reguła prywatności)**: wszystko, co zawiera treść medyczną — surowe dokumenty, `pending/` (propozycje aliasów/ustaleń), magazyn NDJSON — żyje pod `data/` (w `.gitignore`). Wersjonowane są wyłącznie `config/` (YAML domenowy bez PII), kod i docs. Nigdy nie twórz plików z treścią medyczną poza `data/`.

  | Ścieżka | Zawartość | Git | Kiedy zapełniane |
  |---|---|---|---|
  | `config/` | YAML domenowy (`aliases`, `units`, `reference_ranges`, `laboratories`) | wersjonowany | etap 3 |
  | `src/` | kod Python (logika biznesowa) | wersjonowany | od etapu 0 |
  | `data/raw/structural/` | surowe dok. strukturalne (krew/mocz) | lokalnie | ingest (próbka: etap 1) |
  | `data/raw/narrative/` | surowe dok. narracyjne (USG/MRI/TK) | lokalnie | ingest (próbka: etap 1) |
  | `data/interim/` | wyjście pośrednie: OCR-owany + zanonimizowany MD/JSON | lokalnie | etap 1 (OCR), 5 (anonimizacja) |
  | `data/pending/` | propozycje aliasów/ustaleń do zatwierdzenia | lokalnie | etap 3 (aliasy), 5 (ustalenia) |
  | `data/store/` | magazyn NDJSON — źródło prawdy, BigQuery-ready | lokalnie | etap 3, 5, 8 |
  | `data/reports/` | **finalne** raporty Markdown (trendy, na wizytę) | lokalnie | etap 6 |

  Podfoldery `data/` istnieją tylko lokalnie (git nie śledzi ignorowanych ścieżek) — kod pipeline'u tworzy je przy starcie (`mkdir -p`).

  Podział `data/raw/{structural,narrative}/` to **realny układ ingestu**: klasę nadaje operator ręcznie przy uploadzie przez n8n (human-in-the-loop, nie klasyfikator automatyczny — PRD Scope V1 pkt 3), a plik ląduje w podfolderze swojej klasy. Ingest wyłącznie ręczny — **brak konektora Google Drive** (usunięty w PRD v1.1).
- **Kolejność implementacji**: pipeline strukturalny najpierw, ale ekstrakcję narracyjną zwaliduj na 5–10 przykładowych opisach zanim zbudujesz wokół niej resztę.

## Stack i ograniczenia techniczne

- **Python** — cała logika biznesowa (OCR, standaryzacja, anonimizacja, zapis). **n8n** — wyłącznie orkiestracja, zero logiki.
- **OCR**: Docling (główny silnik) + Apple Vision jako backend dla zdjęć. Środowisko: lokalnie na macOS.
- **Anonimizacja**: Microsoft Presidio — `PlPeselRecognizer` wbudowany; polski NER wymaga spaCy `pl_core_news_lg` jako NLP engine.
- **LLM: wyłącznie Claude przez abonament Pro — zero zakupu tokenów API.** Wywołania programistyczne przez Claude Code headless: `claude -p "<prompt>"` jako komenda shell z Pythona/n8n. Weryfikacja aliasów: Haiku (`--model`). Nie dodawaj kodu używającego kluczy API Anthropic ani SDK z rozliczeniem tokenowym.
- Kod i nazwy po angielsku, komentarze i docstringi po polsku.
- Diagramy Mermaid: etykiety węzłów zawsze w cudzysłowach (`A["..."]`), bez znaku `"` w treści etykiet — pełne reguły i historia incydentu na końcu `docs/roadmap.md`.

## Praca etapami — `docs/stages/`

Implementacja podzielona na etapy `00`–`08`; każdy plik w `docs/stages/` ma sekcje: **Cel**, **Zakres / Definition of Done** (checkboxy = kroki) i **Notatki**. Kolejność plików = kolejność pracy (zależności: etap 5 wymaga 2 i 4).

**Workflow obowiązkowy w każdej sesji implementacyjnej:**

1. Na starcie ustal bieżący etap: pierwszy plik w `docs/stages/` z nieodhaczonymi checkboxami. Przeczytaj go przed rozpoczęciem pracy.
2. **Natychmiast po wykonaniu akcji z checkboxa odhacz go** (z krótkim konkretem co zrobiono — bez dat i numerów commitów, chronologię trzyma git) — nie na końcu sesji, nie „w domyśle". Deklaracja w czacie, że coś zrobiono, bez edycji pliku etapu = zadanie niewykonane.
3. Wykonana praca spoza checkboxów, która domyka element etapu — dopisz jako nowy odhaczony checkbox.

**Sekcja `## Notatki` — jak ją prowadzić** (projekt służy też nauce właściciela; te notatki są materiałem do czytania i powtórki):

- **Grupuj po temacie, nie po dacie.** Każdy temat to nagłówek `### <czego dotyczy>` (zwykle krok z Zakresu lub użyte narzędzie), a pod nim samodzielna notatka do nauki.
- Pod tematem układ: **Decyzja** (co ustalono) → **Dlaczego** (uzasadnienie, trade-offy) → **Jak działa** (mechanizm narzędzia pod spodem — sedno wartości edukacyjnej) → **Pułapki** (co zaskoczyło). Nie każdy temat wymaga wszystkich czterech. **Każdy podpunkt w osobnym akapicie** (pusta linia między nimi) — inaczej markdown skleja je w jeden blok i notatka jest nieczytelna.
- **Etykiety akapitów to zbiór zamknięty: dokładnie `Decyzja` / `Dlaczego` / `Jak działa` / `Pułapki` (lub podzbiór).** Nie wymyślaj własnych etykiet (np. wiązanych z numerami DoD w stylu „Struktura przeżywa (punkt 3):") ani nie łącz dwóch w jedną („Jak działa / Pułapki:"). Ta sama struktura obowiązuje we **wszystkich** plikach `docs/stages/`; wzorzec = `docs/stages/00-setup.md`. Trzymaj ją stałą między sesjami — nie zmieniaj konwencji.
- **Bez dat** — chronologię trzyma git; notatka ma być czytelnym wyjaśnieniem, nie changelogiem.
- **Nie log czynności** („zrobiliśmy X, potem Y") — zapisuj tylko to, co nieoczywiste i użyteczne za miesiąc.
- Nie powielaj treści PRD — zakres i wymagania żyją w `docs/prd.md`.

Etap skończony = wszystkie checkboxy odhaczone lub świadomie skreślone z adnotacją.

## Out of scope V1 (nie implementuj bez zmiany PRD)

Domeny inne niż medyczna; UI/dashboard/wykresy; automatyczny load do BigQuery; dziennik interwencji/stylu życia; RAG, wektorowe bazy, FastAPI/Docker/Cloud Run, MCP server, agenci (to wersje V2–V5 z zarysu).
