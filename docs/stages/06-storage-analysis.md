# Etap 6 — Magazyn NDJSON i analiza trendów

## Cel
Warstwa, dla której to wszystko powstało: trwały magazyn z osią czasu i odpytywanie trendów przez Claude Code (S2) + zgodność z BigQuery (S4).

## Zakres / Definition of Done
- [ ] Kanoniczny NDJSON: płaskie rekordy append-only, schemat pipeline'u strukturalnego
- [ ] Trend dowolnego markera jednym promptem w Claude Code (test S2: marker z ≥3 pomiarami)
- [ ] Porównanie dwóch markerów na osi czasu (np. Fe vs CRP)
- [ ] Ręczny load NDJSON do BigQuery bez błędów schematu (test S4)
- [ ] Raport Markdown „do lekarza": trendy markerów

## Notatki
<!-- Grupuj po temacie, nie po dacie (chronologię trzyma git). Każdy podpunkt
     w OSOBNYM akapicie (pusta linia między nimi). Dla każdego tematu:

### <Temat / czego dotyczy>

**Decyzja:** co ustalono.

**Dlaczego:** uzasadnienie, trade-offy.

**Jak działa:** mechanizm narzędzia pod spodem — sedno nauki.

**Pułapki:** co zaskoczyło, na co uważać.

Nie każdy temat wymaga wszystkich czterech podpunktów. To notatki do nauki, nie log czynności. -->

