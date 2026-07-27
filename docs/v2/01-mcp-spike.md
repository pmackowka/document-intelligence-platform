# Etap 1 (V2) — MCP spike

## Cel

Zweryfikować, że minimalny serwer MCP (Python SDK, transport stdio) faktycznie działa end-to-end — zanim zbudujemy właściwą logikę narzędzi (`get_marker_trend`, `compare_markers`) i wydzielimy `src/storage.py`. To spike — kod może być brzydki (jedno trywialne narzędzie testowe, nie docelowa logika), wnioski mają być twarde.

Analogicznie do `docs/v1/01-ocr-spike.md`, który dowiódł, że wybrany silnik OCR działa na realnych dokumentach, zanim zbudowano cały pipeline: tu ryzykiem nie jest logika domenowa (dobrze znana, gotowa z V1), tylko sam mechanizm MCP — czy transport stdio, Python SDK i realny klient (Claude Desktop) faktycznie się ze sobą dogadują na tej maszynie. Budowanie `get_marker_trend` na niesprawdzonym fundamencie odwróciłoby kolejność ryzyka.

## Zakres / Definition of Done

- [x] Minimalny serwer MCP w Pythonie (oficjalny SDK, FastMCP) z jednym trywialnym narzędziem testowym — `src/mcp_server.py`, narzędzie `ping` → `"pong"`; import i rejestracja narzędzia zweryfikowane lokalnie. Dowód działania transportu stdio z realnym klientem — kolejny krok (Inspector)
- [ ] Uruchomienie i ręczne wywołanie przez MCP Inspector (`mcp dev` z Python SDK, lub `npx @modelcontextprotocol/inspector`) — potwierdzona poprawna odpowiedź bez konfigurowania Desktopa
- [ ] Podpięcie do Claude Desktop (konfiguracja klienta po stronie operatora) — realne zapytanie end-to-end z Desktopa do trywialnego narzędzia
- [ ] Decyzja: lokalizacja i nazwa pliku serwera w `src/` (np. `src/mcp_server.py`), spójna z resztą stacku
- [ ] Sign-off operatora: serwer połączony i odpowiada z realnego Claude Desktop, bez ręcznego obejścia

## Notatki

### Wersja SDK — stabilna v1, nie beta v2

**Decyzja:** `uv add "mcp[cli]"` bez przypięcia wersji — rozwiązało się do `mcp==1.28.1`.

**Dlaczego:** oficjalne repo SDK ma równolegle linię v2 w becie (przygotowywaną pod specyfikację MCP z 2026-07-28), z jawnym ostrzeżeniem „nie używać produkcyjnie". Instalacja bez jawnego żądania pre-release nie łapie bety — potwierdzone realnym `uv add`, nie tylko dokumentacją.

**Pułapki:** przy kolejnych `uv add`/`uv sync` w tym projekcie pilnować, żeby nikt (w tym przyszła sesja) nie przypiął przypadkiem `mcp==2.x` z jakiegoś tutoriala pisanego pod nową wersję — API między liniami się różni.
