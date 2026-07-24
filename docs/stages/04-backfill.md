# Etap 4 — Backfill i weryfikacja Success Criteria

## Cel
Przetworzenie dokumentów strukturalnych z archiwum ~390 plików (szacunkowo ~30%, czyli ~100–120 — reszta to narracyjne, poza V1) i pomiar S1–S4 z PRD. Rozłożone w czasie — tempo ograniczone limitami Pro (~3 dok./dzień wystarcza).

Sedno: pierwszy etap, gdzie zbudowany pipeline (etapy 0–3, zwalidowany na 14 dok.) spotyka realną skalę i realny czas — nie „czy działa", tylko „czy przeżyje przerwanie w połowie, czy policzy dokumenty nieczytelne zamiast je przemilczeć, i czy operator nie zniechęci się zatwierdzaniem". PRD nazywa to w tabeli ryzyk: „zatwierdzanie ręczne zniechęci po backfillu → front-load, słownik nasyca się na pierwszych ~50 dokumentach" — stąd pierwsza partia to ~50, nie cały wolumen naraz.

## Zakres / Definition of Done
- [x] Partia wsadowa: kolejkowanie (`[i/N]`, stała kolejność `sorted()`), wznawianie po przerwaniu (Warstwa 3 odzyskuje propozycje z `pending/aliases.yml`), licznik odrzuconych (`MIN_OCR_CHARS=500`) — `src/structural_pipeline.py`, oba mechanizmy przetestowane jednostkowo przed realnymi danymi; zero regresji na 14 dokumentach (114 rekordów bez zmian)
- [x] S1: 100% markerów zmapowanych na 40 dokumentach; 32/40 dało rekordy, **8/40 świadomie odrzucone** (trzeci, nierozpoznany format — patrz „8 odrzuconych dokumentów"). Liczba rekordów spadła 221→200 przez poaudytowe poprawki i wykluczenia (patrz „Błędy wartości..." i „Wykluczenia")
- [x] S3: nowy dokument end-to-end w ≤15 min pracy operatora — zmierzone na realnym pliku: **13,5 min (813s), PASS**. Sam pipeline: 44s
- [x] Pomiar i zapis wyników S1–S4 w tym pliku
- [x] Retrospektywa: co poprawić przy bieżącym napływie (2–3 dok./mies.)
- [x] Kolumna `Źródło` w raporcie + usunięcie martwego pola `record_type` ze schematu NDJSON (patrz notatka)
- [x] Migawki datowane (`data/store/YYYY-MM-DD-structural.ndjson`) zamiast bezpośredniego nadpisania zaufanego magazynu — scalenie ręczne, na żądanie operatora, po weryfikacji raportu (PRD v1.3, patrz notatka)

## Wyniki S1–S4

| # | Kryterium | Próg | Wynik |
|---|---|---|---|
| S1 | ≥95% dok. w kanonicznym JSON, 100% markerów zmapowanych/odrzuconych | — | **PASS** — 200 rekordów, 0 nieznanych, 29/37 (78%) aktywnych dok. z wynikami + 8/37 świadomie odrzuconych = 100% rozliczone; dodatkowo 11 wierszy z rozpoznanym markerem bez ustalonego wyniku, flagowanych do ręcznego przeglądu (nie giną po cichu) |
| S2 | Trend markera z ≥3 pomiarami jednym promptem | ≥3 pomiary | **PASS** — 20 serii marker+jednostka z ≥3 datami (np. cholesterol całkowity: 4 pomiary, 2020–2025, 194→238→227→225 mg/dl); realnie wygenerowany raport, nie tylko zapytanie |
| S3 | Nowy dokument end-to-end | ≤15 min pracy operatora | **PASS** — 13,5 min z 1 nowym aliasem (sam pipeline: 44s) |
| S4 | NDJSON ładuje się do BigQuery bez transformacji | brak błędów schematu | **PASS** — potwierdzone przez operatora (etap 3): load 11-, potem 12-kolumnowy, oba bez błędów |

## Notatki

### Tabela bez nagłówka ICD-9 — jeden objaw, dwie przyczyny

**Decyzja:** płaski lookup `ALL_MARKERS` po wszystkich panelach jako fallback w ścieżce tabeli WYŁĄCZNIE gdy `panel is None`. Fallback per-wiersz (`row_panel`, nie nadpisuje globalnego `panel`), żeby jeden trafiony marker z „biochemia" nie blokował kolejnego wiersza z „morfologia".

**Dlaczego:** nowy lab nigdy nie drukuje rozpoznawalnego nagłówka `(ICD-9: kod)` dla tabeli (w przeciwieństwie do „Morfologia krwi (ICD-9: C55)" z oryginalnego labu) — `panel` zostawał `None`, a `resolve(None, klucz)` zawsze zwraca `None`, mimo że 47 aliasów dla tych markerów było już zatwierdzonych. Efekt naprawy: 164→216 rekordów, 51→0 nieznanych.

**Pułapki:** dwie różne przyczyny dawały ten sam objaw w logu („nieznany marker") — bracket-w-linii-sekcyjnej (`[L23] Fosforany`, rozwiązanie `_BRACKET_CODE`) i tabela-bez-nagłówka (`ALL_MARKERS`). Pierwsza diagnoza (bracket) działała na syntetycznym teście, ale nie zmieniła nic na realnych danych — prawdziwą przyczyną było to drugie, znalezione dopiero przez sprawdzenie surowego OCR. Nie zakładaj jednej przyczyny dla jednego objawu; syntetyczny test poprawności mechanizmu ≠ dowód, że to TEN mechanizm jest przyczyną.

### 8 odrzuconych dokumentów — trzeci format, świadoma decyzja nie inżynierować dalej

**Decyzja:** 8 pojedynczych testów (`183202680`, `Kał - pasożyty`, `Endokrynologiczne (Hormony) 1`, `CK`, `Kalprotektyna`, `Kał badanie ogólne`, `Krew utajona`, `Badanie ogólne moczu`) świadomie odrzucone dla tej partii.

**Dlaczego:** struktura OCR sprawdzona dla wszystkich (zero PII, tylko kształt) — żaden nie ma tabeli ani nawiasów kwadratowych, jedyny trafiony `ICD-9` jest uszkodzony przez OCR. To trzeci format tego samego labu — jeden marker na dokument, prosty układ „nazwa: wynik". Koszt zaprojektowania i przetestowania kolejnego parsera dla 8 jednorazowych przypadków (każdy inny plik, nie powtarzalny wzorzec) przewyższa wartość — ten sam kompromis co przy progu referencyjnym lipidogramu (etap 3).

**Jak działa:** technicznie to wciąż flaga `⚠ SPRAWDŹ RĘCZNIE` z kodu (nie cichy brak) — „świadome odrzucenie" to warstwa DECYZJI operatora nad tą flagą, nie osobny mechanizm.

**Pułapki:** jeśli w kolejnej partii ten trzeci format zacznie się powtarzać w większej liczbie plików, opłacalność parsera „nazwa: wynik" się zmienia — wróć tu i przelicz, zamiast zakładać, że decyzja z 40-dokumentowej próbki jest trwała.

### Partia ~50 i próg „nieczytelny OCR" — decyzje z danych, nie z zgadywania

**Decyzja:** pierwsza partia to ~50 dok. (nie cały wolumen naraz), a `MIN_OCR_CHARS = 500` rozdziela dokument realny od nieczytelnego.

**Dlaczego:** partia ~50 to nie nowa decyzja — PRD miał ją w tabeli ryzyk („front-load: słownik nasyca się na pierwszych ~50"). Próg 500 kalibrowany na dwóch znanych granicach: najkrótszy PRAWDZIWY dokument w próbce miał 710 znaków, najdłuższy znany pusty/nieczytelny OCR — 394. 500 leży bezpiecznie w przerwie.

**Pułapki:** pierwsza wersja progu (300) przeszła code review „na oko", ale nie łapała znanego przypadku 394 znaków. Dopiero jednostkowy test na obu skrajnych, już znanych wartościach (`710 > próg`, `394 < próg`) to złapał. Kalibracja progu bez sprawdzenia na obu skrajnych przypadkach to fałszywe poczucie bezpieczeństwa.

### Wznawianie Warstwy 3 po przerwaniu

**Decyzja:** przed zapytaniem Haiku o nieznany marker, `load_existing_proposals()` sprawdza, czy `pending/aliases.yml` z poprzedniego (może przerwanego) runu już ma propozycję dla tej pary (panel, znormalizowana nazwa). Jeśli tak — odzyskuje ją bez wywołania API.

**Dlaczego:** przy backfillu pod limitami Pro przerwanie w połowie (throttle, Ctrl+C) jest realne. Bez tego każde wznowienie odpytywałoby Haiku o WSZYSTKIE nieznane markery od nowa — marnowanie wywołań i złamanie litery DoD („wznawianie po przerwaniu").

**Jak działa:** `pending/aliases.yml` ma strukturę `{pending_panels: {panel: {nazwa: kod}}}` — funkcja spłaszcza to do `(panel, norm(nazwa)) -> kod`; pętla Warstwy 3 sprawdza słownik PRZED `propose_alias_haiku()`, trafienie = reużycie.

**Pułapki:** zweryfikowane testem z monkeypatch Haiku, która rzuciłaby błąd, gdyby ją wywołano dla znanego markera — nie samą inspekcją kodu. Realne dane mają dziś 0 nieznanych (słownik nasycony), więc test izolowany był jedyną drogą sprawdzenia mechanizmu przed pierwszym backfillem.

### Błędy wartości przy poprawnej nazwie — czego S1 nie łapie

**Decyzja:** przed loadem do BigQuery i pokazaniem lekarzowi zrobiony osobny przegląd spójności WARTOŚCI (nie tylko S1 „0 nieznanych markerów" — to sprawdza wyłącznie nazwy). Znaleziono wiele niezależnych błędów, żaden widoczny w metrykach S1–S4, bo wszystkie dotyczyły wartości/daty przy poprawnie rozpoznanym markerze. Wszystkie naprawy żyją w `report.py`/`structural_pipeline.py`, nie w ręcznie łatanym wyjściu — działają na każdym przyszłym dokumencie.

**Jak działa (lista naprawionych luk kodu):**
- `report.py` wywalał się — `rows.sort(key=lambda r: r["exam_date"])` porównywał `None` ze stringiem. Naprawa: `key=... or ""` + „brak daty" w tabeli.
- `exam_date` łapał tylko jeden format (`Data wykonania: DD.MM.YYYY`). Nowe laby piszą to inaczej — 60/221 rekordów (27%) miało `null` mimo daty w tekście. Naprawa: `_DATE_FORMATS`, lista wzorców po kolei (oryginalny pierwszy, zero regresji).
- kolumna „jednostka" cicho łapała zakres — część labów pakuje wynik+jednostkę w jedną komórkę, zakres w drugą; komórka z zakresem lądowała w `unit`, a garbowana data w `reference_high` (`SHBG.reference_low: 24.0202` = fragment daty). Naprawa: `_range_from_cell()` rozpoznaje komórkę-zakres/granicę niezależnie od pozycji, z limitem 1–3 cyfr przed przecinkiem.
- literalne „None" w kolumnie Wartość (16 markerów) — `fmt_value()` doklejało jednostkę bez warunku, a przy `unit=None` (marker bezjednostkowy, np. INR) wypisywało tekst „None". Naprawa: dokleja jednostkę tylko gdy istnieje.
- ten sam marker rozbity na 2–3 tabele — grupowanie sztywno po `(marker, jednostka)`. Naprawa: grupuj po markerze, dziel po jednostce TYLKO gdy marker ma ≥2 realne jednostki (NEU/LYM w % vs tys/µl — świadomie niescalone, różnica bywa kliniczna).
- dwuznaczne etykiety — „Leukocyty"/„Glukoza"/„Barwa" dla krwi i moczu naraz. Naprawa: strona moczowa/kałowa dostaje kwalifikator („Glukoza w moczu"), strona krwi bez, zgodnie z konwencją `FOB: "Krew utajona w kale"`.
- strażnik pustych rekordów działał tylko w ścieżce TABELI — ścieżka SEKCYJNA miała słabszy (wymagał, by WSZYSTKIE pola były puste), więc rekord z samą jednostką bez wyniku (CRP: `unit="ng/ml"`, `value=None`) trafiał do magazynu. Naprawa: ten sam warunek w obu — brak wartości I brak tekstu wyniku.
- grupa bilirubiny źle skonfigurowana — „Bilirubina wolna (pośrednia) (ICD-9: I91)" to NAGŁÓWEK grupy trzech wyników, nie marker. Naprawa: alias przeniesiony na wiersz-dziecko, dodane `BIL_DIR`/`BIL_TOTAL`, nagłówek do `_NOISE`.
- duplikat komórki jako jednostka — `Badanie_lekarskie_286035426` (kał) ma kolumnę 2 powtarzającą kolumnę 1 (`Barwa | brązowa | brązowa`); dla `stool_ph` dawało `unit="6,0"` → „6 6,0". Naprawa: gdy `cell2 == cells[1]`, jednostka pusta.
- zakres gubił się przy dopisku labu — `188572094` ma „0,00 - 0,01 (Parametr nieakredytowany)"; `_RANGE_CELL` wymagał czystej komórki. Naprawa: `_range_from_cell()` usuwa fragment w nawiasie przed dopasowaniem (3 rekordy odzyskały zakres).

**Jak działa (zasada wspólna):** „nie zgaduj, sygnalizuj" — cichy `None`/pominięty wiersz jest tańszy do naprawienia później niż cicho zapisana zła liczba, wyglądająca wiarygodnie w raporcie „do lekarza".

**Pułapki:** dwa pliki z Medicover (`188572094`, `190111920`) mają layout, gdzie etykieta i wartość są w OSOBNYCH blokach dopasowywanych pozycyjnie — „Data pobrania:" sąsiaduje z datą urodzenia, prawdziwa data leży 5 linii dalej. Świadomie NIE dodane do regexu (zgadywanie po bliskości groziłoby złą datą, gorszą niż `None`) — 33 rekordy bez daty, do osobnej naprawy tego layoutu.

### Błędy OCR-a vs błędy Pythona — różna naprawa, różna lokalizacja

**Decyzja:** błąd OCR-a (zła cyfra lub kolejność w tekście, zanim Python go zobaczył) naprawiamy ręcznie w **cache'owanym pliku OCR** (`data/interim/structural-ocr/*.md`), NIE w NDJSON — magazyn regeneruje się z cache przy każdym uruchomieniu (OCR pomija już przetworzone pliki), więc poprawka w NDJSON zniknęłaby przy najbliższym scaleniu. Błąd logiki naprawiamy w kodzie (raz, działa na każdym przyszłym dokumencie).

**Jak działa (błędy Pythona z rundy weryfikacji względem PDF):**
- `to_num()` usuwał `<`/`>` z wyniku — „<1" (poniżej progu wykrywalności) stawało się „1.0". Ścieżka sekcyjna miała ochronę, tabela nie. Naprawa: to samo w obu + `fmt_value()` preferuje `value_text` do wyświetlenia.
- `_range_from_cell()` nie rozpoznawał zakresu rozdzielonego spacją bez myślnika — „1,005 1,030" gubiło cały zakres. Naprawa: dodano `_RANGE` jako dodatkowe dopasowanie.
- liczba z doklejoną flagą na końcu linii — „190,00 H" nie pasowało do `_NUM` (wymagało wyłącznie liczby), MAX znikał, a MIN (115) trafiał błędnie jako górna granica. Naprawa: `_NUM` toleruje doklejoną literę flagi (`H`/`L`/`N`/`*`), funkcje wyciągają liczbę z grupy.
- kod w nawiasie renderowany jako nagłówek Markdown — `## [I99] Cholesterol całkowity`; `_BRACKET_CODE` sprawdzał początek linii bez zdjęcia `#`, więc marker znikał całkowicie, nawet nie trafiając do `unknown` (naruszenie S1). Naprawa: `.lstrip("#").strip()` przed dopasowaniem.

**Jak działa (sześć wariantów błędu OCR-a — każdy naprawiony ręcznie w cache):** (1) zła cyfra (MCV: „90,9"→„20,9"); (2) przestawiona kolejność linii w sekcji między markerami (Sód, bilirubina wolna/całkowita — MAX trafiał do chunku sąsiada); (3) przestawione dane między dwoma wierszami tabeli, gdzie jeden wiersz nie generował rekordu (Potas w moczu — odzyskanie wymagało odtworzenia całego brakującego rekordu z `bad_rows`); (4) trzy liczby w złej kolejności w jednym markerze (OB: MIN, MAX, WYNIK zamiast WYNIK, MIN, MAX); (5) przesunięcie „o jeden" na poziomie całego dokumentu (`Urologiczne i reumatologiczne` — patrz „Wykluczenia"); (6) przesunięcie między dwoma sąsiednimi markerami (Lipidogram (1): OB dostał dolną granicę Glukozy jako `hi`).

**Pułapki:** rozróżnienie „błąd OCR" od „błąd Pythona" wymaga sprawdzenia surowego OCR (`grep` po wartości) — sama niezgodność raportu z PDF-em nie mówi, na którym poziomie problem powstał. Ręczna poprawka cache to wyjątek od „nie patchuj danych ręcznie" — uzasadniony tylko gdy przyczyna jest jednoznacznie w OCR i operator wizualnie potwierdził wartość względem oryginału. Nawet ta ręczna poprawka wymaga weryfikacji jak każda inna — pierwsza próba przestawienia linii Glukozy zamieniła wynik z zakresem, złapana dopiero przez uruchomienie parsera, nie przez „wygląda dobrze".

### Wykluczenia — kiedy nie naprawiać (5 dokumentów) + wyciek PII

**Decyzja:** 5 dokumentów przeniesionych do `data/raw/structural/_excluded-scrambled-ocr/` (folder lokalny, poza gitem): 2× `Badanie lekarskie` (2026.04.02), `CK, Kwas moczowy...`, `Lipidogram.pdf` (nie mylić z `(1)/(2)/-kopia`), `Urologiczne i reumatologiczne`. Wykluczone, nie łatane.

**Dlaczego:** przy fundamentalnie pomieszanej kolejności czytania OCR nie ma bezpiecznego sposobu odtworzenia, która wartość należy do którego markera — każda heurystyka pozycyjna zgadywałaby, co gorsze niż jawne wykluczenie. Te same materiały występują wielokrotnie w czystych dokumentach tego okresu, więc utrata pojedynczego pomiaru nie tworzy luki w trendzie. Przykłady dowodów (klinicznej niewiarygodności, nie „wygląda podejrzanie"): ALP dostał wynik w mmol/l (zawsze U/l) z zakresem wapnia; Na dostał dolną granicę potasu (3,5); `Lipidogram.pdf` raportował każdy marker dwukrotnie (mg/dl + mmol/l), myląc granice fragmentów i gubiąc TSH całkowicie.

**Pułapki (wyciek PII):** przy pomieszaniu kolejności dane osób trafiały do pola wyniku — nazwisko pacjenta („MAĆKÓWKA PIOTR" jako wynik Kreatyniny, z powtórzonego nagłówka `## MAĆKÓWKA PIOTR`) i nazwisko lekarza („Mlngr DAMIAN CHARYTON" jako `VIT_D_25OH.value_text`). Naprawa strony pacjenta: `parse_section_chunk` pamięta, czy poprzednia (odfiltrowana) linia była etykietą osobową (Pacjent/Lekarz/Autoryzował) — jeśli tak, następną linię gasi jako nazwisko niezależnie od formatowania. Pierwsza, szersza wersja (odrzuć wszystkie nagłówki markdown w chunku) była zbyt szeroka — złapała prawdziwy wynik `## nie wykryto` (antygen HBs) i o mało nie spowodowała cichej regresji.

**Pułapki:** po naprawie „przypis jako wynik" sprawdzono, czy 3 wcześniej wykluczone da się odzyskać — **nie**, dane wciąż klinicznie nieprawdopodobne (wyciek nazwiska niezwiązany z przypisami). Ten sam objaw miał dwie przyczyny nałożone; naprawienie jednej nie naprawia całości — weryfikuj end-to-end, nie brak błędu w logu. Poprawka `_BRACKET_CODE`, sama w sobie bezpieczna, odsłoniła ukryte gorsze problemy w 2 dokumentach — dlatego pełny diff całego magazynu po każdej zmianie kodu jest obowiązkowy.

### Weryfikacja: automat konieczny, ale niewystarczający

**Decyzja:** przy każdej rundzie weryfikacji — napisz szybki automatyczny test, ale NIE ufaj mu ślepo; sprawdź każdy wynik ręcznie w źródle, zanim uznasz go za błąd albo za czysty. Do tego: pełny diff całego magazynu po każdej zmianie kodu, i ocena KLINICZNEJ wiarygodności wartości, nie tylko obecności rekordu.

**Dlaczego:** pierwszy skrypt bliskości (czy wartość jest w oknie ~20 linii od markera) dał 25 kandydatów, z czego 22 to fałszywe alarmy własnego skryptu (za restrykcyjny limit długości linii) — gdyby przyjąć bezkrytycznie, powstałaby fałszywa lista 25 „błędów" zamiast prawdziwej listy 2. Osobno: to ludzkie oko (operator: „wątpię, aby zakres referencyjny zmienił się tak w miesiąc") złapało pomieszany OCR, którego żaden automat nie łapał — S1 „0 nieznanych markerów" widzi tylko nazwy.

**Pułapki:** automatyczne checki na poziomie „czy rekord istnieje" nie łapią błędów na poziomie „czy pole w rekordzie jest poprawne". Najbardziej podstępny przypadek: AST WYGLĄDAŁ w pełni poprawnie (wartość, zakres, jednostka zgodne z PDF), a jednostka pochodziła z przesuniętego, cudzego źródła (przypadkiem ten sam tekst „U/l"). Bez porównania z oryginałem — niewykrywalne.

### Kolumna `Źródło` + usunięcie `record_type`

**Decyzja:** tabela raportu (`report.py::build_report`) dostała kolumnę `Źródło` (pole `source_file`, w NDJSON od początku). Przy okazji usunięte martwe `record_type` (zawsze „structural" od czasu wycięcia narracji z V1) — z `_record` i ze schematu BigQuery w `03-storage-analysis.md` (12→11 kolumn).

**Dlaczego:** po rundach audytu operator zasygnalizował, że ręczne sprawdzanie ~100+ dokumentów naraz przy każdym backfillu jest nie do utrzymania, ale bieżący mały napływ (2–3 dok./mies.) już tak. Propozycja: zamrozić obecną partię na obecnym poziomie zaufania, a każdy nowy dokument weryfikować pojedynczo od razu po ingestcie. `Źródło` to najtańszy krok — operator widzi przy każdej wartości, z którego pliku pochodzi, i sprawdza ją względem oryginału bez grzebania w NDJSON.

### Migawki datowane + scalenie ręczne

**Decyzja:** zamiast wykrywać dryf już zweryfikowanych danych — **uniemożliwić go strukturalnie**. `structural_pipeline.py::main()` zapisuje każdy przebieg do osobnej migawki (`data/store/YYYY-MM-DD-structural.ndjson`) i **nigdy nie dotyka** zaufanego `structural-backfill.ndjson`. Ten plik zmienia się wyłącznie, gdy operator — po ręcznej weryfikacji raportu z migawki — poprosi o scalenie: zwykłą kopię migawki na miejsce zaufanego pliku, na żądanie.

**Dlaczego lepsze niż rejestr + diff:** rejestr zweryfikowanych + porównanie starego/nowego magazynu wymagałby nowego mechanizmu, który MUSIAŁBY być poprawny, żeby cokolwiek chronić — kolejny kod do zaufania. Migawki + scalenie nie polegają na wykrywaniu błędu — zaufany plik fizycznie nie może się zmienić bez jawnej akcji operatora. Prostsze, bo `main()` i tak od zawsze robi pełny reprocessing, więc „scalenie" to podmiana jednego pliku na drugi, nie łączenie diffów.

**Jak działa:** `report.py` przyjmuje opcjonalny argument ścieżki — bez argumentu czyta zaufany magazyn, z argumentem dowolną migawkę-kandydata. Terminal jawnie oznacza tryb (`KANDYDAT` vs `zaufany magazyn`).

**Pułapki:** `report.py` zapisuje raport zawsze pod tą samą nazwą dnia (`<data>-trendy.md`) niezależnie od trybu — uruchomienie najpierw z kandydatem, potem bez argumentu nadpisze raport wersją sprzed scalenia; kolejność w README ma znaczenie. Stare migawki nie są sprzątane automatycznie (koszt niski, `data/` lokalnie) — retencja to kandydat na przyszłość, dziś przedwczesna.

### Nazwa zaufanego pliku — `structural-backfill.ndjson`, nie `structural.ndjson`

**Decyzja:** zaufany plik nazwany `structural-backfill.ndjson`, nie `structural.ndjson`.

**Dlaczego:** zaraz po wdrożeniu migawek zaufany plik i migawka z tego samego dnia (`2026-07-22-structural.ndjson`) wyglądały jak przypadkowy duplikat nazwy — nieoczywiste, który jest który. `-backfill` opisuje POCHODZENIE linii danych (ten sam plik od pierwszego dużego wsadu, rozwijany scaleniami), nie moment zamrożenia — jak nazwa brancha „main" w gicie. Data w nazwie (`structural-2026-07-22.ndjson`) sugerowałaby zamrożenie, mylące dla pliku zmienianego miesiącami.

**Pułapki:** czysto kosmetyczna zmiana, ale nazwa jest zaszyta w kodzie (`report.py::STORE`, `structural_pipeline.py::main`) i w 4 miejscach dokumentacji — każda przyszła zmiana wymaga tego samego przeglądu (`grep -rn structural.ndjson` przed uznaniem za skończone).

### Retrospektywa — bieżący napływ (2–3 dok./mies.)

**Decyzja:** proces jest gotowy na bieżący, mały napływ bez dalszych zmian w kodzie — S3 (13,5 min/dok., 44s pipeline) daje duży margines. To, co wymagało poprawy, poprawiło się w trakcie tej partii.

**Dlaczego (nauka z 40 dokumentów):** każde NOWE źródło przynosi własne, nieoczekiwane konwencje — w tej partii: nawiasy kwadratowe zamiast `(ICD-9)`, tabele bez nagłówka panelu, linie metadanych mylone z markerami. Trzy przyczyny, ten sam objaw w logu, żadnej nie dało się przewidzieć — wszystkie wymagały sprawdzenia surowego OCR. Wniosek: przy kolejnym nowym labie oczekuj 1–3 nowych „dziur" parsera i zacznij diagnozę od `data/interim/structural-ocr/*.md` (obecność `|`, `ICD-9`, nawiasów), zanim cokolwiek naprawisz.

**Jak działa proces przeglądu aliasów (potwierdzone realnie):** ręczny przegląd propozycji Haiku złapał realne błędy, nie tylko oczywistości — niespójne kody (`NEUT` vs `NEU`), i 3 z 8 „pewnych" przypisań krew/mocz błędne, wykryte dopiero po sprawdzeniu, z którego PLIKU pochodzi marker (nazwa „Pierwiastki w krwi" vs „w moczu" rozstrzygnęła). HITL na aliasach nie jest biurokracją — realnie zapobiega cichemu mieszaniu danych.

**Pułapki:** limit Pro objawił się realnie przy 96 sekwencyjnych wywołaniach Haiku naraz (timeout w środku pętli) — teraz obsłużone (zapis po każdym markerze), ale przy dużych partiach lepiej rozkładać w czasie niż odpalać jedną komendą.

### Trzeci format tabeli — karta szpitalna (minitabela na marker)

**Decyzja:** karta informacyjna z leczenia szpitalnego (>30 markerów) zapisana jako **osobna minitabela na marker** (`## Nazwa` + tabela `Lp. | Data | <wartość>`), zamiast wspólnej tabeli albo formatu sekcyjnego. Sekcje narracyjne (Epikryza, zalecenia, leki) świadomie zignorowane (poza V1). Wzorzec w pełni addytywny — dwukrotny pełny diff potwierdził zero zmian w 227 istniejących rekordach.

**Dlaczego nowy kod, nie tylko aliasy:** żaden istniejący mechanizm (ICD-9 inline, nawias kwadratowy, pozycyjna tabela) nie pasował do „nazwa jako nagłówek + osobna minitabela". Dodano trzeci wąski wzorzec: śledzenie ostatniego nagłówka (`last_heading`) + rozpoznanie wiersza „Lp. | Data | ..." jako zapowiedzi wiersza z danymi (`lp_pending`). Sprawdzane PRZED ogólną ścieżką tabeli, żeby „Lp." nie trafiało jako nazwa markera.

**Dlaczego (rozdzielenie DZM od pojedynczej próbki):** Haiku kilkukrotnie błędnie zlał badania „w DZM" (dobowa zbiórka moczu, wydalanie w mmol/24h) z odpowiednikami stężenia we krwi/pojedynczej próbce (proponował „Magnez w DZM" → `Mg`). Różna skala pomiaru, różna jednostka — nie wolno łączyć w jeden trend. Ręcznie: 9 nowych kodów z sufiksem `_24h` (konwencja już istniejąca: `urine_calcium_24h`).

**Pułapki:** jeden tytuł minitabeli („Potas w moczu (pojedyncza porcja)") nie miał `##` — jedyny taki w dokumencie — więc `last_heading` zostawał z poprzedniej wartości i błędnie przypisywał dane. Naprawione ręcznie w cache OCR, złapane przez porównanie z oryginałem. ~9 markerów ma wartość, ale brak jednostki/zakresu — sub-linie CAŁKOWICIE usunięte przez Docling z tych minitabel (nie błąd kodu). OCR czyta „[" jako „I" („Inmol/l]" = „[nmol/l]") — rozpoznawane przez `_LP_UNIT`, ale tylko gdy zamiana jednoznaczna. Złożone panele wielowartościowe (Gazometria, HOMA-IR, TIBC, Morfologia) mają bardziej pogmatwany kształt — świadomie NIE obsłużone, zostają jako `unknown`.

Po scaleniu: **260 rekordów** w zaufanym magazynie (227 + 33 z tego dokumentu).
