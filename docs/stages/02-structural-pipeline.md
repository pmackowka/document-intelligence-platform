# Etap 2 — Pipeline strukturalny (standaryzacja)

## Cel
Szybka wygrana z PRD: badania krwi/moczu/biochemii do kanonicznego JSON. Wejściem jest OCR-owany markdown (etap 1), wyjściem płaskie rekordy NDJSON `{panel, marker, value, value_text, unit, reference_low/high, exam_date, source_file}` — jeden marker = jeden rekord, gotowy do trendów.

Standaryzacja idzie w trzech warstwach nad wiedzą domenową z YAML (dodanie laboratorium = edycja configu, nie kodu): **Warstwa 1** mapuje nazwę źródłową na kanoniczny kod markera panel-aware (ten sam napis znaczy różne rzeczy w różnych badaniach), **Warstwa 2** wyciąga wartość liczbową/jakościową + jednostkę + zakres referencyjny, **Warstwa 3** dla nieznanej nazwy prosi Haiku o propozycję kodu i odkłada ją do `pending/` (człowiek zatwierdza). Realny materiał ma dwa układy — tabela markdown (morfologia/mocz/kał) i format sekcyjny (biochemia/lipidogram/tarczyca/PSA/serologia, gdzie wartość jest rozrzucona w luźnych liniach) — więc parser ma dwie ścieżki wybierane per-linia, ale wspólny słownik i schemat wyjścia.

## Zakres / Definition of Done
- [x] Warstwa 1: dictionary mapping (`config/aliases.yml`, **panel-aware** — „Leukocyty" = WBC w morfologii vs leukocyty w moczu) → kanoniczna nazwa markera; `src/structural_pipeline.py`
- [x] Warstwa 2: regex — ekstrakcja wartości liczbowej (`13.2`, `0,18`, `<1`) + jakościowej (`nieobecna`/`przejrzysty`); wartość i zakres chronione przed cyframi z dat
- [x] Normalizacja jednostek (`config/units.yml`, w tym błędy OCR + encja `&#124;`) + zakresy MIN/MAX z dokumentu → `reference_low`/`reference_high`
- [x] Ścieżka **tabeli** (parsowanie pozycyjne nazwa|wynik|jedn|MIN|MAX) i ścieżka **sekcji** (marker po inline `(ICD-9: kod)` lub nazwa-dziecko pod nagłówkiem; wartość zbierana z kolejnych linii) — wybierane per-linia
- [x] Gwarancja **S1 (nie gubić po cichu)**: nierozpoznana nazwa w tabeli oraz linia markera z realnym kodem ICD w sekcji → `unknown` (Warstwa 3); żadne wejście nie znika — zweryfikowane na syntetycznym nowym markerze
- [x] Nowe panele w `config/aliases.yml`: koprogram (kał), biochemia (OB/Glukoza/ALT/AST/Mocznik/Kreatynina/eGFR/Kwas moczowy), lipidy, tarczyca (TSH/FT3/FT4), psa; rozszerzona morfologia (RDW-SD/IG/NRBC). Etykiety raportowe → `config/marker_labels.yml`
- [x] Warstwa 3: `claude -p --model haiku` proponuje kod dla nieznanych → `data/pending/aliases.yml`; **sanityzacja wyjścia** — akceptujemy wyłącznie pojedynczy token-kod, proza/odmowa → `NEEDS_REVIEW`
- [x] Flow zatwierdzania: pipeline czyta **wyłącznie** `config/` (nigdy `pending/`); nieznane → `pending/`. Cykl wykonany realnie — propozycje z poprzedniego runu (RDW-SD/IG/NRBC/koprogram) zatwierdzone przez przeniesienie do `config/aliases.yml`, kolejny run rozpoznaje je (0 nieznanych)
- [x] Przetworzone end-to-end ≥10 realnych dokumentów: **14 dok. → 114 rekordów, 0 nieznanych, 0 cichych strat** (poprzednio lipidogram/biochemia dawały 0 rekordów)

## Notatki
<!-- Grupuj po temacie, nie po dacie (chronologię trzyma git). Każdy podpunkt
     w OSOBNYM akapicie (pusta linia między nimi). Dla każdego tematu:

### <Temat / czego dotyczy>

**Decyzja:** co ustalono.

**Dlaczego:** uzasadnienie, trade-offy.

**Jak działa:** mechanizm narzędzia pod spodem — sedno nauki.

**Pułapki:** co zaskoczyło, na co uważać.

Nie każdy temat wymaga wszystkich czterech podpunktów. To notatki do nauki, nie log czynności. -->

### Dwa formaty źródła — jedna ścieżka nie wystarcza

**Decyzja:** parser ma dwie ścieżki (tabela / sekcja) wybierane per-linia, ale wspólny słownik i wspólny schemat wyjścia.

**Dlaczego:** LUX MED miesza układy w obrębie jednego laboratorium — morfologia/mocz/kał wychodzą z OCR jako tabela markdown, a biochemia/lipidogram/tarczyca/PSA/serologia jako luźne linie, gdzie wartość, jednostka i zakres są rozrzucone. Jeden algorytm nie obsłuży obu bez rozgałęzienia.

**Jak działa:** linia zaczynająca się od `|` → parsowanie pozycyjne (kolumny nazwa|wynik|jedn|MIN|MAX); w przeciwnym razie ścieżka sekcyjna (anchor markera + zbieranie wartości z kolejnych linii).

**Pułapki:** nagłówek panelu tabeli potrafi siedzieć w komórce (`| Morfologia krwi (ICD-9: C55) | ... |`), nie w osobnej linii — dlatego panel ustawiamy skanując ICD po wszystkich komórkach wiersza, zanim odrzucimy wiersz jako szum.

### Parsowanie sekcyjne: anchor markera + chunk wartości

**Jak działa:** Pass 1 przechodzi linie i zbiera *anchory* — linia markera to albo inline `Nazwa (ICD-9: kod)`, albo nazwa-dziecko pod nagłówkiem sekcji. Pass 2 dla każdego anchora bierze linie aż do następnego anchora i wyciąga: pierwsza liczba = wartość, znana jednostka (`config/units.yml`) = unit, czysto-liczbowe linie = zakres. Prozę referencyjną z liczbami („Poniżej 150 mg/dl") pomijamy — zakres tylko z linii, które są *wyłącznie* liczbami.

**Pułapki:** kod ICD w sekcji jest per-marker i bywa popsuty przez OCR (`-`, `055` zamiast `O55`), więc marker rozpoznajemy po NAZWIE, nie po kodzie. I odwrotnie: nagłówek sekcji (kod ICD panelu) musi mieć pierwszeństwo przed dopasowaniem po nazwie — bo nazwa nagłówka „Krew utajona w kale (ICD-9: A17)" jest identyczna z nazwą markera FOB; bez tego pierwszeństwa nagłówek tworzy pusty anchor-widmo, który zasysa wartość następnego markera.

### Gwarancja „nie gubić po cichu" i jej jedyna granica

**Decyzja:** każde nierozpoznane wejście, które wygląda na marker, trafia do `unknown` (→ Warstwa 3 → pending). To twarde S1 z PRD — cichy `continue` na nieznanej nazwie był realnym bugiem (lipidogram/biochemia dawały 0 rekordów i 0 flag).

**Jak działa:** nazwa w wierszu tabeli oraz linia sekcyjna markera z *realnym* kodem ICD → flaga. Grupujące nagłówki z kodem-śmieciem (`ICD-9: -`) nie są flagowane, bo nie są markerem.

**Pułapki:** została jedna świadoma dziura — luźna nazwa-dziecko BEZ kodu ICD (bare) jest nieodróżnialna od prozy referencyjnej, więc nieznaną bare pomijamy. W praktyce dzieci nagłówków (lipidy, PSA) to zamknięty, znany zbiór; ryzyko dotyczy wyłącznie nietypowego laboratorium z nową nazwą bez ICD. Trade-off, nie przeoczenie.

### Pułapki OCR w formacie sekcyjnym

**Decyzja:** wartość łapiemy zawsze; jednostkę i zakres best-effort, bo OCR bywa je gubi lub przestawia.

**Pułapki:** (1) OCR miesza kolejność linii — jednostka Glukozy potrafi wylądować w chunku poprzedzającego OB; wtedy value jest poprawne, a unit/zakres nie. (2) PESEL/ID (≥6 cyfr) z trailera dokumentu wpadał jako wartość jakościowego FOB — stąd twarda blokada długich liczb i `break` po złapaniu wartości jakościowej. (3) MIN/MAX bywają odwrócone → sortujemy parę. (4) `##` z markdownu i encje HTML (`&gt;`, `&#124;`) trzeba odkodować, zanim odczytamy liczbę.

### Warstwa 3: po co sanityzacja wyjścia Haiku

**Decyzja:** przyjmujemy wyłącznie pojedynczy token wyglądający jak kod; wszystko inne → `NEEDS_REVIEW`.

**Dlaczego:** Haiku dla niepewnych nazw zwraca prozę albo odmowę („Nie ma takiego markera w configu…") zamiast kodu. Bez filtra `pending/aliases.yml` zapełnia się zdaniami, które operator i tak musi ręcznie czyścić — czyli human-in-the-loop przestaje oszczędzać pracę.

**Jak działa:** regex `[A-Za-z][A-Za-z0-9_-]{0,29}` na pierwszej linii (po zdjęciu backticków/cudzysłowów); prompt dodatkowo wymusza jeden token bez spacji i literalne `NEEDS_REVIEW` przy braku pewności.

