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

## Decyzje i dlaczego
<!-- uzupełniane w trakcie pracy -->

## Jak to działa (mechanizmy narzędzi)
<!-- uzupełniane w trakcie pracy -->

## Gotchas / lekcje
<!-- uzupełniane w trakcie pracy -->
