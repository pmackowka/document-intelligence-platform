# Etap 2 — Walidacja ekstrakcji narracyjnej (spike)

## Cel
Sprawdzić na 5–10 opisach (USG, MRI, kolonoskopia), czy ekstrakcja ustaleń przez LLM daje użyteczne wyniki — **zanim** zbudujemy wokół niej moduł. To warunek z PRD: 70% danych zależy od tego mechanizmu.

Sedno: to **strukturyzacja prozy**, nie wnioskowanie medyczne. Model ma wiernie przełożyć opis na rekordy w schemacie, nie interpretować. „Użyteczny wynik" = rekord wierny, kompletny i dobrze umiejscowiony (wartość w polu wartości, jednostka w polu jednostki).

Wejście (proza z opisu USG):
> „W nerce prawej, w dolnym biegunie, widoczny złóg o wymiarach 6 mm. W nerce lewej torbiel prosta 12 mm. Wątroba, trzustka, śledziona — bez zmian."

Wyjście (rekordy w schemacie):

| finding | location | value | unit | status | exam_type |
|---|---|---|---|---|---|
| złóg (kamień) | nerka prawa, dolny biegun | 6 | mm | obecny | USG j. brzusznej |
| torbiel prosta | nerka lewa | 12 | mm | obecny | USG j. brzusznej |

Trzy zdania → dwa płaskie rekordy, odpytywalne SQL-em (dopiero to umożliwia trend: kamień 6 mm w 2023 → 8 mm w 2025). „Bez zmian" → świadomie **brak** rekordu (negacja, nie ustalenie). Walidujemy dokładnie to: czy model zamienia zdania na wiersze — wiernie, bez zmyślania i bez gubienia.

## Zakres / Definition of Done
- [x] 5 opisów zanonimizowanych (USG, echo, 3× kolonoskopia) — tokeny w `data/interim/narrative-anon/*.md`, zweryfikowane grepem (0 resztek PII). Zrobione przez Claude jako **jednorazowy wyjątek** (PII już częściowo w sesji z etapu 1); backfill 390 idzie przez Presidio
- [x] Prompt ekstrakcyjny do schematu — `src/extract_findings.py` (PROMPT), zasada „extract, don't infer" + jawna obsługa negacji/norm
- [x] Wywołanie przez `claude -p` + ocena ręczna — 52 ustalenia z 5 opisów; negacje/normy bez potknięć (5/5), kompletność wysoka, brak zmyśleń; słabości = schemat (jednostki, wielowymiar, status, dedup)
- [x] Decyzja: **GO**; 4 poprawki schematu naniesione do PRD v1.2 (status enum, lista `measurements`, normalizacja jednostek, dedup po badaniu)
- [x] Golden set per dokument — `data/interim/narrative-anon/*.golden.yml` (token → oryginał, lokalnie/gitignored); benchmark recall Presidio na etap 4. Pułapka złapana: NPWZ lekarza ukryty w OID dokumentu (`DOC_INSTANCE_ID_001`)

## Instrukcja ręcznej anonimizacji
Ręcznie, bo Presidio jeszcze nie istnieje, a reguła twarda z PRD obejmuje też sesję Claude Code (to też API Anthropic). PII w polskich opisach siedzi w nagłówku/stopce: pacjent (nazwisko → `PERSON_001`, PESEL → `PESEL_001`, data urodzenia → `DOB_001`, adres → `ADDRESS_001`), lekarz + PWZ → `DOCTOR_001`, placówka/nr badania → `FACILITY_001`/`EXAM_ID_001`. **Zostaje**: data badania (oś czasu) i cała treść medyczna. ~3–5 min/dokument.

## Notatki
<!-- Grupuj po temacie, nie po dacie (chronologię trzyma git). Każdy podpunkt
     w OSOBNYM akapicie (pusta linia między nimi). Dla każdego tematu:

### <Temat / czego dotyczy>

**Decyzja:** co ustalono.

**Dlaczego:** uzasadnienie, trade-offy.

**Jak działa:** mechanizm narzędzia pod spodem — sedno nauki.

**Pułapki:** co zaskoczyło, na co uważać.

Nie każdy temat wymaga wszystkich czterech podpunktów. To notatki do nauki, nie log czynności. -->

### Walidacja ekstrakcji — wynik i decyzja

**Decyzja:** GO. `claude -p` (model domyślny Pro) na 5 zanonimizowanych opisach dał 52 ustalenia; mechanizm strukturyzuje prozę wiernie. Schemat doprecyzowany 4 poprawkami, naniesiony do PRD v1.2.

**Dlaczego:** główny risk z PRD („model gubi / nadinterpretuje") się nie zmaterializował — negacje i normy obsłużone bez potknięć w 5/5 („brak przerostu" → `nieobecny`, „prawidłowy" → norma), kompletność wysoka (Echo: 23 ustalenia z jednego akapitu), brak zmyśleń, tokeny PII zignorowane. Ryzyko okazało się nie w „czy LLM działa", lecz w kształcie schematu.

### Schemat — 4 poprawki wymuszone obserwacjami

**Decyzja:** (a) `status` = `prawidłowy`/`nieprawidłowy`/`nieobecny` (norma/patologia/wykluczone); (b) `measurements` jako lista `{value, unit, label}` zamiast pojedynczego pola; (c) normalizacja jednostek także w narracji (`units.yml` + domyślne domenowe); (d) dedup po badaniu (`exam_type` + `exam_date`).

**Dlaczego:** każda poprawka wynika z konkretnego defektu, nie z teorii — (a) prawidłowy płat tarczycy dostał `obecny`, a prawidłowy wymiar LV `prawidłowy` (enum mieszał obecność z normą); (b) „22×23×37 mm" zeszło do tekstu, w polu została tylko objętość; (c) BBPS raz `"BBPS"`, raz `"punkty z 9"` — ten sam byt, różna jednostka; (d) karta wizyty + opis + histopatologia to jedno badanie w trzech plikach → potrójne rekordy.

### Parsowanie wyjścia LLM — pułapka fence

**Pułapki:** model owija JSON w ` ```json `, przez co `json.loads` pada na char 0 mimo instrukcji „bez fence". Prompt nie wystarcza — parser musi być odporny na markdown-fence i preambułę (`strip_fence` w `extract_findings.py`). Zasada ogólna: nie ufaj, że LLM odda czysty JSON; zawsze sanityzuj wyjście.

