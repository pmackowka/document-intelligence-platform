# Etap 4 — Backfill i weryfikacja Success Criteria

## Cel
Przetworzenie dokumentów strukturalnych z archiwum ~390 plików (szacunkowo ~30%, czyli ok. 115–120 — reszta to narracyjne, poza zakresem V1) i pomiar S1–S4 z PRD. Rozłożone w czasie — tempo ograniczone limitami abonamentu Pro (~3 dok./dzień wystarcza).

## Zakres / Definition of Done
- [ ] Partia wsadowa: kolejkowanie, wznawianie po przerwaniu, licznik dokumentów odrzuconych (nieczytelny OCR)
- [ ] S1: ≥95% dokumentów strukturalnych w kanonicznym JSON, 100% markerów zmapowanych lub świadomie odrzuconych
- [ ] S3: nowy dokument przechodzi pipeline end-to-end w ≤15 min pracy operatora — pomiar na realnym pliku (upload do `data/raw/structural/` → `uv run python src/structural_pipeline.py` → zatwierdzenie ew. aliasów w `pending/` → zapis NDJSON). Bez orkiestratora — uruchomienie z terminala (n8n usunięty z V1, patrz PRD)
- [ ] Pomiar i zapis wyników S1–S4 w tym pliku
- [ ] Retrospektywa: co poprawić przy bieżącym napływie nowych dokumentów (2–3/mies.)

## Wyniki S1–S4
<!-- uzupełniane po backfillu -->

## Notatki
<!-- Grupuj po temacie, nie po dacie (chronologię trzyma git). Każdy podpunkt
     w OSOBNYM akapicie (pusta linia między nimi). Dla każdego tematu:

### <Temat / czego dotyczy>

**Decyzja:** co ustalono.

**Dlaczego:** uzasadnienie, trade-offy.

**Jak działa:** mechanizm narzędzia pod spodem — sedno nauki.

**Pułapki:** co zaskoczyło, na co uważać.

Nie każdy temat wymaga wszystkich czterech podpunktów. To notatki do nauki, nie log czynności. -->

