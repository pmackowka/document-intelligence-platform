# Etap 4 — Orkiestracja n8n

## Cel
Spięcie modułów w workflow: nowy dokument → pipeline → zapis → powiadomienie. n8n wyłącznie orkiestruje — zero logiki biznesowej (reguła z PRD).

## Zakres / Definition of Done
- [ ] Trigger ręczny (upload) — jedyna ścieżka ingestu (PRD v1.1)
- [ ] ~~Konektor folderu Google Drive — ścieżka automatyczna~~ — skreślone (PRD v1.1: ingest wyłącznie ręczny, bez konektora Drive)
- [ ] Wywołanie modułu Python (pipeline strukturalny) przez Execute Command — pojedyncza ścieżka, bez routingu/klasyfikacji (zbędne po zawężeniu V1 do jednej klasy dokumentów, PRD v1.3)
- [ ] Powiadomienie o dokumentach czekających na zatwierdzenie w `pending/`
- [ ] Nowy dokument przechodzi end-to-end w ≤15 min pracy operatora (test S3)

## Notatki
<!-- Grupuj po temacie, nie po dacie (chronologię trzyma git). Każdy podpunkt
     w OSOBNYM akapicie (pusta linia między nimi). Dla każdego tematu:

### <Temat / czego dotyczy>

**Decyzja:** co ustalono.

**Dlaczego:** uzasadnienie, trade-offy.

**Jak działa:** mechanizm narzędzia pod spodem — sedno nauki.

**Pułapki:** co zaskoczyło, na co uważać.

Nie każdy temat wymaga wszystkich czterech podpunktów. To notatki do nauki, nie log czynności. -->

