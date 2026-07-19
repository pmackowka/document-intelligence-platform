# Etap 5 — Pipeline narracyjny (ekstrakcja ustaleń)

## Cel
Pełny moduł dla ~70% wolumenu (opisy USG/MRI/TK/kolonoskopii). Wejściem jest OCR-owany, zanonimizowany markdown opisu (etap 1 + 4), wyjściem płaskie rekordy — jedno ustalenie = jeden rekord w schemacie zwalidowanym w etapie 2 (v1.2): `finding`, `location`, `measurements` (lista `{value, unit, label}` — obsługuje pomiary wielowymiarowe, np. 22×23×37 mm + objętość), `status` (`prawidłowy`/`nieprawidłowy`/`nieobecny`), `exam_type`, `exam_date`. To strukturyzacja prozy, nie wnioskowanie medyczne — model wiernie przekłada opis na wiersze, odpytywalne SQL-em pod trendy (kamień 6 mm w 2023 → 8 mm w 2025).

Potok: OCR (etap 1) → anonimizacja Presidio (etap 4, twarda zależność — nic nie idzie do API przed nią) → ekstrakcja przez `claude -p` na tekście po Presidio → propozycje ustaleń do `pending/findings/*.yml` → operator zatwierdza → zapis NDJSON. Human-in-the-loop obowiązkowy: pipeline zapisuje wyłącznie zatwierdzone ustalenia, tak jak strukturalny (etap 3) zapisuje wyłącznie zatwierdzone aliasy. Anonimizowany Markdown opisu ląduje obok rekordów jako kontekst do przyszłych analiz. Negacje i normy („bez zmian", „prawidłowy") to świadomie **brak** rekordu, nie ustalenie — walidacja etapu 2 potwierdziła, że model to obsługuje bez potknięć.

## Zakres / Definition of Done
- [ ] Ekstrakcja przez `claude -p` na tekście **po Presidio** (etap 4 jest zależnością)
- [ ] Propozycje ustaleń do `pending/findings/*.yml`; operator zatwierdza przed zapisem
- [ ] Anonimizowany Markdown opisu zapisywany obok rekordów (kontekst do przyszłych analiz)
- [ ] Przetworzone end-to-end ≥10 realnych dokumentów narracyjnych różnych typów (USG, MRI, TK)

## Notatki
<!-- Grupuj po temacie, nie po dacie (chronologię trzyma git). Każdy podpunkt
     w OSOBNYM akapicie (pusta linia między nimi). Dla każdego tematu:

### <Temat / czego dotyczy>

**Decyzja:** co ustalono.

**Dlaczego:** uzasadnienie, trade-offy.

**Jak działa:** mechanizm narzędzia pod spodem — sedno nauki.

**Pułapki:** co zaskoczyło, na co uważać.

Nie każdy temat wymaga wszystkich czterech podpunktów. To notatki do nauki, nie log czynności. -->

