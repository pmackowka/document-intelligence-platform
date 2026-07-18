# Etap 4 — Anonimizacja (Presidio)

## Cel
Warstwa pseudonimizacji przed jakimkolwiek wysłaniem tekstu dokumentu do API. Cel edukacyjny: Privacy Engineering.

## Zakres / Definition of Done
- [ ] Presidio z polskim NLP engine (spaCy `pl_core_news_lg`)
- [ ] Encje: nazwiska, adresy, telefony, PESEL (`PlPeselRecognizer` — wbudowany, walidacja sumy kontrolnej), e-mail
- [ ] Pseudonimizacja spójna (Jan Kowalski → PERSON_001, konsekwentnie w dokumencie)
- [ ] Test jakości na próbce realnych dokumentów — szczególnie adresy (zidentyfikowane ryzyko z PRD)
- [ ] Pomiar recall na złotym zbiorze z etapu 2 (ręcznie zanonimizowana próbka = ground truth: porównaj wykrycia Presidio z listą ręcznych podmian)
- [ ] Jeśli adresy/nazwiska wykrywane słabo → custom recognizer lub deny-lista

## Notatki
<!-- Grupuj po temacie, nie po dacie (chronologię trzyma git). Dla każdego tematu:

### <Temat / czego dotyczy>
**Decyzja:** co ustalono.
**Dlaczego:** uzasadnienie, trade-offy.
**Jak działa:** mechanizm narzędzia pod spodem — sedno nauki.
**Pułapki:** co zaskoczyło, na co uważać.

Nie każdy temat wymaga wszystkich czterech podpunktów. To notatki do nauki, nie log czynności. -->

