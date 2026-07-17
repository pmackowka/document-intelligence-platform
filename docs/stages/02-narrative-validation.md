# Etap 2 — Walidacja ekstrakcji narracyjnej (spike)

## Cel
Sprawdzić na 5–10 opisach (USG, MRI, kolonoskopia), czy ekstrakcja ustaleń przez LLM daje użyteczne wyniki — **zanim** zbudujemy wokół niej moduł. To warunek z PRD: 70% danych zależy od tego mechanizmu.

## Zakres / Definition of Done
- [ ] 5–10 opisów zanonimizowanych **ręcznie** (Presidio jeszcze nie istnieje — PII nie wychodzi bez anonimizacji, reguła twarda z PRD)
- [ ] Prompt ekstrakcyjny do schematu: `finding`, `location`, `measurement_value`, `measurement_unit`, `status`, `exam_type`, `exam_date`
- [ ] Wywołanie przez `claude -p`, ocena ręczna: co model pominął, co nadinterpretował
- [ ] Decyzja go/no-go dla schematu; ewentualne poprawki schematu → aktualizacja PRD

## Decyzje i dlaczego
<!-- uzupełniane w trakcie pracy -->

## Jak to działa (mechanizmy narzędzi)
<!-- uzupełniane w trakcie pracy -->

## Gotchas / lekcje
<!-- uzupełniane w trakcie pracy -->
