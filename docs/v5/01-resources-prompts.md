# Etap 1 (V5) — Resources i Prompts nad serwerem MCP z V2

## Cel

Dołożyć do `src/mcp_server.py` dwa dotąd nieużyte prymitywy protokołu MCP — Resources i Prompts —
obok istniejących trzech Tools z V2. Zakres i uzasadnienie: `docs/v5/prd.md` (status „zatwierdzony").
To nadobowiązkowy krok nauki mechaniki protokołu na już działającym serwerze, nie nowa potrzeba
produktowa — dowód gotowości to MCP Inspector, nie realny klient docelowy (Desktop), świadomie węższy
rygor niż V2/V4.

## Zakres / Definition of Done

- [x] Resource `markers://catalog` w `mcp_server.py` — zwraca listę kodów i polskich etykiet z
  `marker_labels.yml`, reużywając `load_labels()` z `storage.py`
- [x] Resource `report://latest` w `mcp_server.py` — zwraca treść najnowszego pliku z `data/reports/`;
  jawny komunikat zamiast wyjątku/cichej pustki, gdy folder jest pusty
- [x] Prompt `porownaj_markery(marker1, marker2)` w `mcp_server.py` — zwraca sformatowany tekst
  „Porównaj moje wyniki {marker1} i {marker2} w czasie.", bez odczytu magazynu
- [x] Funkcja znajdująca najnowszy plik w `data/reports/` — `latest_report()` w `storage.py`, obok
  przeniesionej tam stałej `REPORTS` (wcześniej lokalnej w `report.py`)
- [x] Testy jednostkowe (warstwa 1 z 2 weryfikacji z PRD): najnowszy plik spośród kilku, pusty/nieistniejący
  folder (`test_storage.py`), kształt trzech nowych elementów serwera + specjalne znaki w identyfikatorze
  (`test_mcp_server.py`) — 8 nowych testów, 38/38 w całym pakiecie
- [x] Weryfikacja przez MCP Inspector (warstwa 2 z 2) — realne wywołanie wszystkich trzech nowych
  elementów przez automatyzację przeglądarki: `markers://catalog` i `report://latest` odczytane
  (RESOURCES/READ → OK), `porownaj_markery("Hemoglobina", "OB")` wykonany (PROMPTS/GET → OK), tekst
  zwrócony dokładnie zgodny z S2

## Notatki

### Centralizacja `REPORTS` w `storage.py`

**Decyzja:** stała `REPORTS` (`data/reports/`) przeniesiona z `report.py` do `storage.py`, obok `STORE`/`LABELS`; `report.py` teraz ją importuje zamiast definiować lokalnie.

**Dlaczego:** `mcp_server.py` (PRD V2, Tech Constraints, „Reużycie kodu") nie może importować ze skryptu CLI (`report.py`) — więc funkcja `latest_report()`, potrzebna przez `report://latest`, musiała żyć w `storage.py`. Skoro tam już musi być ścieżka do katalogu raportów, naturalne było przenieść tam też samą stałą, zamiast trzymać jej definicję w dwóch miejscach.

**Jak działa:** ten sam wzorzec co `STORE`/`LABELS` — stała ścieżki w `storage.py`, konsument (tu: `report.py` i `mcp_server.py`) tylko importuje, zero duplikacji `ROOT / "data" / "reports"`.

### `report://latest` i `Tryb` w treści raportu

**Decyzja:** `report://latest` nie ma własnej logiki wykrywania trybu (zaufany magazyn/KANDYDAT) — dziedziczy to bezpośrednio z treści pliku, dzięki wcześniejszej poprawce `report.py` (`Tryb: {...}` w nagłówku).

**Pułapki:** zweryfikowane w Inspectorze na realnym, istniejącym pliku (`2026-07-23-trendy.md`) — ten konkretny plik powstał PRZED poprawką `Tryb:`, więc zwrócona treść nie miała tej linii. Nie błąd nowego kodu — po prostu stary plik w starym formacie. Nowe raporty (wygenerowane po poprawce) będą już mieć `Tryb:` w treści; `report://latest` samo się o to nie martwi, bo tylko czyta, co znajdzie na dysku.

### Weryfikacja przez Inspector — automatyzacja przeglądarki zamiast ręcznych kliknięć

**Decyzja:** warstwa 2 wykonana przez `mcp dev` na osobnym porcie (`CLIENT_PORT=6280 SERVER_PORT=6281`, żeby nie kolidować z inną, już działającą instancją Inspectora na porcie 6274 z innej sesji terminala) + sterowanie przeglądarką (kliknięcia, wpisywanie, zrzuty ekranu) zamiast poproszenia operatora o ręczne kliknięcie.

**Dlaczego:** PRD wymaga „realnego wywołania", nie tylko przeglądu list — automatyzacja przeglądarki dawała to samo co ręczne kliknięcie operatora, bez angażowania go do mechanicznego kroku.

**Pułapki:** domyślny port Inspectora (6274) był już zajęty przez proces z innej, niezależnej sesji terminala (działający od rana) — nie zabity, tylko ominięty własnymi portami; ważne, żeby nie zakładać, że port jest wolny, i nie ubijać cudzych procesów bez sprawdzenia, do czego należą.

### Ręczne odtworzenie warstwy 2 przez operatora

**Decyzja:** oprócz automatycznej weryfikacji (wykonanej w tej sesji przez sterowanie przeglądarką), operator powtarza to samo ręcznie w Inspectorze — najpierw Resources, potem Prompt.

**Jak działa:**

1. Z katalogu głównego repo: `cd /Users/p/Documents/dev/Document-Intelligence-Platform`
2. `uv run mcp dev src/mcp_server.py` — poczekać na linię `MCP Inspector Web is up and running at: http://localhost:6274?MCP_INSPECTOR_API_TOKEN=...` (jeśli port 6274 zajęty przez inną, wcześniej odpaloną instancję — zamknąć ją albo odpalić na innym porcie: `CLIENT_PORT=6280 SERVER_PORT=6281 uv run mcp dev src/mcp_server.py`)
3. Otworzyć wypisany URL w przeglądarce (Inspector zwykle otwiera się sam)
4. Na karcie serwera „uv" kliknąć przełącznik przy „Disconnected", żeby połączyć — zmieni się na zielone „Connected"
5. Kliknąć zakładkę **Resources** w górnym menu
6. Na liście „URIs (2)" kliknąć `markers_catalog` — w panelu podglądu powinna pojawić się lista kodów i polskich etykiet (np. `HGB: Hemoglobina`)
7. Kliknąć `report_latest` — w panelu podglądu powinna pojawić się treść najnowszego pliku z `data/reports/` (nagłówek z `Wygenerowano:` i, dla raportów wygenerowanych po poprawce `report.py`, linią `Tryb:`); jeśli `data/reports/` jest pusty, zamiast treści pojawi się komunikat „Brak wygenerowanych raportów..."
8. Kliknąć zakładkę **Prompts** w górnym menu
9. Kliknąć `porownaj_markery` z listy po lewej
10. Wypełnić pole `marker1` (np. `Hemoglobina`) i `marker2` (np. `OB`)
11. Kliknąć **Get Prompt**
12. Sprawdzić, że w panelu „Messages" pojawił się dokładnie tekst: „Porównaj moje wyniki Hemoglobina i OB w czasie." (z kropką na końcu)

**Pułapki:** krok 2 zawiesza terminal na czas działania Inspectora (proces pierwszoplanowy) — żeby korzystać z terminala w międzyczasie, otworzyć drugą kartę/okno terminala albo dopisać `&` na końcu komendy.

### Weryfikacja w Claude Desktop — potwierdzona przez operatora (poza wymogiem PRD)

**Decyzja:** operator potwierdził działanie wszystkich trzech elementów w Claude Desktop po restarcie appki — poza wymogiem tego PRD (Inspector wystarczał jako dowód), ale wartościowe, bo pokazuje realny klient docelowy, nie tylko narzędzie deweloperskie.

**Jak działa:** Resources i Prompts NIE pojawiają się tam, gdzie Tools (toggle „document-intelligence-platform" + lista „Tool access") — mają własną pozycję w menu „+": „Add from document-intelligence-platform", obok „Add from Google Drive". W środku widoczne trzy pozycje z ikonami różnymi dla typu: dymek dla Prompta (`Porownaj markery`), dokument dla Resource (`Markers catalog`, `Report latest`). To bezpośrednie odzwierciedlenie różnicy w protokole: Tools wywołuje model sam w trakcie rozmowy (stąd toggle/uprawnienia), Resources i Prompts świadomie dołącza operator przed wysłaniem wiadomości (stąd osobny mechanizm „dodaj do wiadomości", nie przełącznik dostępności).

**Pułapki:** nazwy wyświetlane w Desktopie są zhumanizowane automatycznie z nazw funkcji Pythona (`markers_catalog` → „Markers catalog", `porownaj_markery` → „Porownaj markery") — nigdzie w kodzie nie ustawialiśmy `name`/`title` jawnie; to domyślne zachowanie FastMCP/Desktopa, nie coś, co trzeba było skonfigurować.
