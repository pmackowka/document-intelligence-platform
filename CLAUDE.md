# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stan projektu

Faza przed implementacją — repozytorium zawiera na razie wyłącznie dokumentację. **`docs/prd.md` jest kontraktem: każdą sesję zaczynaj od jego przeczytania i działaj zgodnie z nim.** Każda zmiana zakresu wymaga aktualizacji `docs/prd.md`, nie tylko kodu. `docs/Document-Intelligence-Platform.md` to pierwotny zarys z roadmapą wersji V1–V5 — kontekst historyczny; przy sprzeczności wygrywa PRD.

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
- **Kolejność implementacji**: pipeline strukturalny najpierw, ale ekstrakcję narracyjną zwaliduj na 5–10 przykładowych opisach zanim zbudujesz wokół niej resztę.

## Stack i ograniczenia techniczne

- **Python** — cała logika biznesowa (OCR, standaryzacja, anonimizacja, zapis). **n8n** — wyłącznie orkiestracja, zero logiki.
- **OCR**: Docling (główny silnik) + Apple Vision jako backend dla zdjęć. Środowisko: lokalnie na macOS.
- **Anonimizacja**: Microsoft Presidio — `PlPeselRecognizer` wbudowany; polski NER wymaga spaCy `pl_core_news_lg` jako NLP engine.
- **LLM: wyłącznie Claude przez abonament Pro — zero zakupu tokenów API.** Wywołania programistyczne przez Claude Code headless: `claude -p "<prompt>"` jako komenda shell z Pythona/n8n. Weryfikacja aliasów: Haiku (`--model`). Nie dodawaj kodu używającego kluczy API Anthropic ani SDK z rozliczeniem tokenowym.
- Kod i nazwy po angielsku, komentarze i docstringi po polsku.

## Praca etapami — `docs/stages/`

Implementacja podzielona na etapy `00`–`08`; każdy plik w `docs/stages/` ma sekcje: Cel, Zakres/DoD, Decyzje i dlaczego, Jak to działa, Gotchas. Kolejność plików = kolejność pracy (zależności: etap 5 wymaga 2 i 4).

**Workflow obowiązkowy w każdej sesji implementacyjnej:**

1. Na starcie ustal bieżący etap: pierwszy plik w `docs/stages/` z nieodhaczonymi checkboxami. Przeczytaj go przed rozpoczęciem pracy.
2. **Natychmiast po wykonaniu akcji z checkboxa odhacz go** (z datą i konkretem, np. numerem commita) — nie na końcu sesji, nie „w domyśle". Deklaracja w czacie, że coś zrobiono, bez edycji pliku etapu = zadanie niewykonane.
3. Wykonana praca spoza checkboxów, która domyka element etapu — dopisz jako nowy odhaczony checkbox.

Reguły prowadzenia tych plików (projekt służy też nauce właściciela):

- Podczas pracy nad etapem **dopisuj do jego pliku** decyzje z uzasadnieniem, mechanizmy narzędzi (jak coś działa pod spodem) i gotchas — z krótkim kontekstem edukacyjnym.
- **Nie prowadź tam logu czynności** („zrobiliśmy X, potem Y") — od tego jest git history. Zapisuj tylko to, co nieoczywiste i użyteczne za miesiąc.
- Nie powielaj treści PRD — zakres i wymagania żyją w `docs/prd.md`.
- Odhaczaj checkboxy w Zakres/DoD w miarę realizacji; etap skończony = wszystkie odhaczone lub świadomie skreślone z adnotacją.

## Out of scope V1 (nie implementuj bez zmiany PRD)

Domeny inne niż medyczna; UI/dashboard/wykresy; automatyczny load do BigQuery; dziennik interwencji/stylu życia; RAG, wektorowe bazy, FastAPI/Docker/Cloud Run, MCP server, agenci (to wersje V2–V5 z zarysu).
