# Etap 5 — Pipeline narracyjny (ekstrakcja ustaleń)

## Cel
Pełny moduł dla 70% wolumenu: OCR → Presidio → ekstrakcja LLM → zatwierdzanie → zapis. Bazuje na schemacie zwalidowanym w etapie 2.

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

