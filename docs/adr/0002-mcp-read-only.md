# MCP server V2: wyłącznie odczyt

Serwer MCP w V2 wystawia wyłącznie narzędzia do odczytu (`get_marker_trend`, `compare_markers`), czytające `data/store/structural-backfill.ndjson`. Rozważono i odrzucono wariant z akcją zapisu — np. zatwierdzanie propozycji aliasu z poziomu Claude Desktop, zamiast ręcznej edycji `pending/*.yml` w Claude Code.

**Dlaczego:** mechanika zatwierdzania aliasów (plikowa, human-in-the-loop) jest ustalona i działająca od V1 — nie ma powodu jej duplikować w nowym kanale. Zapis przez MCP zwiększa powierzchnię ryzyka (klient MCP mógłby zmieniać zaufany słownik domenowy) bez odpowiadającej mu, potwierdzonej potrzeby produktowej — luka, którą V2 realnie adresuje, to brak dostępu do *odczytu* danych z klientów bez własnego dostępu do plików (Claude Desktop), nie brak alternatywnej ścieżki zapisu.
