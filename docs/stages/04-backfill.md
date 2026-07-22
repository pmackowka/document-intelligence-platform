# Etap 4 — Backfill i weryfikacja Success Criteria

## Cel
Przetworzenie dokumentów strukturalnych z archiwum ~390 plików (szacunkowo ~30%, czyli ok. 100–120 — reszta to narracyjne, poza zakresem V1) i pomiar S1–S4 z PRD. Rozłożone w czasie — tempo ograniczone limitami abonamentu Pro (~3 dok./dzień wystarcza).

Sedno: to pierwszy etap, gdzie pipeline (etapy 0–3, już zbudowany i zwalidowany na 14 dokumentach) spotyka się z realną skalą i realnym czasem — nie „czy działa", tylko „czy przeżyje przerwanie w połowie, czy policzy dokumenty nieczytelne zamiast je przemilczeć, i czy operator nie zniechęci się zatwierdzaniem". PRD ma to nazwane wprost w tabeli ryzyk: „zatwierdzanie ręczne zniechęci po backfillu → front-load, słownik nasyca się na pierwszych ~50 dokumentach" — stąd pierwsza partia to ~50, nie cały wolumen naraz.

Trzy strumienie pracy: (1) domknięcie brakujących mechanizmów DoD w kodzie (licznik odrzuconych, wznawianie Warstwy 3 po przerwaniu) — zbudowane i przetestowane PRZED dotknięciem realnych danych; (2) pierwsza partia ~50 dokumentów, przetworzona i zmierzona pod S1; (3) test S3 (nowy dokument end-to-end ≤15 min) na pojedynczym realnym pliku.

## Zakres / Definition of Done
- [x] Partia wsadowa: kolejkowanie (numerowany postęp `[i/N]`, stała kolejność `sorted()`), wznawianie po przerwaniu (Warstwa 3 odzyskuje propozycje z `pending/aliases.yml` zamiast pytać Haiku drugi raz), licznik dokumentów odrzuconych (próg `MIN_OCR_CHARS=500`, kalibrowany na realnych danych) — `src/structural_pipeline.py`, oba mechanizmy przetestowane jednostkowo (mock Haiku, syntetyczny pending) przed uruchomieniem na realnych danych; zero regresji na 14 istniejących dokumentach (114 rekordów, bez zmian)
- [x] S1: 100% markerów zmapowanych (200 rekordów, 0 nieznanych) na 40 dokumentach pierwszej partii; 32/40 (80%) dało realne rekordy, **8/40 (20%) świadomie odrzucone** (trzeci, nierozpoznany format — pojedyncze testy bez tabeli/ICD-9/nawiasów, decyzja operatora po sprawdzeniu struktury: nie inżynierować kolejnego parsera dla garstki jednorazowych przypadków, patrz notatka „8 odrzuconych dokumentów"). Liczba spadła z 221 do 211 w trzech rundach poaudytowych poprawek (patrz „Trzy błędy znalezione po domknięciu etapu" i „Drugi audyt"), potem z 211 do 200 po wykluczeniu 3 dokumentów o pomieszanej kolejności OCR (patrz „Czwarty audyt" niżej) — 37/40 aktywnie w magazynie
- [x] S3: nowy dokument przechodzi pipeline end-to-end w ≤15 min pracy operatora — zmierzone na realnym pliku (`Bilirubina, Kreatynina, Potas : K, Sód : Na.pdf`): **13,5 min (813s), PASS**. Sam pipeline: 44s. Reszta: zatwierdzenie 1 nowego aliasu (`BIL_IND`) + narzut identyfikacji, który plik jest nowy (nie dotyczy normalnego użycia — operator wie, co dodał)
- [x] Pomiar i zapis wyników S1–S4 w tym pliku
- [x] Retrospektywa: co poprawić przy bieżącym napływie nowych dokumentów (2–3/mies.)
- [x] Kolumna `Źródło` (nazwa pliku źródłowego) w raporcie Markdown + usunięcie martwego pola `record_type` ze schematu NDJSON — pierwszy krok do weryfikacji krok-po-kroku przy bieżącym, małym napływie (patrz notatka niżej)
- [x] Migawki datowane (`data/store/YYYY-MM-DD-structural.ndjson`) zamiast bezpośredniego nadpisania zaufanego magazynu — scalenie ręczne, na żądanie operatora, dopiero po weryfikacji raportu (PRD v1.3, patrz notatka niżej)

## Wyniki S1–S4

| # | Kryterium | Próg | Wynik |
|---|---|---|---|
| S1 | ≥95% dokumentów w kanonicznym JSON, 100% markerów zmapowanych/odrzuconych | — | **PASS** — 200 rekordów (211 → 200 po wykluczeniu 3 dokumentów o pomieszanej kolejności OCR, patrz „Czwarty audyt"), 0 nieznanych markerów, 29/37 (78%) aktywnych dok. z wynikami + 8/37 (22%) świadomie odrzuconych = 100% z 37 aktywnie przetwarzanych rozliczone; dodatkowo 11 wierszy z rozpoznanym markerem, ale bez ustalonego wyniku, flagowane do ręcznego przeglądu (nie liczą się jako "zmapowane", nie giną po cichu) |
| S2 | Trend markera z ≥3 pomiarami dostępny jednym promptem | ≥3 pomiary | **PASS** — 20 serii marker+jednostka z ≥3 datami (np. cholesterol całkowity: 4 pomiary, 2020–2025, 194→238→227→225 mg/dl); ponownie zweryfikowane po naprawie `report.py` (patrz notatka niżej) — realnie wygenerowany raport, nie tylko zapytanie do NDJSON |
| S3 | Nowy dokument end-to-end | ≤15 min pracy operatora | **PASS** — 13,5 min na realnym pliku z 1 nowym aliasem do zatwierdzenia (sam pipeline: 44s) |
| S4 | NDJSON ładuje się do BigQuery bez transformacji | brak błędów schematu | **PASS** — potwierdzone przez operatora (etap 3): load 11-kolumnowy, potem 12-kolumnowy (`reference_note`) po rozszerzeniu schematu, oba bez błędów |

## Notatki
<!-- Grupuj po temacie, nie po dacie (chronologię trzyma git). Każdy podpunkt
     w OSOBNYM akapicie (pusta linia między nimi). Dla każdego tematu:

### <Temat / czego dotyczy>

**Decyzja:** co ustalono.

**Dlaczego:** uzasadnienie, trade-offy.

**Jak działa:** mechanizm narzędzia pod spodem — sedno nauki.

**Pułapki:** co zaskoczyło, na co uważać.

Nie każdy temat wymaga wszystkich czterech podpunktów. To notatki do nauki, nie log czynności. -->

### ROZWIĄZANE — tabela bez nagłówka ICD-9, nie brakujący alias ani format `[XXX]`

**Status: naprawione tej samej sesji, po tym jak pierwsza diagnoza (poniżej, zachowana jako nauka) okazała się częściowo błędna.**

**Pierwsza diagnoza (błędna w szczególe):** wyglądało na to, że problem to markery zapisane w nawiasach kwadratowych `[L23] Fosforany` zamiast `(ICD-9: L23)`, i że trzeba nauczyć parser rozpoznawać ten format jako inline-kod sekcyjny. Dodałem taki wzorzec (`_BRACKET_CODE`) — działał poprawnie na syntetycznym teście, ale **nie zmienił nic na realnych danych**. Dobra lekcja: syntetyczny test poprawności mechanizmu ≠ dowód, że to ten mechanizm jest przyczyną realnego problemu.

**Prawdziwa przyczyna, znaleziona przez sprawdzenie surowego OCR:** `[L23] Fosforany` nie jest bare linią sekcyjną — to **pierwsza kolumna wiersza TABELI** (`| [L23] Fosforany | 3,06 mg/dl | ... |`). Ten nowy lab nigdy nie drukuje rozpoznawalnego nagłówka `(ICD-9: kod)` dla całej tabeli (w przeciwieństwie do „Morfologia krwi (ICD-9: C55)” z oryginalnego labu) — `panel` zostawał `None` przez cały dokument, a `resolve(None, klucz)` zawsze zwraca `None`, niezależnie od tego, że 47 aliasów dla dokładnie tych markerów było już zatwierdzonych w `config/aliases.yml` (commit `b13e11a`).

**Naprawa:** `ALL_MARKERS` — płaski lookup po wszystkich panelach (nie tylko sekcyjnych, jak istniejący `SECTION_MARKERS`), użyty jako fallback w ścieżce tabeli WYŁĄCZNIE gdy `panel is None`. Fallback per-wiersz (`row_panel`, nie nadpisuje globalnego `panel`) — jeden trafiony marker z panelu „biochemia” nie blokuje kolejnego wiersza tej samej tabeli należącego do „morfologia”; zweryfikowane testem na syntetycznej tabeli mieszanej PRZED uruchomieniem na realnych danych.

**Efekt:** 164→216 rekordów, 51→0 nieznanych markerów na 39 dokumentach. `Brak nieznanych markerów — wszystkie zmapowane.`

**Pułapka do zapamiętania:** dwie różne przyczyny dawały ten sam objaw w logu („nieznany marker”) — bracket-w-linii-sekcyjnej (rozwiązanie: `_BRACKET_CODE`, realny choć nie dla TEGO przypadku) i tabela-bez-nagłówka (rozwiązanie: `ALL_MARKERS`). Nie zakładaj jednej przyczyny dla jednego objawu — sprawdź surowy OCR, zanim napiszesz poprawkę.

### 8 odrzuconych dokumentów — trzeci format, świadoma decyzja nie inżynierować dalej

**Decyzja:** `183202680.pdf`, `2026.01.09 - Kał - pasożyty.pdf`, `2026.05.14 - Endokrynologiczne (Hormony) 1.pdf`, `Badanie ogólne moczu.pdf`, `CK - (kinaza kreatynowa).pdf`, `Kalprotektyna w kale (ilosciowo).pdf`, `Kał badanie ogólne i ocena resztek pokarmowych.pdf`, `Krew utajona w kale.pdf` — świadomie odrzucone dla tej partii backfillu, nie przetwarzane dalej.

**Dlaczego:** struktura OCR sprawdzona dla wszystkich 8 (zero PII, tylko kształt: liczba znaków, obecność `|`/`ICD-9`/`[XXX]`) — żaden nie ma tabeli, żaden nie ma nawiasów kwadratowych, a jedyny trafiony `ICD-9` (`CK - kinaza kreatynowa.pdf`) wygląda na uszkodzony przez OCR (`(ICD-9: 2 140` bez zamykającego nawiasu). To **trzeci format** tego samego nowego labu — pojedyncze testy (jeden marker na dokument), prawdopodobnie prosty układ „nazwa: wynik" bez żadnej z dwóch already-obsługiwanych konwencji (tabela, sekcja z inline kodem). Koszt zaprojektowania i przetestowania kolejnego wzorca parsera dla 8 jednorazowych przypadków (21% partii, ale każdy inny plik = inny mini-dokument, nie powtarzalny wzorzec na dużą skalę) przewyższa wartość — ten sam kompromis co przy progu referencyjnym lipidogramu w etapie 3.

**Jak działa mechanizm odrzucenia:** techniczie to wciąż flaga `⚠ SPRAWDŹ RĘCZNIE (nierozpoznany format)` z kodu (nie cichy brak) — „świadome odrzucenie" z PRD to warstwa DECYZJI operatora NAD tą flagą, nie osobny mechanizm w kodzie. Licznik S1 liczy je jako świadomie odrzucone od momentu tej decyzji (2026-07-21), nie automatycznie.

**Pułapki / do rewizji:** jeśli w kolejnej partii backfillu (etap 4, kolejne ~50–70 dokumentów) ten sam trzeci format zacznie się powtarzać w większej liczbie plików, opłacalność inżynierowania wzorca „nazwa: wynik" się zmienia — wróć do tej notatki i przelicz ponownie, zamiast zakładać że decyzja z 39-dokumentowej próbki jest trwała.

### Ile dokumentów w pierwszej partii — nie zgadywanie, tylko PRD

**Decyzja:** pierwsza partia backfillu to ~50 dokumentów, nie cały szacowany wolumen (~100–120) naraz.

**Dlaczego:** to nie nowa decyzja — PRD miał to już nazwane w tabeli ryzyk przed etapem 4: „Zatwierdzanie ręczne zniechęci po backfillu → Front-load: słownik nasyca się na pierwszych ~50 dokumentach". Operator zapytał wprost „ile teraz" — odpowiedź wyciągnięta z już podjętej decyzji projektowej, nie świeże zgadywanie. Dodatkowy argument: 14 dokumentów już przetworzonych ujawniło jeden realny gap parsera (`reference_note`, etap 3) mimo małej próby — większa, zróżnicowana partia od razu, przed zbudowaniem odporności na przerwanie, byłaby ryzykowniejsza niż trzeba.

### Próg odrzucenia „nieczytelny OCR" — kalibracja z realnych danych, nie zgadana liczba

**Decyzja:** `MIN_OCR_CHARS = 500` — dokument z OCR poniżej tego progu liczy się jako odrzucony (nieczytelny), nie jako „0 rekordów" bez wyjaśnienia.

**Dlaczego:** DoD wymaga licznika odrzuconych, którego pipeline nie miał. Próg musiał rozdzielić dwie znane grupy: najkrótszy PRAWDZIWY dokument w próbce etapu 2 miał 710 znaków; najdłuższy ZNANY pusty/nieczytelny OCR (placeholder `<!-- image -->` z audiogramów, etap wcześniej usunięty z projektu) miał 394. Między 394 a 710 jest przerwa — 500 leży bezpiecznie w środku.

**Pułapki:** pierwsza wersja progu (300) przeszła code review „na oko", ale nie przeszła własnego testu — 300 nie łapało znanego przypadku 394 znaków. Dopiero jednostkowy test na obu granicznych wartościach (`710 > próg`, `394 < próg`) to złapał. Kalibrowanie progu bez sprawdzenia go na obu skrajnych, już znanych przypadkach to fałszywe poczucie bezpieczeństwa.

### Wznawianie Warstwy 3 po przerwaniu — koszt bez tego mechanizmu

**Decyzja:** przed zapytaniem Haiku o nieznany marker, `load_existing_proposals()` sprawdza, czy `pending/aliases.yml` z poprzedniego (możliwe że przerwanego) runu już ma propozycję dla tej samej pary (panel, znormalizowana nazwa). Jeśli tak — odzyskuje ją bez wywołania API.

**Dlaczego:** przy backfillu ~50 dokumentów pod limitami abonamentu Pro przerwanie w połowie (throttle, Ctrl+C, cokolwiek) jest realnym scenariuszem, nie teoretycznym — dokładnie to samo ryzyko zmaterializowało się w etapie 5 (narracyjnym, dziś usuniętym) przy serii wywołań `claude -p`. Bez tego mechanizmu każde wznowienie od nowa odpytywałoby Haiku o WSZYSTKIE nieznane markery, łącznie z tymi już czekającymi na zatwierdzenie — marnowanie wywołań i realne złamanie litery DoD („wznawianie po przerwaniu").

**Jak działa:** `pending/aliases.yml` ma strukturę `{pending_panels: {panel: {nazwa: kod}}}` — funkcja spłaszcza to do słownika `(panel, norm(nazwa)) -> kod`. Pętla Warstwy 3 sprawdza ten słownik PRZED wywołaniem `propose_alias_haiku()`; trafienie = reużycie, licznik `reused` raportowany w logu.

**Pułapki:** zweryfikowane testem z podmienioną (monkeypatch) funkcją Haiku, która rzuciłaby błąd, gdyby została wywołana dla już znanego markera — nie samą inspekcją kodu. Realne dane strukturalne mają dziś 0 nieznanych markerów (słownik nasycony po etapie 2), więc mechanizmu nie dało się przetestować na produkcyjnym przebiegu — test izolowany był jedyną drogą do sprawdzenia go przed pierwszym realnym backfillem.


### Retrospektywa — co poprawić przy bieżącym napływie (2–3 dok./mies.)

**Decyzja:** proces jest gotowy na bieżący, mały napływ bez dalszych zmian w kodzie — S3 (13,5 min na dokument z nowym markerem, 44s sam pipeline) daje duży margines wobec ~3 dok./dzień, na które PRD i tak zakłada limit abonamentu Pro. Nic w mechanizmie nie wymaga poprawy PRZED kontynuacją; to, co wymagało poprawy, poprawiło się w trakcie tej właśnie partii.

**Dlaczego (co się nauczyliśmy z 40 dokumentów):** każde NOWE źródło (inny lab niż oryginalny LUX MED/Diagnostyka) przynosi własne, nieoczekiwane konwencje formatowania — w tej jednej partii: nawiasy kwadratowe zamiast `(ICD-9: X)`, tabele bez żadnego nagłówka panelu, linie metadanych (nr księgi, autoryzacja, materiał/metoda badania) mylone z markerami. Trzy różne przyczyny, ten sam objaw w logu („nieznany marker”) — żadnej nie dało się przewidzieć z góry, wszystkie wymagały sprawdzenia surowego OCR, nie zgadywania z samego kształtu danych w `pending/`. Konkretny wniosek na przyszłość: gdy pojawi się KOLEJNY nowy lab, oczekuj podobnego wzorca (1–3 nowe „dziury” parsera) i zacznij diagnozę od tego samego miejsca — `data/interim/structural-ocr/*.md`, sprawdzenie obecności `|`, `ICD-9`, nawiasów — zanim cokolwiek naprawisz.

**Jak działa proces przeglądu aliasów (potwierdzone realnie, nie teoretycznie):** ręczny przegląd propozycji Haiku złapał realne błędy, nie tylko potwierdził oczywistości — niespójne kody dla tego samego markera (`NEUT` vs `NEU`, `MON` vs `MONO`), i co ważniejsze: 3 z 8 wstępnych „pewnych” przypisań krew/mocz były błędne, wykryte dopiero po sprawdzeniu, z którego PLIKU ŹRÓDŁOWEGO pochodzi każdy marker (nazwa pliku „Pierwiastki w krwi” vs „w moczu” rozstrzygnęła jednoznacznie tam, gdzie dopasowanie po samym kodzie zawodziło). To dowód, że HITL na aliasach nie jest biurokracją — realnie zapobiega cichemu mieszaniu danych.

**Pułapki:** limit abonamentu Pro objawił się realnie przy 96 sekwencyjnych wywołaniach Haiku naraz (timeout w środku pętli) — teraz obsłużone (zapis po każdym markerze, pojedynczy timeout nie ubija reszty), ale przy kolejnych dużych partiach nadal lepiej rozkładać w czasie niż odpalać wszystko jedną komendą, zgodnie z ryzykiem już nazwanym w PRD.

### Trzy błędy znalezione po domknięciu etapu — spójność danych przed load'em do BigQuery

**Decyzja:** przed pierwszym realnym wgraniem do BigQuery i pokazaniem czegokolwiek lekarzowi zrobiony osobny przegląd spójności danych (nie tylko S1 "0 nieznanych markerów" — to sprawdza WYŁĄCZNIE nazwy, nie wartości). Znaleziono i naprawiono trzy niezależne błędy, żadnego nie było widać w metrykach S1–S4, bo wszystkie dotyczyły WARTOŚCI/DATY przy już poprawnie rozpoznanej nazwie markera.

**Błąd 1 — `report.py` się wywalał:** `rows.sort(key=lambda r: r["exam_date"])` porównuje `None` z `None`/stringiem, gdy w grupie marker+jednostka trafiały się rekordy bez daty obok rekordów z datą — `TypeError` przy generowaniu raportu, live-reprodukowane. Naprawa: `key=lambda r: r["exam_date"] or ""` + wyświetlanie „brak daty" zamiast literalnego `None` w tabeli.

**Błąd 2 — `exam_date` rozpoznawał tylko jeden format:** regex `_DATE` łapał wyłącznie `"Data wykonania: DD.MM.YYYY"` (oryginalny lab). Nowe laby z etapu 4 piszą to samo innym słowem/formatem („Data/godz. pobrania: YYYY-MM-DD", „data i godzina pobrania: DD-MM-YYYY") — 60/221 rekordów (27%) miało `exam_date: null`, mimo że data była wprost w tekście OCR. Naprawa: `_DATE_FORMATS`, lista wzorców próbowanych po kolei (pierwsze trafienie wygrywa — oryginalny wzorzec zostaje pierwszy, zero ryzyka regresji). Po naprawie: 33/212 (16%) bez daty, i to jest twardy sufit, nie niedopatrzenie — patrz Pułapki.

**Błąd 3 — kolumna "jednostka" cicho łapała zakres referencyjny:** pozycyjny parser tabeli zakłada stały układ `nazwa|wynik|jedn|MIN|MAX`. Część nowych labów pakuje wynik+jednostkę w jedną komórkę ("40,2 nmol/l") i zakres referencyjny w drugą ("17,1 — 77,6") zamiast czterech osobnych kolumn — komórka z zakresem lądowała w polu `unit` jak leci (`canon_unit()` bez dopasowania w słowniku zwraca surowy tekst komórki), a garbowana przez OCR data z kolumny "Wykonanie" bywała odczytana jako liczba i trafiała do `reference_high` (np. `SHBG.reference_low: 24.0202` — to fragment daty, nie dolna granica). Naprawa: `_range_from_cell()` rozpoznaje komórkę-zakres ("17,1 — 77,6") i komórkę-granicę ("< 5,61") niezależnie od tego, w której pozycji się znajdzie (kolumna jednostki albo MIN), z limitem 1–3 cyfr przed przecinkiem — odróżnia realny zakres referencyjny od zlepionej przez OCR daty w sąsiedniej kolumnie. Dodatkowo: wiersze, gdzie ani `value`, ani `value_text` nie dało się ustalić (wynik przesunięty do innej komórki niż zwykle — obserwowane u wierszy oflagowanych jako poza normą), trafiają teraz do osobnej listy "wątpliwe" i są widoczne w podsumowaniu pipeline'u zamiast cicho zapisywać się jako pusty rekord.

**Jak działa (zasada wspólna):** we wszystkich trzech przypadkach naprawa to "nie zgaduj, sygnalizuj" — dokładnie ta sama zasada, co przy `reference_note` (etap 3) i "8 odrzuconych dokumentów" (wyżej). Cichy `None`/pominięty wiersz jest tańszy do naprawienia później niż cicho zapisana zła liczba, która wygląda wiarygodnie w raporcie "do lekarza".

**Pułapki:** dwa pliki (`188572094`, `190111920` — z portalu Medicover) mają layout, w którym etykieta i wartość są w OSOBNYCH blokach tekstu, dopasowywanych pozycyjnie (7. etykieta = 7. wartość w kolejności), a nie "etykieta: wartość" w jednej linii — np. "Data pobrania:" sąsiaduje bezpośrednio z datą urodzenia (`18/10/1981`), a prawdziwa data pobrania (`18/11/2023`) leży 5 linii dalej. Świadomie NIE dodano do tego regexu — zgadywanie na podstawie samej bliskości tekstu groziłoby przypisaniem złej daty (np. urodzenia zamiast pobrania), co jest gorsze niż `None`. To 33 rekordy bez daty, zostają tak do czasu osobnej, dedykowanej naprawy tego layoutu (nie prosta zmiana regexu).

Po naprawie znaleziono też dwa DODATKOWE, jeszcze nienaprawione problemy (poza zakresem tej sesji, celowo nieujęte): `fmt_value()` w `report.py` wypisuje literalne „None" przy rekordach z ustawioną liczbową `value`, ale `unit=None` (np. INR, gdzie brak jednostki jest poprawny — sam marker jest bezjednostkowy); oraz `parse_section_chunk` w jednym dokumencie (`2026.04.02 - Badanie lekarskie 1`, marker Mg) wciąga do `value_text` całe zdanie metody badania zamiast zatrzymać się na wyniku. Oba udokumentowane tutaj, żeby nie zniknęły cicho — nie blokują S1–S4, ale wymagają uwagi przed kolejnym pokazaniem raportu lekarzowi.

### Drugi audyt (ręczny przegląd raportu przez operatora) — cztery kolejne błędy

**Decyzja:** po pierwszym audycie operator ręcznie przejrzał wygenerowany raport wiersz po wierszu (nie tylko losowe próbki) i znalazł cztery kolejne, niezależne błędy — żaden nie był widoczny w metrykach S1/S2, bo wszystkie dotyczyły FORMATOWANIA i GRUPOWANIA już poprawnych danych, nie samej ekstrakcji.

**Błąd 1 — literalne „None" w kolumnie Wartość (16 markerów, 23 wiersze):** `fmt_value()` doklejało jednostkę bez warunku (`f"{value:g} {unit}"`) — gdy `unit is None` (marker bezjednostkowy, np. INR, albo jednostka nie została znaleziona w danym dokumencie), Python wypisywał to dosłownie jako tekst „None". Naprawa: dokleja jednostkę tylko gdy istnieje.

**Błąd 2 — ten sam marker rozbity na 2-3 osobne tabele:** grupowanie w `report.py` było sztywno po `(marker, jednostka)`. Ten sam marker kliniczny bywa raz zapisany z jednostką, raz bez (bo konkretny dokument jej nie miał albo parser jej nie znalazł) — sztywne grupowanie traktowało to jako dwie różne serie zamiast jednego trendu. Naprawa: grupuj po markerze, dziel po jednostce TYLKO gdy dla markera istnieją >=2 realne (niepuste) jednostki w danych — bo to jedyny przypadek, gdzie rozdzielenie ma sens kliniczny (NEU/LYM/MONO/EOS/BASO w % vs tys/µl, TSH w mIU/ml vs µIU/ml — świadomie NIE scalone, bo różnica jednostek może być realna, nie tylko kosmetyczna, a to nie jest decyzja do zgadywania przez kod).

**Błąd 3 — dwuznaczne etykiety, ten sam polski label dla różnych badań:** `marker_labels.yml` miało „Leukocyty" (WBC krew *i* mocz), „Glukoza" (krew *i* mocz), „Barwa" (mocz *i* kał), „Krew" (mocz, ale niejednoznaczne samo w sobie). Naprawa: strona moczowa/kałowa dostaje jawny kwalifikator („Krew w moczu", „Glukoza w moczu" itd.) — strona krwi zostaje bez kwalifikatora, zgodnie z konwencją już istniejącą w pliku (`FOB: "Krew utajona w kale"`).

**Błąd 4 — luka w strażniku pustych rekordów, ale tylko w ścieżce SEKCYJNEJ:** strażnik „nie zapisuj pustego rekordu" z pierwszego audytu (patrz wyżej) objął tylko wiersze TABEL. Format sekcyjny (biochemia, tarczyca, PSA...) ma osobną pętlę (Pass 2, dopasowanie anchor→chunk) z osobnym, słabszym strażnikiem — wymagał, żeby WSZYSTKIE pola (wartość, jednostka, zakres, notatka) były puste jednocześnie, więc rekord z samą jednostką, ale bez wyniku (np. CRP: `unit="ng/ml"`, `value=None`, `value_text=None`) i tak trafiał do magazynu. Naprawa: ten sam warunek co w tabeli — brak wartości I brak tekstu wyniku, niezależnie od tego, czy jednostkę/zakres udało się złapać.

**Jak działa (weryfikacja przed zamknięciem):** wszystkie cztery poprawki zweryfikowane na PRAWDZIWYCH danych, nie syntetycznym teście — ponowne uruchomienie pipeline'u (210 rekordów, 0 nieznanych, 11 wierszy do ręcznego przeglądu) i `grep` po regenerowanym raporcie: `None |` → 0 wystąpień, zduplikowane nagłówki `###` → 0. `brak daty` (33) i celowo nienaprawiony błąd formatu sekcyjnego w dokumencie „Bilirubina, Kreatynina..." (BIL_IND, Kreatynina — wymaga decyzji o nowych kodach aliasów) zostały nietknięte, zgodnie z ustaleniem zakresu z operatorem.

**Pułapki:** to NIE była ręczna korekta pliku wyjściowego — wszystkie cztery poprawki żyją w `src/report.py` i `src/structural_pipeline.py`, więc każde kolejne uruchomienie pipeline'u (nowy dokument, backfill, cokolwiek) automatycznie z nich korzysta. Odróżnienie „naprawiam dzisiejszy raport" od „naprawiam system, który generuje wszystkie przyszłe raporty" — świadomie wybrane to drugie, zgodnie z zasadą projektu (kod, nie ręczne łatanie danych).

### Trzeci audyt — grupa bilirubiny źle skonfigurowana + wyciek nazwiska pacjenta do danych

**Decyzja:** operator przesłał zrzut ekranu oryginalnego PDF-u (nie samego markdown) — czytelniejszy od rozjechanego tekstu OCR, ujawnił dokładną strukturę: „Bilirubina wolna (pośrednia) (ICD-9: I91)" to NAGŁÓWEK GRUPY trzech osobnych wyników (Bilirubina związana, Bilirubina wolna, Bilirubina całkowita), nie sam wynik. Wcześniejszy alias `"bilirubina wolna (posrednia)": "BIL_IND"` mylił nagłówek z markerem. Naprawa: alias przeniesiony na właściwy wiersz-dziecko („Bilirubina wolna" bez dopisku), dodane dwa nowe kody (`BIL_DIR`, `BIL_TOTAL`) i etykiety w `marker_labels.yml`, nagłówek grupy dodany do `_NOISE`.

**Przy okazji znaleziony osobny, poważniejszy błąd:** po odfiltrowaniu artefaktu `<!-- image -->` (ten sam commit) kolejny wynik w tym samym dokumencie (Kreatynina) złapał jako „wynik" tekst **„MAĆKÓWKA PIOTR"** — imię i nazwisko właściciela danych, wzięte z powtórzonego nagłówka pacjenta na 2. stronie PDF-u (`Pacjent:\n\n## MAĆKÓWKA PIOTR`, sformatowane jako nagłówek markdown, więc niewidoczne dla filtra szumu po `.lstrip("#")`).

**Jak działa naprawa:** pierwsza wersja (odrzucić WSZYSTKIE nagłówki markdown wewnątrz chunku sekcyjnego) była zbyt szeroka — złapała też PRAWDZIWY wynik jakościowy sformatowany jako nagłówek (`## nie wykryto` dla antygenu HBs, realny przypadek w 2 innych dokumentach) i o mało nie spowodowała cichej regresji. Właściwa naprawa: `parse_section_chunk` pamięta, czy poprzednia (odfiltrowana jako szum) linia była etykietą osobową (Pacjent:/Lekarz/Odbiorca/Autoryzował) — jeśli tak, NASTĘPNA linia jest gaszona jako nazwisko, niezależnie od wielkości liter czy formatowania nagłówkowego. `## nie wykryto` nie jest poprzedzone taką etykietą, więc przechodzi normalnie.

**Pułapka do zapamiętania:** ta sama lekcja co przy etapie 3/4 wcześniej — pierwsza, prostsza wersja poprawki (blanket-filter nagłówków) wyglądała słusznie w izolacji, ale złamałaby realny, już działający przypadek gdzieś indziej w tych samych 40 dokumentach. Zawsze sprawdzić poprawkę na PEŁNYM zbiorze, nie tylko na dokumencie, w którym znaleziono błąd.

### Czwarty audyt — pomieszana kolejność OCR w 3 dokumentach, wykluczone z magazynu

**Decyzja:** trzy dokumenty przeniesione poza aktywne przetwarzanie do `data/raw/structural/_excluded-scrambled-ocr/` (folder lokalny, nie w gicie — jak cała reszta `data/`): `2026.04.02 - Badanie lekarskie 1.jpeg`, `2026.04.02 - Badanie lekarskie 2.jpeg` (strona 2 tego samego badania), `2026.01.09 - CK, Kwas moczowy _ Uric acid, Potas _ K, Sód _ Na.pdf`. Wykluczone, nie łatane — 211→200 rekordów.

**Dlaczego:** operator ręcznie sprawdził wartości w raporcie pod kątem klinicznej wiarygodności (nie tylko obecność/format) i złapał to, czego żaden automatyczny check nie łapie — zakres referencyjny ALP zmienił się drastycznie między dwoma badaniami w odstępie miesiąca, co jest statystycznie nieprawdopodobne dla stałego parametru laboratoryjnego. Sprawdzenie surowego OCR ujawniło przyczynę: w pliku „Badanie lekarskie 1" wartości/jednostki/zakresy ALP, Ca, PHOS, Mg, VIT_D_25OH i eGFR były systematycznie POMIESZANE MIĘDZY MARKERAMI (nie tylko przesunięte w obrębie jednego wiersza, jak w błędzie 3 z pierwszego audytu) — DOCLING pogubił kolejność czytania na tym konkretnym layoucie. Ten sam katalog źródłowy (ten sam portal/szablon) dał też drugi plik z identycznym objawem (Na/K/Kwas moczowy pomieszane, K dostał błędną jednostkę „mg/dl" zamiast „mmol/l").

**Drugi wyciek PII, znaleziony przy okazji:** w pliku „Badanie lekarskie 1" `VIT_D_25OH.value_text` zawierał **„Mlngr DAMIAN CHARYTON"** — nazwisko lekarza autoryzującego wynik, złapane jako wartość markera z tego samego pomieszania kolejności OCR co reszta. Ten sam mechanizm ryzyka co PII pacjenta z „Trzeciego audytu" wyżej (dane osobowe trzeciej osoby lądujące w polu przeznaczonym na wynik liczbowy), inny wektor — tu nie brakująca reguła szumu, tylko fundamentalnie zgubiona kolejność tekstu w OCR, której nie da się naprawić regexem.

**Jak działa decyzja o wykluczeniu (nie naprawie):** przy pomieszanej kolejności czytania nie ma bezpiecznego sposobu odtworzenia, która wartość należała do którego markera — każda heurystyka pozycyjna zgadywałaby, co jest gorsze niż jawne wykluczenie z magazynu. Ten sam kompromis co „8 odrzuconych dokumentów" (koszt zaprojektowania parsera dla jednorazowego layoutu przewyższa wartość), ale tu odkryty PO tym, jak dokument już wyprodukował rekordy — różnica: te rekordy wyglądały wiarygodnie (liczby w sensownym zakresie), więc S1 („0 nieznanych markerów") ich nie złapał. Złapało dopiero ludzkie oko sprawdzające wiarygodność wartości, nie format.

**Pułapki:** to trzeci, niezależny typ błędu znaleziony w tej samej partii dokumentów (po: literalne „None", rozbite tabele/dwuznaczne etykiety, źle skonfigurowana grupa bilirubiny) — każdy audyt złapał inną klasę problemu, żaden nie był nadzbiorem poprzedniego. Automatyczne checki (liczba rekordów, „0 nieznanych", grep po „None") są konieczne, ale niewystarczające — nie zastępują przeglądu wartości pod kątem wiarygodności klinicznej. Jeśli kolejny dokument z tego samego portalu/szablonu pojawi się w przyszłości, oczekuj tego samego objawu i zacznij diagnozę od porównania surowego OCR z oryginałem strona po stronie, nie od regexa.

### Kolumna `Źródło` w raporcie + usunięcie `record_type` — pierwszy krok do weryfikacji krok-po-kroku

**Decyzja:** tabela w raporcie Markdown (`report.py::build_report`) dostała czwartą kolumnę — `Źródło` (nazwa pliku źródłowego, pole `source_file`, obecne w NDJSON od początku). Przy okazji usunięte martwe pole `record_type` (zawsze `"structural"`, bez informacji od czasu wycięcia pipeline'u narracyjnego z V1) — z rekordu w `structural_pipeline.py::_record` i ze schematu BigQuery w `docs/stages/03-storage-analysis.md` (12→11 kolumn).

**Dlaczego:** po czterech rundach audytu tej samej partii operator zasygnalizował, że ręczne sprawdzanie ~100+ dokumentów naraz przy każdym większym backfillu jest przytłaczające i nie do utrzymania, natomiast bieżący, mały napływ (PRD: 2–3 dok./mies.) już nie — propozycja: zamrozić obecną partię na obecnym poziomie zaufania (cztery rundy audytu, opisane wyżej), a każdy nowy dokument weryfikować pojedynczo, od razu po ingestcie. Kolumna `Źródło` to najtańszy możliwy krok w tym kierunku — operator widzi przy każdej wartości w raporcie, z którego pliku ona pochodzi, i może ją sprawdzić względem oryginału bez grzebania w NDJSON.

**Pułapka do rozwiązania later, nie dziś:** sama kolumna `Źródło` NIE chroni przed cichym dryfem już zweryfikowanych rekordów — `main()` przetwarza WSZYSTKIE pliki z `data/raw/structural/` od nowa i nadpisuje cały `structural.ndjson` przy każdym uruchomieniu (patrz `docs/stages/03-storage-analysis.md`), więc poprawka regexa zrobiona z powodu jednego nowego dokumentu teoretycznie może po cichu zmienić wartość w rekordzie, który operator już zweryfikował miesiąc wcześniej. Nic w kodzie dziś tego nie wykrywa. Rejestr zweryfikowanych dokumentów + porównanie starego/nowego magazynu ograniczone do już zweryfikowanych `source_file` (żeby złapać taki dryf, zamiast cicho go zaakceptować) zaproponowane, ale świadomie NIE zbudowane w tej sesji — decyzja odłożona do czasu, aż operator zdecyduje, czy ten dodatkowy narzut jest wart ceny.

### Migawki datowane + scalenie ręczne — domknięcie pułapki dryfu z poprzedniej notatki

**Decyzja:** operator zaproponował prostszą alternatywę dla rejestru weryfikacji + strażnika dryfu opisanego wyżej: zamiast automatycznie wykrywać dryf, **uniemożliwić go strukturalnie**. `structural_pipeline.py::main()` zapisuje teraz każdy przebieg do osobnej, datowanej migawki (`data/store/YYYY-MM-DD-structural.ndjson`) i **nigdy nie dotyka** zaufanego `data/store/structural-backfill.ndjson` (nazwa świadomie odróżniona od migawek — patrz notatka „Nazwa zaufanego pliku" niżej). Ten plik zmienia się wyłącznie, gdy operator — po ręcznej weryfikacji raportu wygenerowanego z migawki (kolumna `Źródło`, patrz notatka wyżej) — poprosi model w Claude Code o scalenie: zwykłą kopię wskazanej migawki na miejsce zaufanego pliku, wykonywaną na żądanie, nie automatycznie.

**Dlaczego to lepsze rozwiązanie niż rejestr + diff:** rejestr zweryfikowanych dokumentów + porównywanie starego/nowego magazynu (poprzednia propozycja) wymagałby nowego mechanizmu, który MUSIAŁBY być poprawny, żeby cokolwiek chronić — kolejny kawałek kodu do zaufania. Migawki + ręczne scalenie nie polegają na wykrywaniu błędu — zaufany plik fizycznie nie może się zmienić bez jawnej akcji operatora, więc nie ma czego wykrywać. Prostsze, bo `main()` i tak od zawsze robił pełny reprocessing (nie inkrementalny), więc „scalenie" to nie łączenie diffów, tylko podmiana jednego pliku na drugi — najtańsza możliwa operacja.

**Jak działa:** `report.py` przyjmuje teraz opcjonalny argument ścieżki (`uv run python src/report.py data/store/<data>-structural.ndjson`) — bez argumentu czyta zaufany magazyn, z argumentem dowolną migawkę-kandydata. Terminal jawnie oznacza tryb (`KANDYDAT` vs `zaufany magazyn`), żeby nie było wątpliwości, który plik właśnie się czyta.

### Nazwa zaufanego pliku — `structural-backfill.ndjson`, nie `structural.ndjson`

**Decyzja:** operator zauważył, że zaraz po wdrożeniu migawek zaufany plik (`structural.ndjson`) i migawka z tego samego dnia (`2026-07-22-structural.ndjson`) wyglądały jak przypadkowy duplikat tej samej nazwy — nieoczywiste na pierwszy rzut oka, który jest który. Zaufany plik przemianowany na `structural-backfill.ndjson`: nazwa czytelnie mówi, że to ciągły magazyn wywodzący się z pierwszego, dużego wsadu backfillu, wizualnie odróżniony od datowanych migawek przyszłych, mniejszych wsadów.

**Dlaczego bez daty w nazwie:** nazwa z konkretną datą (np. `structural-2026-07-22.ndjson`) sugerowałaby, że dane są zamrożone na ten dzień — mylące, skoro plik będzie się zmieniał przy każdym kolejnym scaleniu, miesiącami. `-backfill` opisuje POCHODZENIE linii danych (ten sam plik od pierwszego dużego wsadu, rozwijany scaleniami), nie moment zamrożenia — jak nazwa głównego brancha w gicie, który zostaje „main" niezależnie od tego, ile commitów później na niego trafi.

**Pułapki:** to czysto kosmetyczna zmiana nazwy pliku, zero zmiany w logice — ale nazwa jest zaszyta w kodzie (`report.py::STORE`, `structural_pipeline.py::main`) i w czterech miejscach dokumentacji (`README.md`, `docs/prd.md`, `docs/stages/03-storage-analysis.md`, ten plik). Każda przyszła zmiana nazwy zaufanego pliku wymaga tego samego przeglądu — łatwo przeoczyć jedno miejsce (`grep -rn structural.ndjson` przed uznaniem zmiany za skończoną).

**Pułapki:** (1) `report.py` zapisuje raport zawsze pod tą samą nazwą dnia (`<data>-trendy.md`) niezależnie od trybu — uruchomienie najpierw z kandydatem, potem bez argumentu (np. z przyzwyczajenia) nadpisze plik raportu starą, sprzed-scalenia wersją zaufanego magazynu; kolejność w README (krok 6 przed 8) ma znaczenie. (2) stare migawki nie są sprzątane automatycznie — koszt niski (`data/` lokalnie, gitignored), ale przy długim używaniu warto kiedyś dodać retencję, nie zrobione dziś, bo przedwczesne.

### Weryfikacja magazynu względem OCR (bez PDF-ów) — dwa realne błędy w 200 rekordach

**Decyzja:** zamiast otwierać surowe PDF-y (nowa kategoria ekspozycji PII, odrzucona przez operatora — patrz rozmowa), zweryfikowano wszystkie 200 rekordów zaufanego magazynu względem już posiadanych plików OCR (`data/interim/structural-ocr/*.md`). Automatyczny pierwszy przebieg (czy liczba występuje GDZIEKOLWIEK w dokumencie) dał 0 trafień — za słaby test, nie sprawdzał bliskości do markera. Drugi przebieg (bliskość do nazwy markera, oknem ~20 linii) dał 25 kandydatów, z czego 22 okazały się fałszywymi alarmami własnego skryptu (zbyt restrykcyjny limit długości linii odrzucał poprawne kotwice w mocno wypełnionych spacjami wierszach tabel) — potwierdzone ręcznie w źródle. Zostały 2 realne błędy.

**Błąd 1 — kolumna „jednostka" łapie zduplikowany wynik zamiast `None`:** dokument `Badanie_lekarskie_286035426` (kał) ma nietypową 5-kolumnową tabelę, gdzie kolumna 2 (normalnie „jednostka") czasem powtarza dokładnie tekst z kolumny 1 („wynik") — np. `Barwa | brązowa | brązowa | ...`. Parser traktował ten duplikat jak prawdziwą jednostkę (`canon_unit()` bez trafienia w słowniku zwraca surowy tekst). Dla wyników jakościowych (`stool_color`, `stool_consistency`) błąd był niewidoczny w raporcie (unit-suffix renderuje się tylko przy realnej wartości liczbowej w serii), ale dla `stool_ph` (Odczyn, wartość liczbowa 6,0) był **widoczny**: `unit="6,0"` dawało w raporcie coś w stylu „6 6,0". Naprawa: gdy `cell2 == cells[1]` (dokładny duplikat), traktuj kolumnę jednostki jako pustą.

**Błąd 2 — zakres referencyjny gubi się przy dopisku labu:** dokument `188572094` ma komórki zakresu z doklejonym tekstem „(Parametr nieakredytowany)” (przed albo po liczbach) — np. „0,00 - 0,01 (Parametr nieakredytowany)” albo „(Parametr nieakredytowany) 0,1 - 0,8”. `_RANGE_CELL` wymaga, żeby CAŁA komórka była tylko liczbami z myślnikiem — dopisek łamał dopasowanie, zakres znikał całkowicie (nie trafiał nawet do `reference_note`, bo ten mechanizm łapie tylko linie zaczynające się od symbolu porównania). Naprawa: `_range_from_cell()` usuwa dowolny fragment w nawiasie przed próbą dopasowania zakresu — 3 rekordy (NRBC x10³/µl, IG %, NRBC %) odzyskały swoje zakresy.

**Jak działa (metoda, nie tylko wynik):** oba błędy znaleziono metodą „napisz szybki automatyczny test, potem NIE UFAJ mu ślepo — sprawdź każdy wynik ręcznie w źródle, zanim uznasz go za prawdziwy problem albo za czysty wynik”. Test dał 25 kandydatów z 92% fałszywych alarmów — gdyby przyjąć go bezkrytycznie, powstałaby fałszywa lista 25 „błędów” zamiast prawdziwej listy 2.

**Pułapki:** żaden z tych dwóch błędów nie został znaleziony wcześniejszymi automatycznymi checkami (S1: „0 nieznanych markerów”, grep po „None”) — oba dotyczyły poprawnie rozpoznanego markera z cichym, częściowym uszkodzeniem pola. To ta sama lekcja co przy poprzednich audytach: automatyczne checki na poziomie „czy rekord istnieje” nie łapią błędów na poziomie „czy pole w rekordzie jest poprawne”.
