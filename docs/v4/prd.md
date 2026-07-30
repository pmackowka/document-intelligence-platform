# PRD: Document Intelligence Platform — Version 4 (Architektura agentowa)

> Status: **v4.1 — zatwierdzony**.
> Kontrakt V1 (`docs/v1/prd.md`) i V2 (`docs/v2/prd.md`) pozostają zamknięte i niezmienione — V4 buduje na module V2 bez re-otwierania jego ustaleń.
> V3 (przeniesienie do chmury) świadomie pominięta — decyzja i uzasadnienie: `docs/roadmap.md`, sekcja „Zasada kolejności".
> Terminologia domenowa: `CONTEXT.md`. Decyzje architektoniczne V2, wciąż obowiązujące: `docs/adr/0001-mcp-stdio-no-listening-port.md` (transport), `docs/adr/0002-mcp-read-only.md` (wyłącznie odczyt) — V4 nie zmienia żadnej z nich, tylko dokłada warstwę agentową nad tym samym serwerem.
>
> **v4.1 (runda review 1):** trzy luki z v4.0 rozstrzygnięte i zweryfikowane empirycznie (nie tylko dokumentacją) — nazewnictwo plików wyjściowych bez ryzyka nadpisania, potwierdzony mechanizm zawężenia toolsetu/pamięci w `ClaudeAgentOptions`, trójwarstwowa strategia weryfikacji analogiczna do V2.

---

## Problem

V2 udostępniło dane przez MCP, ale wymaga, żeby operator sam wiedział, o który marker zapytać, i sam złożył wynik w całość — dokładnie tyle, ile zwróci pojedyncze wywołanie `get_marker_trend` albo `compare_markers`. Przygotowanie się do wizyty u konkretnego specjalisty (np. nefrologa) wymaga wiedzy, KTÓRE markery są istotne, i ręcznego złożenia kilku zapytań w spójną całość.

To nie jest problem z dostępem do danych (V2 to rozwiązało) — to problem z planowaniem: operator musi sam być „agentem" łączącym kroki. V4 nie buduje nowej analityki ani nowych narzędzi — dokłada warstwę, która sama planuje, które z istniejących dwóch narzędzi V2 wywołać i w jakiej kolejności, żeby odpowiedzieć na jedno, otwarte pytanie.

## User Persona

Ta sama osoba co w V1/V2 — jeden użytkownik, właściciel projektu i danych. W V4 dochodzi nowy tryb pracy: operator formułuje jedno, otwarte zapytanie (np. „przygotuj mnie do wizyty u nefrologa"), zamiast samodzielnie dobierać marker i wywoływać narzędzie wprost.

**Anty-persona:** bez zmian względem V1/V2.

## Success Criteria

| # | Kryterium | Próg |
|---|---|---|
| S1 | Agent poprawnie obsługuje pojedynczy marker bez wskazania narzędzia | Realne zapytanie naturalnym językiem o jeden marker (np. „jak wygląda mój poziom ferrytyny w czasie"), bez nazwania `get_marker_trend` czy kodu markera wprost — agent sam rozpoznaje potrzebę wywołania narzędzia i poprawnie identyfikuje marker |
| S2 | Agent planuje i wykonuje zadanie wieloetapowe | Realne, otwarte zapytanie (np. „przygotuj mnie do wizyty u nefrologa"), bez wskazania narzędzi/markerów — agent samodzielnie planuje potrzebne dane (np. kreatynina, eGFR), wywołuje `get_marker_trend`/`compare_markers` dla właściwych markerów, syntetyzuje wynik w raport zapisany do `data/agent/` z realnymi danymi i pytaniami do lekarza |

Oba kryteria wymagają dowodu end-to-end na realnych danych — sama poprawna odpowiedź techniczna serwera MCP (już potwierdzona w V2) nie wystarcza; tu weryfikujemy warstwę planowania nad nim.

## Scope V4

### In scope (must have)

1. **Claude Agent SDK** (`claude-agent-sdk`), tryb jednorazowy (`query()`, nie `ClaudeSDKClient`) — zgodnie z resztą projektu (bezstanowe, terminal-native wywołania, jak V1/V2).
2. **Uwierzytelnianie wyłącznie przez istniejący abonament Claude Pro** — zero kluczy API, zero rozliczenia per token. Potwierdzone spike'em: `apiKeySource: 'none'`, zużycie z puli `rate_limit_type: 'five_hour'` (subskrypcja), nie z Anthropic Console/API billing.
3. **Zawężony toolset agenta** — wyłącznie klient MCP do dwóch istniejących narzędzi z V2 (`get_marker_trend`, `compare_markers`), bez wbudowanych narzędzi Claude Code (Bash, Write, Edit, Read na systemie plików itd.). Domyślna sesja Agent SDK dziedziczy pełny toolset Claude Code — to świadome zawężenie, nie ustawienie domyślne.
4. **Wyłączone auto-memory / zminimalizowane dziedziczenie configu sesji** — sesja agenta V4 nie ma dostępu do mechanizmu pamięci międzysesyjnej Claude Code (ten sam katalog `memory_paths`, którego używają zwykłe sesje Claude Code w tym repo). Powód: agent przetwarza realne dane medyczne w swoim rozumowaniu — bez tego zawężenia teoretycznie mógłby zapisać ich fragment jako trwałą pamięć, czego V1/V2 nigdy nie robiły (żaden z nich nie ma mechanizmu pamięci Claude Code).
5. **Brak nowych narzędzi MCP** — V4 orkiestruje wyłącznie dwa istniejące narzędzia z V2. `search_findings` (przeszukiwanie/wyszukiwanie dokumentów) pozostaje poza zakresem, tak jak w PRD V2.
6. **Zapis wyniku do dedykowanego folderu, bez ryzyka nadpisania** — `data/agent/YYYY-MM-DD-<temat>.md`, osobno od `data/reports/` (V1). `<temat>` to slug wygenerowany z treści zapytania; jeśli plik o tej nazwie już istnieje (kolejne wywołanie tego samego dnia), kod dopisuje licznik (`-2`, `-3`...) zamiast nadpisywać — nowy kod, więc ochrona wbudowana od początku, nie dyscyplina proceduralna jak przy incydencie z `report.py` (2026-07-22, `CLAUDE.md`).

### Out of scope (not now)

- **Tryb wieloturowy / interaktywny** (`ClaudeSDKClient`) — V4 to jednorazowe zapytanie, bez dopytywania czy kontynuacji rozmowy. Kandydat na przyszłą wersję, jeśli pojawi się potwierdzona potrzeba.
- **Nowe narzędzia MCP** (`search_findings` i podobne) — patrz Scope, punkt 5.
- **Zapis/akcje modyfikujące dane** — agent V4 dziedziczy „wyłącznie odczyt" z V2 (`docs/adr/0002`); nie zatwierdza aliasów, nie modyfikuje magazynu.
- **Pełny toolset Claude Code** (Bash, Write, Edit, dostęp do systemu plików poza `data/agent/`) — świadomie wyłączone, patrz Scope, punkt 3.
- **Transport sieciowy / hosting zdalny** — V3 nadal pominięta (`docs/roadmap.md`); agent działa lokalnie, nad tym samym lokalnym serwerem MCP co V2.
- Wszystko pozostałe z „Out of scope" PRD V1 i V2 nadal obowiązuje bez zmian.

## User Stories

1. Jako operator chcę zapytać o jeden marker naturalnym językiem, bez pamiętania nazwy narzędzia czy dokładnego kodu, żeby nie musieć znać wewnętrznej struktury systemu.
2. Jako operator przygotowujący się do wizyty u konkretnego specjalisty chcę zadać jedno, otwarte pytanie i dostać gotowy raport z odpowiednimi markerami i pytaniami do lekarza, zamiast samodzielnie planować, o co zapytać.
3. Jako operator chcę mieć pewność, że agent nie ma dostępu do niczego poza dwoma istniejącymi narzędziami odczytu — żadnego zapisu, żadnego dostępu do systemu plików poza własnym folderem wyników.
4. Jako operator chcę mieć pewność, że przetwarzanie moich danych medycznych przez agenta nie zostawia trwałego śladu w pamięci międzysesyjnej Claude Code.

## Threat Model / Privacy (rozszerzenie względem V2)

V2 świadomie rozszerzyło zakres o realne wartości pomiarów trafiające do kontekstu klienta MCP. V4 nie rozszerza tego dalej co do samych danych (agent czyta te same dwa narzędzia, też lokalnie, też stdio) — ale wprowadza **nowy wektor**, którego V1/V2 nie miały: sesja Claude Agent SDK to pełnoprawna sesja Claude Code, z własnym mechanizmem pamięci międzysesyjnej. Zmierzone w spike'u: `memory_paths` sesji wskazywał dokładnie na katalog pamięci używany przez zwykłe sesje Claude Code w tym repo.

**Mitygacja — zweryfikowana empirycznie w rundzie review, dwie niezależne warstwy:**

1. `tools=[]` w `ClaudeAgentOptions` + jawna, jedyna konfiguracja `mcp_servers` (serwer z V2) — potwierdzone: sesja widzi wyłącznie trzy narzędzia serwera V2 (`get_marker_trend`, `compare_markers`, `ping`), zero Read/Write/Bash/Edit i zero pozostałych wbudowanych narzędzi Claude Code. Skoro nie ma Read/Write, agent fizycznie nie może odczytać ani dopisać niczego do plików pamięci, nawet gdyby chciał.
2. `system_prompt={"type": "preset", "preset": "claude_code", "exclude_dynamic_sections": True}` — udokumentowana opcja SDK, która jawnie usuwa auto-memory (i inne dynamiczne sekcje: working directory, git status) z treści promptu systemowego. Metadane `memory_paths` nadal pojawiają się w wiadomości inicjującej sesję (to tylko referencja ścieżki, nie treść) — nieszkodliwe w połączeniu z warstwą 1.

Zasada nadrzędna: agent V4 dostaje wyłącznie to, co niezbędne do wywołania dwóch narzędzi MCP i zapisania wyniku — nic więcej z domyślnej, pełnej sesji Claude Code.

Wymóg prywatności pozostaje **miękki**, bez zmian względem V1/V2.

## Tech Constraints

- **Framework:** `claude-agent-sdk` (Python), potwierdzone działającym spike'em na tym repo — `query()` w trybie jednorazowym, model domyślny (`claude-sonnet-5` w teście), zero zmiennej `ANTHROPIC_API_KEY`.
- **Uwierzytelnianie:** wyłącznie istniejąca sesja `claude` CLI (subskrypcja Pro) — zero kluczy API, zero zakupu tokenów, zgodnie z twardą zasadą projektu (`CLAUDE.md`).
- **Konfiguracja `ClaudeAgentOptions` (zweryfikowana empirycznie w rundzie review, nie tylko z dokumentacji):**
  - `tools=[]` — wyłącza wszystkie wbudowane narzędzia Claude Code (bez tego domyślna sesja dziedziczy pełny toolset: Bash, Write, Edit, Read, ToolSearch, Cron*, SendMessage itd. — potwierdzone w pierwszym, niezawężonym teście).
  - `mcp_servers={"document-intelligence-platform": {...}}` — jedyne źródło narzędzi: te same trzy z serwera V2.
  - `allowed_tools=["mcp__document-intelligence-platform__get_marker_trend", "mcp__document-intelligence-platform__compare_markers"]` — auto-zatwierdzenie tych dwóch narzędzi. Bez tego agent poprawnie planuje wywołanie, ale utyka na prośbie o uprawnienia, bo w trybie jednorazowym nikt nie może jej ręcznie zatwierdzić (znalezione i naprawione w rundzie review).
  - `setting_sources=[]` — bez wczytywania `CLAUDE.md`/ustawień projektu spoza tego, co jawnie skonfigurowane.
  - `system_prompt={"type": "preset", "preset": "claude_code", "exclude_dynamic_sections": True}` — usuwa auto-memory (i inne dynamiczne sekcje) z promptu systemowego.
- **Wyjście:** zapis do `data/agent/YYYY-MM-DD-<temat>.md` z automatyczną ochroną przed nadpisaniem (licznik `-2`, `-3`... przy kolizji nazwy); folder `data/agent/` żyje pod `data/` (w `.gitignore`), zgodnie z regułą prywatności artefaktów z V1.
- **Środowisko:** lokalnie na Macu, jak V1/V2. Bez chmury obliczeniowej (V3 pominięta).
- **Weryfikacja przed produkcją — trzy warstwy rosnącego kosztu (analogicznie do V2):**
  1. Testy jednostkowe czystej logiki — generowanie slugów/nazw plików i ochrona przed kolizją, konstrukcja opcji `ClaudeAgentOptions`.
  2. Izolowana weryfikacja konfiguracji agenta bez pełnego scenariusza — potwierdzenie, że lista dostępnych narzędzi to dokładnie te trzy z serwera V2 i że wywołanie faktycznie się wykonuje (nie utyka na uprawnieniach). Ta warstwa już częściowo wykonana w rundzie review.
  3. Pełne S1/S2 na realnych danych — dopiero to liczy się jako dowód Success Criteria.

## Ryzyka (nazwane, zaakceptowane lub do mitygacji)

| Ryzyko | Mitygacja |
|---|---|
| Agent nie rozpozna potrzeby wywołania narzędzia albo źle zaplanuje kroki dla złożonego zapytania | S1/S2 to wprost test tego scenariusza — nie ma dowodu bez realnego zapytania end-to-end |
| Agent syntetyzuje wynik zawierający liczby/fakty nieoparte na realnych danych z narzędzi (halucynacja) | Do zaadresowania w etapie 1: wymóg, żeby synteza cytowała wyłącznie wartości faktycznie zwrócone przez `get_marker_trend`/`compare_markers`, nie generowała własnych |
| Sesja Agent SDK dziedziczy pełny toolset/pamięć/config Claude Code, jeśli `ClaudeAgentOptions` nie zostanie jawnie zawężone | Zweryfikowane empirycznie w rundzie review — konkretna konfiguracja (`tools=[]`, `mcp_servers`, `setting_sources=[]`, `exclude_dynamic_sections`) opisana w Tech Constraints, nie tylko nazwana jako wymóg |
| Agent poprawnie planuje wywołanie narzędzia, ale utyka na prośbie o uprawnienia w trybie jednorazowym (brak kogoś, kto by ją zatwierdził) | Znalezione i naprawione w rundzie review — `allowed_tools` z jawnie wskazanymi dwoma narzędziami |
| Zużycie limitu pięciogodzinnego (subskrypcja Pro) współdzielone ze zwykłym użyciem Claude Code w tym samym oknie czasowym | Świadomie zaakceptowane — to bezpośrednia konsekwencja wyboru „zero kluczy API"; brak dodatkowej mitygacji na tym etapie |
| V3 (przeniesienie do chmury) wymaga rewizji modelu lokalnego/stdio | Nazwane już w `docs/roadmap.md` i `docs/adr/0001` — nie dotyczy V4, dopóki V3 pozostaje pominięta |

### Rozstrzygnięte (sesja sokratejska)

- Priorytet konflikt nauka/produkt → produkt wygrywa, jak V1/V2.
- Framework agentowy → Claude Agent SDK, wybrany jako jedyny z trzech kandydatów (LangGraph, OpenAI Agents SDK, Claude Agent SDK) działający wyłącznie na subskrypcji Pro bez zakupu tokenów API — potwierdzone spike'em przed zapisaniem PRD.
- Zakres narzędzi agenta → zawężony do klienta MCP (dwa istniejące narzędzia), bez pełnego toolsetu Claude Code.
- Zakres zadań → wyłącznie orkiestracja dwóch istniejących narzędzi z V2, bez nowego narzędzia MCP (`search_findings` nadal poza zakresem).
- Tryb wywołania → jednorazowy (`query()`), nie wieloturowy.
- Wyjście → zapis do pliku, dedykowany folder `data/agent/` (nie `data/reports/`, żeby uniknąć kolizji z V1).
- Kryteria sukcesu → dwa, rosnącej złożoności: S1 (pojedynczy marker, pojedyncze narzędzie) i S2 (planowanie wieloetapowe, przykład z roadmapy).
- Pamięć/prywatność → auto-memory wyłączone dla sesji agenta, jako nowy wymóg nieobecny w V1/V2.

### Rozstrzygnięte (runda review 1)

- Nazewnictwo plików wyjściowych → automatyczna ochrona przed nadpisaniem wbudowana od początku (licznik przy kolizji nazwy tego samego dnia), zamiast dyscypliny proceduralnej jak przy `report.py`.
- Zawężenie toolsetu i pamięci → zweryfikowane empirycznie, nie tylko z dokumentacji SDK: `tools=[]` + `mcp_servers` ogranicza dostępne narzędzia do dokładnie trzech z serwera V2; `exclude_dynamic_sections` usuwa auto-memory z promptu; brak Read/Write to dodatkowa, niezależna bariera.
- Przy okazji weryfikacji znaleziono i naprawiono realną przeszkodę nienazwaną w v4.0: tryb jednorazowy blokuje się na prośbie o uprawnienia bez `allowed_tools`.
- Strategia weryfikacji → trzy warstwy rosnącego kosztu, analogicznie do V2 (testy jednostkowe → izolowana weryfikacja configu agenta → pełne S1/S2 na realnych danych).
