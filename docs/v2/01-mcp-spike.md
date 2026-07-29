# Etap 1 (V2) — MCP spike

## Cel

Zweryfikować, że minimalny serwer MCP (Python SDK, transport stdio) faktycznie działa end-to-end — zanim zbudujemy właściwą logikę narzędzi (`get_marker_trend`, `compare_markers`) i wydzielimy `src/storage.py`. To spike — kod może być brzydki (jedno trywialne narzędzie testowe, nie docelowa logika), wnioski mają być twarde.

Analogicznie do `docs/v1/01-ocr-spike.md`, który dowiódł, że wybrany silnik OCR działa na realnych dokumentach, zanim zbudowano cały pipeline: tu ryzykiem nie jest logika domenowa (dobrze znana, gotowa z V1), tylko sam mechanizm MCP — czy transport stdio, Python SDK i realny klient (Claude Desktop) faktycznie się ze sobą dogadują na tej maszynie. Budowanie `get_marker_trend` na niesprawdzonym fundamencie odwróciłoby kolejność ryzyka.

## Zakres / Definition of Done

- [x] Minimalny serwer MCP w Pythonie (oficjalny SDK, FastMCP) z jednym trywialnym narzędziem testowym — `src/mcp_server.py`, narzędzie `ping` → `"pong"`; import i rejestracja narzędzia zweryfikowane lokalnie. Dowód działania transportu stdio z realnym klientem — kolejny krok (Inspector)
- [x] Uruchomienie i ręczne wywołanie przez MCP Inspector (`uv run mcp dev src/mcp_server.py`) — połączenie STDIO nawiązane (`Connected`, MCP 2025-11-25), narzędzie `ping` wywołane ręcznie z UI, odpowiedź `pong` potwierdzona w panelu Results
- [ ] Podpięcie do Claude Desktop (konfiguracja klienta po stronie operatora) — realne zapytanie end-to-end z Desktopa do trywialnego narzędzia
- [ ] Decyzja: lokalizacja i nazwa pliku serwera w `src/` (np. `src/mcp_server.py`), spójna z resztą stacku
- [ ] Sign-off operatora: serwer połączony i odpowiada z realnego Claude Desktop, bez ręcznego obejścia

## Notatki

### Wersja SDK — stabilna v1, nie beta v2

**Decyzja:** `uv add "mcp[cli]"` bez przypięcia wersji — rozwiązało się do `mcp==1.28.1`.

**Dlaczego:** oficjalne repo SDK ma równolegle linię v2 w becie (przygotowywaną pod specyfikację MCP z 2026-07-28), z jawnym ostrzeżeniem „nie używać produkcyjnie". Instalacja bez jawnego żądania pre-release nie łapie bety — potwierdzone realnym `uv add`, nie tylko dokumentacją.

**Pułapki:** przy kolejnych `uv add`/`uv sync` w tym projekcie pilnować, żeby nikt (w tym przyszła sesja) nie przypiął przypadkiem `mcp==2.x` z jakiegoś tutoriala pisanego pod nową wersję — API między liniami się różni.

### MCP Inspector — jak zweryfikować serwer bez klienta docelowego

**Decyzja:** weryfikacja przez `uv run mcp dev src/mcp_server.py` (komenda z `mcp[cli]`), nie ręczna instalacja `npx @modelcontextprotocol/inspector`.

**Jak działa:** `mcp dev` sam odpala Inspector przez `npx` (przy pierwszym uruchomieniu pobiera pakiet `@modelcontextprotocol/inspector` — kilka sekund), stawia lokalny serwer webowy (domyślnie `localhost:6274`) i proxy do serwera MCP uruchomionego w podprocesie po STDIO. Panel Protocol po prawej pokazuje surowe requesty JSON-RPC (`tools/list`, `tools/call`) — dobry sposób, żeby zobaczyć realny handshake, nie tylko wynik.

Kroki do powtórzenia testu ręcznie:

1. `cd /Users/p/Documents/dev/Document-Intelligence-Platform`
2. `uv run mcp dev src/mcp_server.py` — poczekać na linię `MCP Inspector Web is up and running at: http://localhost:6274?MCP_INSPECTOR_API_TOKEN=...`
3. Otworzyć w przeglądarce dokładnie ten URL (token w query string wymagany, bez niego brak połączenia z sesją) — zwykle otwiera się sam
4. Karta serwera „uv" → kliknąć toggle obok „Disconnected", aż zmieni się na „Connected"
5. Zakładka „Tools" (górne menu) → kliknąć `ping` z listy
6. Kliknąć „Execute Tool" (bez parametrów) → wynik `pong` w panelu Results
7. `Ctrl+C` w terminalu zamyka Inspector i serwer

**Pułapki:** Inspector to osobny proces webowy, nie kończy się sam — trzeba go świadomie zatrzymać (tu: zabity po weryfikacji), inaczej zostaje w tle i trzyma port.
