# Etap 2 — Walidacja ekstrakcji narracyjnej (spike)

## Cel
Sprawdzić na 5–10 opisach (USG, MRI, kolonoskopia), czy ekstrakcja ustaleń przez LLM daje użyteczne wyniki — **zanim** zbudujemy wokół niej moduł. To warunek z PRD: 70% danych zależy od tego mechanizmu.

## Zakres / Definition of Done
- [ ] 5–10 opisów zanonimizowanych **ręcznie** (Presidio jeszcze nie istnieje — PII nie wychodzi bez anonimizacji, reguła twarda z PRD)
- [ ] Prompt ekstrakcyjny do schematu: `finding`, `location`, `measurement_value`, `measurement_unit`, `status`, `exam_type`, `exam_date`
- [ ] Wywołanie przez `claude -p`, ocena ręczna: co model pominął, co nadinterpretował
- [ ] Decyzja go/no-go dla schematu; ewentualne poprawki schematu → aktualizacja PRD
- [ ] Zachowana lista ręcznie podmienionych encji per dokument (co i gdzie zamieniono) — to złoty zbiór testowy do pomiaru recall Presidio w etapie 4

## Instrukcja ręcznej anonimizacji
Ręcznie, bo Presidio jeszcze nie istnieje, a reguła twarda z PRD obejmuje też sesję Claude Code (to też API Anthropic). PII w polskich opisach siedzi w nagłówku/stopce: pacjent (nazwisko → `PERSON_001`, PESEL → `PESEL_001`, data urodzenia → `DOB_001`, adres → `ADDRESS_001`), lekarz + PWZ → `DOCTOR_001`, placówka/nr badania → `FACILITY_001`/`EXAM_ID_001`. **Zostaje**: data badania (oś czasu) i cała treść medyczna. ~3–5 min/dokument.

## Notatki
<!-- Grupuj po temacie, nie po dacie (chronologię trzyma git). Dla każdego tematu:

### <Temat / czego dotyczy>
**Decyzja:** co ustalono.
**Dlaczego:** uzasadnienie, trade-offy.
**Jak działa:** mechanizm narzędzia pod spodem — sedno nauki.
**Pułapki:** co zaskoczyło, na co uważać.

Nie każdy temat wymaga wszystkich czterech podpunktów. To notatki do nauki, nie log czynności. -->

