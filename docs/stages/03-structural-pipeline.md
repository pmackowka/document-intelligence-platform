# Etap 3 — Pipeline strukturalny (standaryzacja)

## Cel
Szybka wygrana z PRD: badania krwi/moczu do kanonicznego JSON. Trzy warstwy standaryzacji + plikowy human-in-the-loop.

## Zakres / Definition of Done
- [ ] Warstwa 1: dictionary mapping (`config/aliases.yml`) → kanoniczna nazwa markera
- [ ] Warstwa 2: regex — ekstrakcja wartości liczbowej (formaty: `13.2`, `0,18`, `CRP........0,18`)
- [ ] Normalizacja jednostek (`config/units.yml`) i zakresów referencyjnych → `reference_low`/`reference_high`
- [ ] Warstwa 3: weryfikacja nieznanych nazw przez `claude -p --model haiku` → propozycja do `pending/aliases.yml`
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

