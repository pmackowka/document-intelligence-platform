# Etap 1 (V4) — agent nad serwerem MCP z V2

## Cel

Zbudować `src/agent.py` — pierwszy realny skrypt używający Claude Agent SDK do orkiestracji dwóch istniejących narzędzi MCP z V2 (`get_marker_trend`, `compare_markers`), zgodnie z konfiguracją `ClaudeAgentOptions` już zweryfikowaną empirycznie podczas rundy review PRD (`docs/v4/prd.md`, notatka w `docs/v4/00-planning.md`).

Najtrudniejsze niewiadome — czy framework w ogóle działa wyłącznie na subskrypcji Claude Pro (bez klucza API), i czy da się zawęzić toolset agenta oraz wyłączyć auto-memory — są już rozstrzygnięte spike'em wykonanym w trakcie sesji sokratejskiej i rundy review. Ten etap formalizuje tamten ad-hoc test w stały moduł projektu i dowodzi obu kryteriów sukcesu (S1, S2) z PRD na realnych danych — dopiero to liczy się jako spełnienie kryteriów, nie sama zielona odpowiedź techniczna.

## Zakres / Definition of Done

- [x] `src/agent.py`: konfiguracja `ClaudeAgentOptions` (`tools=[]`, `mcp_servers` wskazujący na `src/mcp_server.py`, `allowed_tools` dla `get_marker_trend`/`compare_markers`, `setting_sources=[]`, `system_prompt` z `exclude_dynamic_sections=True`) — przeniesiona z ad-hoc testu w rundzie review do stałego modułu projektu, tryb jednorazowy (`query()`)
- [x] Generowanie nazwy pliku wyjściowego: slug z treści zapytania + ochrona przed nadpisaniem (licznik `-2`, `-3`... przy kolizji tego samego dnia) — zapis do `data/agent/YYYY-MM-DD-<temat>.md`
- [x] Testy jednostkowe (warstwa 1 z 3 weryfikacji z PRD): generowanie slugów, ochrona przed kolizją nazw plików, kształt konfiguracji `ClaudeAgentOptions` — `tests/test_agent.py`, 12 testów, zero wywołań sieciowych/API
- [x] Izolowana weryfikacja konfiguracji agenta (warstwa 2 z 3): potwierdzenie, że dostępne narzędzia to dokładnie te trzy z serwera V2 i że wywołanie nie blokuje się na prośbie o uprawnienia — częściowo już zrobione ad-hoc w rundzie review PRD, do powtórzenia jako formalny krok na `src/agent.py`. Powtórzone na realnym `build_options()`, dwoma kontrastowymi wywołaniami: `SystemMessage` init zwrócił dokładnie `mcp__document-intelligence-platform__{ping,get_marker_trend,compare_markers}`; `get_marker_trend("HGB")` (na liście `allowed_tools`) wykonane bez żadnej prośby o zgodę; `ping` (widoczny, ale spoza `allowed_tools`) odrzucony automatycznie przez SDK z czytelnym komunikatem, bez zawieszenia procesu — patrz Notatki
- [x] Sign-off S1: realne zapytanie o jeden marker bez wskazania narzędzia (np. „jak wygląda mój poziom ferrytyny w czasie") — agent sam wybiera narzędzie, poprawnie identyfikuje marker, zwraca sensowną odpowiedź na realnych danych. Wykonane: agent rozpoznał FERR bez podania kodu/nazwy narzędzia, poprawnie zgłosił pojedynczy pomiar (25,0 ng/ml, poniżej normy) i brak podstaw do oceny trendu — `data/agent/2026-07-31-jak-wyglada-moj-poziom-ferrytyny-w-czasi.md`
- [x] Sign-off S2: realne, otwarte zapytanie wymagające planowania wieloetapowego (np. „przygotuj mnie do wizyty u nefrologa") — agent planuje potrzebne markery, wywołuje oba narzędzia, syntetyzuje wynik w raport zapisany do `data/agent/` z realnymi danymi i pytaniami do lekarza. Wykonane: agent zaplanował i porównał eGFR, kreatyninę, mocznik, elektrolity, kwas moczowy, białko w moczu i hemoglobinę, zsyntetyzował trend (łagodne pogorszenie filtracji), nazwał braki w danych (wapń/fosfor) i przygotował 3 pytania do lekarza — `data/agent/2026-07-31-przygotuj-mnie-do-wizyty-u-nefrologa.md`

## Notatki

### Serwer MCP jako podproces agenta

**Decyzja:** `command=sys.executable` (nie literał `"python"`) w konfiguracji stdio `mcp_servers`, z `args=[str(MCP_SERVER_PATH)]` wskazującym na `src/mcp_server.py`.

**Dlaczego:** gwarantuje, że podproces serwera MCP odpala się tym samym interpreterem/venv co `agent.py` — `mcp_server.py` importuje `storage.py`, które zależy od `pyyaml`; literał `"python"` mógłby trafić w inny interpreter (systemowy, bez zależności projektu) w zależności od `$PATH` operatora.

### Namespacing narzędzi MCP w `allowed_tools`

**Decyzja:** pełna nazwa narzędzia do auto-zatwierdzenia to `mcp__<klucz z mcp_servers>__<nazwa narzędzia w FastMCP>` — potwierdzone i w dokumentacji SDK, i w realnym wywołaniu (warstwa 2): `mcp__document-intelligence-platform__get_marker_trend`.

**Jak działa:** to CLI/SDK po stronie subprocessu łączy klucz słownika `mcp_servers` z nazwą narzędzia zarejestrowanego przez `@mcp.tool()` w `FastMCP` — nie ma osobnego mapowania po stronie Pythona, więc literał klucza (`SERVER_NAME` w `agent.py`) musi być identyczny w obu miejscach (`mcp_servers` i `allowed_tools`).

**Pułapki:** rozjazd nazw (np. literówka w jednym z dwóch miejsc) nie rzuca czytelnego błędu — narzędzie po prostu nie zostanie auto-zatwierdzone, co w trybie jednorazowym objawia się jako blokada bez wyjaśnienia. Warto trzymać `SERVER_NAME` jako jedną stałą reużywaną w obu miejscach (co robi `build_options()`), zamiast wpisywać literał dwa razy.

### Warstwa 2 — realna weryfikacja configu na `src/agent.py`

**Decyzja:** weryfikacja przez dwa kontrastowe, realne wywołania `query()` na tym samym `build_options()` — jeden prompt wymuszający `get_marker_trend` (na liście `allowed_tools`), drugi wymuszający `ping` (widoczny w toolsetcie, ale spoza `allowed_tools`) — nie przez samą lekturę kodu ani przez sam test „szczęśliwej ścieżki". Bez kontrastu z narzędziem spoza listy nie dało się odróżnić „`allowed_tools` faktycznie coś ogranicza" od „zadziałałoby tak czy inaczej".

**Jak działa:** pierwsza wiadomość sesji to `SystemMessage` (`subtype == "init"`), której pole `data["tools"]` niesie pełną listę dostępnych narzędzi — potwierdza zawężenie toolsetu (dokładnie trzy: `ping`, `get_marker_trend`, `compare_markers`) niezależnie od treści właściwej odpowiedzi modelu. Dla `get_marker_trend("HGB")` model wywołał narzędzie i dostał wynik bez żadnej prośby o zgodę. Dla `ping` model spróbował wywołać narzędzie, SDK odrzuciło je automatycznie (bez pytania kogokolwiek — nie ma kogo pytać w trybie jednorazowym), a model sam, w tekście odpowiedzi, wyjaśnił operatorowi, że nie ma uprawnień i że trzeba by je zatwierdzić albo zmienić tryb uprawnień.

**Pułapki:** rzeczywiste zachowanie różni się od sformułowania w `docs/v4/00-planning.md` („blokada na uprawnieniach") — to nie jest zawieszenie procesu, tylko cicha, natychmiastowa odmowa SDK plus łagodne wyjaśnienie od modelu; `IS_ERROR` zostaje `False`. Dla `get_marker_trend`/`compare_markers` (na liście) to rozróżnienie jest bez znaczenia, bo nigdy do odmowy nie dochodzi — ale gdyby ktoś pominął `allowed_tools` w przyszłości, objawem NIE będzie zawieszony proces, tylko agent grzecznie tłumaczący, że niczego nie może zrobić (funkcjonalna porażka S1/S2, nie techniczny hang).

`ResultMessage.total_cost_usd` zwraca realną kwotę-odpowiednik zużycia (tu: ok. 0.29 USD dla wywołania `get_marker_trend`) mimo że billing idzie z puli subskrypcji Pro (`five_hour`), nie z płatnego API — to metryka „ile by kosztowało przy rozliczeniu per token", nie faktyczna opłata. Nie mylić z naruszeniem twardej zasady projektu „zero kluczy API".

### Sign-off S1/S2 na realnych danych

**Decyzja:** oba kryteria potwierdzone jednym uruchomieniem `uv run python src/agent.py "<zapytanie>"` każde, bez dodatkowych iteracji ani poprawek promptu.

**Jak działa:** S1 („jak wygląda mój poziom ferrytyny w czasie") — agent bez podania kodu markera ani nazwy narzędzia sam rozpoznał FERR, wywołał `get_marker_trend`, poprawnie zgłosił, że jeden pomiar to za mało na trend, i zauważył wynik poniżej normy referencyjnej. S2 („przygotuj mnie do wizyty u nefrologa") — agent zaplanował zestaw markerów istotnych nefrologicznie (eGFR, kreatynina, mocznik, elektrolity, kwas moczowy, białko w moczu, hemoglobina), wywołał `compare_markers`, zsyntetyzował trend (łagodne pogorszenie filtracji w czasie), nazwał braki w danych (wapń/fosfor, istotne przy CKD-MBD) i przygotował konkretne pytania do lekarza — dokładnie kształt wyniku wymagany przez S2, nie tylko surowe dane z narzędzia.

**Pułapki:** żadna — obie odpowiedzi cytowały wyłącznie wartości faktycznie zwrócone przez narzędzia (widoczne w przechwyconym JSON-ie z warstwy 2 i w treści zapisanych raportów), bez halucynowanych liczb. Ryzyko z PRD („agent syntetyzuje wynik zawierający liczby nieoparte na realnych danych") nie zmaterializowało się w tych dwóch przebiegach, ale to dowód na próbce n=2, nie gwarancja na przyszłość.

### Ręczne odtworzenie S1/S2 przez operatora

**Decyzja:** oprócz automatycznej weryfikacji (wykonanej w tej sesji), operator uruchamia oba sign-offy sam w terminalu — human-in-the-loop nie kończy się na przeczytaniu wyniku w czacie, obejmuje też samodzielne odtworzenie.

**Jak działa:** terminal na macOS startuje w `$HOME`, nie w katalogu repo — najpierw `cd` do projektu, potem komenda:

```
cd /Users/p/Documents/dev/Document-Intelligence-Platform
uv run python src/agent.py "jak wygląda mój poziom ferrytyny w czasie"
uv run python src/agent.py "przygotuj mnie do wizyty u nefrologa"
```

Każde wywołanie tworzy nowy plik `data/agent/YYYY-MM-DD-<slug-z-zapytania>.md` i wypisuje w terminalu jego ścieżkę (`Zapisano: ...`) — wystarczy otworzyć wskazany plik. Ponowne uruchomienie tego samego dnia z tym samym zapytaniem nie nadpisuje poprzedniego wyniku, tylko dopisuje `-2`, `-3`... do nazwy (ochrona przed nadpisaniem, DoD punkt 2), więc stare i nowe uruchomienie można porównać obok siebie. Można też podać inne zapytanie niż te dwa przykłady z PRD — dowolny marker albo innego specjalistę — `build_options()` nie ogranicza treści promptu, tylko dostępne narzędzia.

**Pułapki:** każde uruchomienie to realne wywołanie `query()` z Claude Agent SDK — zużywa pulę pięciogodzinną subskrypcji Pro (współdzieloną ze zwykłymi sesjami Claude Code) i zajmuje realny czas (dla S2 rząd kilkunastu-kilkudziesięciu sekund, bo agent planuje i woła narzędzie kilka razy) — to nie jest darmowa, natychmiastowa operacja jak `pytest`.
