# Etap 3 — Pipeline strukturalny (standaryzacja)

## Cel
Szybka wygrana z PRD: badania krwi/moczu do kanonicznego JSON. Trzy warstwy standaryzacji + plikowy human-in-the-loop.

## Zakres / Definition of Done
- [x] Warstwa 1: dictionary mapping (`config/aliases.yml`, **panel-aware** — „Leukocyty" = WBC w morfologii vs leukocyty w moczu) → kanoniczna nazwa markera; `src/structural_pipeline.py`
- [x] Warstwa 2: regex — ekstrakcja wartości liczbowej (`13.2`, `0,18`, `<1`) + jakościowej (`nieobecna`/`przejrzysty`); wartość i zakres chronione przed cyframi z dat
- [x] Normalizacja jednostek (`config/units.yml`, w tym błędy OCR + encja `&#124;`) + zakresy MIN/MAX z dokumentu → `reference_low`/`reference_high`
- [x] Warstwa 3: `claude -p --model haiku` proponuje aliasy dla nieznanych → `data/pending/aliases.yml` (11 propozycji na realnym zbiorze 14 dok.); **TODO: sanityzacja wyjścia — Haiku bywa zwraca zdania/odmowy zamiast kodu**
- [ ] Flow zatwierdzania: pipeline czyta wyłącznie zatwierdzone wpisy; edycja pending w Claude Code
- [ ] Przetworzone end-to-end ≥10 realnych dokumentów strukturalnych

## Notatki
<!-- Grupuj po temacie, nie po dacie (chronologię trzyma git). Każdy podpunkt
     w OSOBNYM akapicie (pusta linia między nimi). Dla każdego tematu:

### <Temat / czego dotyczy>

**Decyzja:** co ustalono.

**Dlaczego:** uzasadnienie, trade-offy.

**Jak działa:** mechanizm narzędzia pod spodem — sedno nauki.

**Pułapki:** co zaskoczyło, na co uważać.

Nie każdy temat wymaga wszystkich czterech podpunktów. To notatki do nauki, nie log czynności. -->

