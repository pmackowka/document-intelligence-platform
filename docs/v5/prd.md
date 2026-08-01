# PRD: Document Intelligence Platform — Version 5 (Prompts i Resources MCP)

> Status: **v5.1 — zatwierdzony** (rozmowa robocza, świadomie bez formalnej sesji `/grilling` — operator
> uznał to za wystarczające dla nadobowiązkowego etapu nauki, analogicznie do decyzji o pominięciu rundy 2
> przy V4).
> Kontrakty V1/V2/V4 pozostają zamknięte i niezmienione — V5 nie zmienia żadnego istniejącego Tool,
> nie dotyka configu agenta z V4, buduje wyłącznie nad serwerem MCP z V2.
> Decyzje architektoniczne V2, wciąż obowiązujące bez rewizji: `docs/adr/0001-mcp-stdio-no-listening-port.md`
> (transport), `docs/adr/0002-mcp-read-only.md` (wyłącznie odczyt).
>
> **v5.1 (runda review):** dwie luki znalezione i domknięte przed zatwierdzeniem — (1) `report://latest`
> ujawniłby treść raportu bez informacji, czy dane pochodzą z zaufanego magazynu czy z niezweryfikowanej
> migawki-kandydata (ta sama klasa niejednoznaczności co incydent z `report.py` z `CLAUDE.md`); naprawione
> w `report.py` (`build_report()` zapisuje teraz `Tryb: {zaufany magazyn|KANDYDAT}` w treści pliku, nie
> tylko w banerze terminala) — `report://latest` dziedziczy tę poprawkę bez dodatkowego kodu. (2) Success
> Criteria S2 i Scope punkt 3 cytowały przykładowy tekst promptu niespójnie (bez/z kropką na końcu) —
> ujednolicone do wersji z kropką (Scope punkt 3 jest specyfikacją literalnego zwracanego tekstu).

---

## Problem

Serwer MCP z V2 wystawia wyłącznie **Tools** — jeden z trzech prymitywów protokołu MCP. Nigdy nie użył
pozostałych dwóch: **Resources** (bierna treść do odczytu, adresowana URI) i **Prompts** (gotowe,
sparametryzowane szablony zapytań, wywoływane przez użytkownika, nie przez model). W zakładkach
„Resources" i „Prompts" MCP Inspectora serwer dziś zwraca pustą listę — nie dlatego, że coś jest zepsute,
tylko dlatego, że `mcp_server.py` nigdy nie zarejestrował niczego pod tymi dekoratorami.

To nie jest luka produktowa w sensie V1–V4 — nikt nie zgłosił potrzeby, żadne kryterium sukcesu
wcześniejszej wersji jej nie wymagało. To świadomy, **nadobowiązkowy** krok nauki: zobaczyć oba
pozostałe prymitywy MCP działające na tym samym, już zbudowanym serwerze, z realnym debugowaniem
w MCP Inspectorze — zamiast poprzestawać na czytaniu o nich w dokumentacji SDK.

## User Persona

Ta sama osoba co w V1/V2/V4 — jeden użytkownik, właściciel projektu i danych. W V5 dochodzi tryb
eksploracyjny: operator uczący się mechaniki protokołu MCP na własnym, realnym serwerze, nie
realizujący nowej potrzeby produktowej.

**Anty-persona:** bez zmian względem V1/V2/V4.

## Success Criteria

| # | Kryterium | Próg |
|---|---|---|
| S1 | Zakładka **Resources** w MCP Inspectorze pokazuje `markers://catalog` i `report://latest` | Wybranie `markers://catalog` zwraca listę kodów i etykiet zgodną z `marker_labels.yml`; wybranie `report://latest` zwraca treść najnowszego pliku z `data/reports/` (albo jawny, czytelny komunikat, jeśli folder jest pusty) |
| S2 | Zakładka **Prompts** w MCP Inspectorze pokazuje `porownaj_markery` z dwoma polami (`marker1`, `marker2`) | Wypełnienie pól (np. `Hemoglobina`, `OB`) i wykonanie zwraca dokładnie tekst „Porównaj moje wyniki Hemoglobina i OB w czasie." |

Oba kryteria weryfikuje **wyłącznie MCP Inspector** — to świadoma różnica względem V2/V4, gdzie dowodem
było realne wywołanie z Claude Desktop. Przy nadobowiązkowym etapie nauki mechanizmu protokołu Inspector
wystarcza jako dowód; podpięcie do Desktopa (patrz Out of scope) zostaje osobnym, opcjonalnym krokiem,
nie blokuje zamknięcia tego etapu.

## Scope V5

### In scope (must have)

1. **Resource `markers://catalog`** — zwraca sformatowaną listę wszystkich kodów i polskich etykiet
   z `marker_labels.yml`, reużywając `load_labels()` z `storage.py` (V2). Zero nowej logiki domenowej.
2. **Resource `report://latest`** — zwraca treść najnowszego pliku z `data/reports/`
   (nazewnictwo `YYYY-MM-DD-trendy.md` z V1, sortowanie leksykograficzne = chronologiczne dzięki
   formatowi ISO). Pusty `data/reports/` → jawny, czytelny komunikat, nie wyjątek ani cicha pusta treść —
   ta sama zasada „nigdy cicha pustka" co przy `MarkerNotFound` w V2.
3. **Prompt `porownaj_markery(marker1, marker2)`** — zwraca sformatowany tekst
   `"Porównaj moje wyniki {marker1} i {marker2} w czasie."`, bez odczytu magazynu, bez wywołania narzędzia.
   Rozwiązuje wprost pułapkę nazwaną w części 2 serii bloga o tym projekcie: dosłowna fraza
   „porównaj hemoglobinę i OB" nie triggerowała `compare_markers`, dopiero dodanie „moje wyniki" i
   „w czasie" zadziałało. Prompt zaszywa tę poprawną frazę raz, w kodzie, zamiast wymagać, żeby operator
   pamiętał ją za każdym razem.
4. **Rejestracja w `mcp_server.py`**, obok istniejących trzech Tools, przez `@mcp.resource(uri)` i
   `@mcp.prompt()` — te same dekoratory FastMCP co `@mcp.tool()`, ten sam plik.
5. **Testy jednostkowe** (warstwa 1 z 2 weryfikacji, patrz Tech Constraints): `report://latest` — wybór
   najnowszego pliku spośród kilku, zachowanie przy pustym folderze; `porownaj_markery` — poprawne
   sformatowanie tekstu dla różnych par identyfikatorów, w tym znaków specjalnych w nazwie markera.
6. **Weryfikacja przez MCP Inspector** (warstwa 2 z 2) — realne wywołanie wszystkich trzech nowych
   elementów, nie tylko przegląd list.

### Out of scope (not now)

- **Podpięcie do Claude Desktop** — realne kliknięcie `+` → Resources/Prompts w Desktopie. Wartościowe,
  ale nadobowiązkowe względem nadobowiązkowego etapu; brak automatycznej weryfikacji z tej sesji (nie mam
  dostępu do live UI operatora) — jeśli operator to zrobi, ścieżka kliknięć to ogólny wzorzec, nie
  gwarantowany zrzut ekranu, bo dokładne nazwy elementów UI mogą się różnić między wersjami appki.
- **Nowe Tools** — zestaw z V2 (`get_marker_trend`, `compare_markers`) zostaje bez zmian; `search_findings`
  nadal poza zakresem, jak w PRD V2 i V4.
- **Zmiana configu agenta V4** — `ClaudeAgentOptions` w `agent.py` (`tools=[]`, `allowed_tools` tylko dla
  dwóch Tools) zostaje bez zmian. Resources i Prompts to warstwa dla klientów czatowych (Inspector,
  Desktop), nie dla jednorazowego wywołania agenta — agent V4 nie przegląda zasobów ani nie wywołuje
  promptów, więc rozszerzenie serwera o nie nie zmienia jego zachowania.
- **Zapis/modyfikacja danych** — Resources i Prompts w MCP są z definicji odczytowe/generujące tekst;
  żaden z trzech nowych elementów nie zapisuje niczego. ADR-0002 (wyłącznie odczyt) zostaje bez rewizji.
- **Transport sieciowy** — bez zmian, wciąż stdio (ADR-0001).

## User Stories

1. Jako operator chcę zobaczyć w MCP Inspectorze, że mój serwer wystawia coś w zakładkach Resources
   i Prompts, nie tylko Tools, żeby zrozumieć różnicę między trzema prymitywami MCP na własnym, realnym
   przykładzie, nie na cudzej dokumentacji.
2. Jako operator chcę mieć dostęp do katalogu markerów jako Resource, żeby docelowo (poza zakresem tego
   PRD) móc dołączyć go do rozmowy i pytać o dostępne dane bez zgadywania identyfikatora.
3. Jako operator chcę mieć gotowy Prompt do porównania dwóch markerów, żeby docelowo nie musieć pamiętać
   poprawnie sformułowanej frazy wyzwalającej narzędzie.

## Threat Model / Privacy (rozszerzenie względem V2/V4)

**Bez rozszerzenia zakresu danych.** `markers://catalog` to wyłącznie metadane domenowe (kody i etykiety
z `marker_labels.yml`) — zero PII, zero wartości pomiarów, ten sam plik konfiguracyjny, który już dziś
czyta `resolve_marker` w V2. `report://latest` niesie te same realne dane medyczne (wartości, daty,
zakresy referencyjne), które już dziś trafiają do kontekstu klienta MCP przez Tools z V2 — to nie nowa
kategoria danych, tylko nowy kształt dostarczenia danych już zaakceptowanych w threat modelu V2. Prompt
`porownaj_markery` nie czyta żadnego pliku — generuje wyłącznie tekst zapytania.

Granica zaufania z V2 (stdio, opt-in per klient) zostaje bez zmian — Resources i Prompts, tak samo jak
Tools, są dostępne wyłącznie klientowi, który sam, świadomie, połączył się z tym serwerem.

## Tech Constraints

- **SDK:** te same dekoratory FastMCP co w V2 — `@mcp.resource(uri)`, `@mcp.prompt()`, obok `@mcp.tool()`
  w `mcp_server.py`. Zero nowej zależności.
- **`report://latest`:** wymaga funkcji znajdującej najnowszy plik w `data/reports/` po nazwie — analogia
  do ochrony przed nadpisaniem w `agent.py` (V4), tylko w drugą stronę: tam szukaliśmy pierwszej wolnej
  nazwy, tu szukamy najnowszej istniejącej. Rozważyć umieszczenie tej funkcji w `storage.py`, jeśli
  logika okaże się reużywalna — decyzja do etapu implementacyjnego, nie przesądzona w tym PRD.
- **Weryfikacja przed uznaniem etapu za zamknięty — dwie warstwy, nie trzy jak V2/V4:**
  1. Testy jednostkowe czystej logiki (patrz Scope, punkt 5).
  2. MCP Inspector — realne wywołanie każdego z trzech nowych elementów.

  Trzecia warstwa z V2/V4 (realny klient docelowy — Desktop) świadomie pominięta jako wymóg tego PRD;
  patrz Out of scope.
- **Środowisko:** lokalnie na Macu, jak V1/V2/V4. Bez zmian w transporcie ani hostingu.

## Ryzyka (nazwane, zaakceptowane lub do mitygacji)

| Ryzyko | Mitygacja |
|---|---|
| `report://latest` nie znajduje żadnego pliku (pusty `data/reports/`) | Jawny, czytelny komunikat zamiast wyjątku albo cichej pustej treści — ta sama zasada co `MarkerNotFound` w V2 |
| Rozjazd między nazwą serwera w `mcp_servers` a nazwą zasobu/prompta w kliencie (ten sam typ pułapki co `allowed_tools` w V4) | Reużyć istniejącą stałą `SERVER_NAME`, nie wpisywać nazw ręcznie w dwóch miejscach |
| Pomylenie roli Resource i Prompt przy pierwszym kontakcie z Inspectorem | To jest właśnie cel etapu — nazwane wprost jako ćwiczenie do zrozumienia różnicy, nie ryzyko do wyeliminowania |
| Operator oczekuje weryfikacji z Desktopa, a S1/S2 dowodzą tylko Inspectorem | Nazwane wprost w Success Criteria i Out of scope — świadoma redukcja rygoru dla nadobowiązkowego etapu, nie przeoczenie |

### Rozstrzygnięte (rozmowa robocza, nie formalna sesja `/grilling`)

- Zakres → dokładnie trzy elementy: `markers://catalog`, `report://latest`, `porownaj_markery`.
  Konkretne przykłady wywołań (pola promptu, treść zapytań) ustalone w rozmowie, nie wymyślone przy
  pisaniu PRD.
- Dowód gotowości → wyłącznie MCP Inspector, nie Claude Desktop — świadoma redukcja względem V2/V4,
  nazwana wprost, nie domyślna.
- Config agenta V4 → bez zmian, V5 to warstwa dla klientów czatowych, nie dla agenta jednorazowego.
- Threat model → bez rozszerzenia zakresu danych względem V2; nowy kształt dostarczenia tych samych,
  już zaakceptowanych danych.

### Rozstrzygnięte (runda review)

- `report://latest` a zaufanie do danych → domknięte poprawką w `report.py` (patrz nagłówek dokumentu),
  nie zmianą zakresu tego PRD.
- Niespójność cytatu w S2/Scope → ujednolicona (wersja z kropką).

Operator potwierdził ten zakres — status „zatwierdzony" (patrz nagłówek).
