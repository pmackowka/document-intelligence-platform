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

## Decyzje i dlaczego
<!-- uzupełniane w trakcie pracy -->

## Jak to działa (mechanizmy narzędzi)
<!-- uzupełniane w trakcie pracy -->

## Gotchas / lekcje
<!-- uzupełniane w trakcie pracy -->
