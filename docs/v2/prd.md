# PRD: Document Intelligence Platform — Version 2 (MCP server)

> Status: **v2.0 — pierwsza wersja po sesji sokratejskiej, oczekuje review** (spisany po sesji `/grill-with-docs`, na podstawie `docs/v2/00-planning.md` i `docs/roadmap.md`, sekcja „Version 2 — MCP server").
> Kontrakt V1 (`docs/v1/prd.md`) pozostaje zamknięty i niezmieniony — V2 buduje na jego module bez re-otwierania jego ustaleń.
> Terminologia domenowa: `CONTEXT.md`. Decyzje architektoniczne trudne do odwrócenia: `docs/adr/0001-mcp-stdio-no-listening-port.md`, `docs/adr/0002-mcp-read-only.md`.

---

## Problem

Zaufany magazyn zbudowany w V1 (`data/store/structural-backfill.ndjson`) jest dziś dostępny wyłącznie klientom z dostępem do systemu plików — w praktyce tylko Claude Code w terminalu. Claude Desktop i inne klienty MCP nie mają żadnego sposobu odczytania tych danych, mimo że mechanizm analizy (trend markera, porównanie dwóch markerów) już działa i jest zweryfikowany (V1, S2).

To nie jest problem z jakością analizy — to problem dostępu. V2 nie buduje nowej analityki; otwiera istniejącą na klientów, którzy dziś nie mają do niej wejścia.

## User Persona

Ta sama osoba co w V1 — jeden użytkownik, właściciel projektu i danych. W V2 dochodzi kontekst pracy poza terminalem: operator korzystający z Claude Desktop (albo innego świadomie skonfigurowanego klienta MCP) chce zadać to samo pytanie o trend/porównanie, bez przełączania się do terminala.

**Anty-persona:** bez zmian względem V1 — nie produkt dla pacjentów, lekarzy, organizacji; zero multi-user.

## Success Criteria

| # | Kryterium | Próg |
|---|---|---|
| S1 | `get_marker_trend` zwraca poprawne dane markera, wywołane z Claude Desktop | Realne zapytanie end-to-end (np. „pokaż trend ferrytyny"), bez żadnego ręcznego kroku pośredniego; marker z ≥3 pomiarami |
| S2 | `compare_markers` zwraca N niezależnych serii dla ≥2 markerów, wywołane z Claude Desktop | Realne zapytanie end-to-end (np. „porównaj hemoglobinę i OB"), bez ręcznego kroku pośredniego |

Oba kryteria wymagają dowodu na poziomie produktu (realne połączenie, realne zapytanie z klienta) — sama zielona odpowiedź narzędzia na wywołanie techniczne nie wystarcza. V1 (`03-storage-analysis.md`) pokazało, że „mechanizm działa" i „kryterium spełnione" to różne stwierdzenia.

## Scope V2

### In scope (must have)

1. **MCP server, Python SDK (oficjalny, FastMCP), transport stdio.** Serwer uruchamiany jako subproces przez klienta, na podstawie jego własnej konfiguracji — brak nasłuchującego portu (`docs/adr/0001`).
2. **Wyłącznie odczyt.** Serwer czyta `data/store/structural-backfill.ndjson` (zaufany magazyn) — nigdy migawek-kandydatów. Żadnych narzędzi zapisu; mechanika zatwierdzania aliasów zostaje plikowa, jak w V1 (`docs/adr/0002`).
3. **`get_marker_trend(identyfikator)`**
   - Identyfikator: kod kanoniczny (np. `HGB`) lub polska etykieta (`marker_labels.yml`), reużycie istniejącego mapowania.
   - Gdy marker ma więcej niż jedną serię (różne jednostki pod tym samym kodem, np. NEU w % i tys/µl) — zwraca wszystkie serie, pogrupowane po jednostce. Bez zgadywania, która jednostka jest „właściwa".
   - Wyjście: surowe rekordy serii (`exam_date`, `value`, `value_text`, `unit`, `reference_low`, `reference_high`, `reference_note`, `source_file`). Zero wbudowanej interpretacji (kierunek trendu, delta) — to rola modelu wywołującego, nie narzędzia.
   - Nierozpoznany identyfikator → jawny błąd/status „nie znaleziono" z podpowiedzią najbliższych dopasowań. Nigdy cicha pusta lista (myliłaby się z „marker istnieje, zero pomiarów").
4. **`compare_markers(lista identyfikatorów)`** — ta sama logika identyfikacji/jednostek/braku interpretacji co `get_marker_trend`, zastosowana do N markerów. Zwraca N niezależnych serii. Świadomie bez łączenia po dacie badania (wymagałoby zgadywania, które pomiary „odpowiadają sobie").
5. **Klienci:** Claude Code, Claude Desktop, inne — wyłącznie świadomie skonfigurowani przez operatora (per-klient opt-in w konfiguracji klienta), nie dowolny proces w systemie.

### Out of scope (not now)

- **Zapis/akcje modyfikujące dane** (np. zatwierdzanie propozycji aliasu z poziomu MCP) — zostaje plikowe, jak w V1 (`docs/adr/0002`).
- **Dostęp do migawek-kandydatów** (`data/store/YYYY-MM-DD-structural.ndjson`) — tylko zaufany magazyn.
- **Transport sieciowy / serwer nasłuchujący na porcie** — tylko stdio (`docs/adr/0001`). Rewizja przy V3 (przeniesienie do chmury), nie w V2.
- **Trzecie narzędzie** (`search_findings` lub inne przeszukiwanie/odkrywanie) — poza `get_marker_trend` i `compare_markers`, niepotwierdzone jako potrzebne.
- **Interpretacja medyczna / kierunek trendu wbudowany w narzędzie** — spójne z PRD V1 („raporty to materiał do rozmowy z lekarzem, nie diagnoza").
- Wszystko pozostałe z „Out of scope" PRD V1 nadal obowiązuje bez zmian (inne domeny, dokumenty narracyjne, UI/dashboard, multi-user, twarde gwarancje prywatności).
- V3 (FastAPI/Docker/Cloud Run), V4 (agenci) — kolejne wersje, `docs/roadmap.md`.

## User Stories

1. Jako operator pracujący w Claude Desktop chcę zapytać o trend markera, aby dostać dane bez przełączania się do terminala i bez ręcznego czytania plików.
2. Jako operator chcę porównać dwa markery z poziomu dowolnego świadomie skonfigurowanego klienta MCP, aby szukać zależności między nimi tak jak dziś robię to w Claude Code.
3. Jako operator chcę, żeby błędnie podany lub nierozpoznany marker dał jawny komunikat z podpowiedzią, a nie cichą pustą odpowiedź, żebym nie pomylił literówki z faktycznym brakiem danych.
4. Jako operator chcę mieć pewność, że podłączenie nowego klienta MCP wymaga mojej jawnej konfiguracji, a nie dzieje się przez sam fakt, że serwer działa na moim Macu.

## Threat Model / Privacy (rozszerzenie względem V1)

V1 miało wąską miękką prywatność: do żadnego API/LLM nie szły wartości pomiarów, wyłącznie nazwa markera (Warstwa 3). **V2 świadomie rozszerza ten zakres** — realne wyniki badań (wartości, daty, zakresy referencyjne) trafiają do kontekstu modelu klienta MCP, bo to jest właśnie wartość produktowa V2 (trend/porównanie czytelne dla modelu). To nie przeoczenie — to nazwana zmiana zakresu, analogiczna do decyzji „Warstwa 3" w V1, tylko szerzej.

Mitygacja: granica zaufania przesuwa się z „co idzie do API" na „kto może się połączyć z serwerem". Transport stdio bez nasłuchującego portu (`docs/adr/0001`) oznacza, że dane opuszczają dysk operatora wyłącznie wtedy, gdy operator sam, świadomie, doda serwer do konfiguracji konkretnego klienta. Co dany klient MCP (np. Claude Desktop) robi dalej z danymi w swoim kontekście — pozostaje poza kontrolą tego projektu, tak jak zaufanie do Claude Code było już przyjęte w V1.

Wymóg prywatności pozostaje **miękki** — bez zmian względem V1: to nie system klasy medycznej, produkcyjne wdrożenie wymagałoby self-hostingu i twardych gwarancji, poza zakresem.

## Tech Constraints

- **SDK:** oficjalny Python SDK (z wbudowanym FastMCP) — spójne z całym istniejącym stackiem (`structural_pipeline.py`, `report.py`), zero drugiego stacku językowego tylko dla tej warstwy.
- **Transport:** stdio, bez nasłuchującego portu.
- **Reużycie kodu:** serwer korzysta z istniejącej logiki wczytywania NDJSON i mapowania kod↔etykieta (`marker_labels.yml`) zamiast duplikować ją od nowa.
- **Środowisko:** lokalnie na Macu, jak V1. Bez chmury obliczeniowej.
- **Dane:** czyta wyłącznie `data/store/structural-backfill.ndjson`. Nie zapisuje nigdzie.

## Ryzyka (nazwane, zaakceptowane lub do mitygacji)

| Ryzyko | Mitygacja |
|---|---|
| Wywołujący model źle dopasuje identyfikator markera mimo etykiety | Jawny błąd „nie znaleziono" z podpowiedzią najbliższych dopasowań, nigdy cicha pusta lista |
| Realne wartości pomiarów trafiają teraz do kontekstu modelu klienta MCP (rozszerzenie zakresu względem V1) | Świadomie zaakceptowane jako rdzeń wartości V2; granica zaufania przesunięta na „kto może się połączyć" (stdio, opt-in per klient) zamiast „co idzie do API" |
| Operator błędnie skonfiguruje serwer w nieznanym/niezaufanym kliencie MCP | Poza kontrolą serwera — to decyzja operatora per klient, nazwana wprost w `docs/adr/0001` |
| V3 (przeniesienie do chmury) wymaga rewizji modelu stdio/lokalnego | Nazwane już w `docs/roadmap.md` i `docs/adr/0001` — rewizja threat model to jawny punkt PRD V3, nie coś do rozwiązania teraz |

### Rozstrzygnięte (sesja sokratejska, `/grill-with-docs`)

- Priorytet konflikt nauka/produkt → produkt wygrywa, jak V1.
- Luka produktowa V2 → dostęp z klientów bez własnego dostępu do plików (Claude Desktop, inne), nie zastąpienie działającego już mechanizmu w Claude Code.
- Zapis vs odczyt → wyłącznie odczyt (`docs/adr/0002`).
- Zakres danych → wyłącznie zaufany magazyn, bez migawek-kandydatów.
- Granica klientów → wyłącznie świadomie skonfigurowani, transport stdio (`docs/adr/0001`).
- SDK → Python SDK oficjalny.
- Zestaw narzędzi → `get_marker_trend` + `compare_markers`, bez trzeciego narzędzia.
- Identyfikacja markera → kod kanoniczny lub polska etykieta (`marker_labels.yml`).
- Wieloznaczność jednostki → wszystkie serie, pogrupowane po jednostce.
- Kształt wyjścia → surowe rekordy, zero interpretacji.
- `compare_markers` → N niezależnych serii, bez łączenia po dacie.
- Nieznany marker → jawny błąd z podpowiedzią.
