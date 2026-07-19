# Etap 4 — Anonimizacja (Presidio)

## Cel
Warstwa pseudonimizacji: brama prywatności, przez którą przechodzi każdy tekst dokumentu, zanim trafi do zewnętrznego API (reguła twarda z PRD — nic wcześniej). Wejściem jest OCR-owany markdown opisu (etap 1), wyjściem ten sam tekst z PII zamienionym na spójne tokeny (`JAN KOWALSKI` → `PERSON_001`, adres → `ADDRESS_001`, PESEL → `PESEL_001`), gotowy do ekstrakcji LLM w etapie 5. Cel edukacyjny: Privacy Engineering.

Wykrywanie idzie w trzech komplementarnych warstwach, bo żadna sama nie wystarcza (wniosek z pomiaru recall): **NER** (spaCy `pl_core_news_lg` jako silnik NLP Presidio) generalizuje nazwiska i miejsca; **recognizery wzorcowe** łapią to, co ma stały kształt niezależny od pacjenta — PESEL z walidacją sumy kontrolnej, telefon (region PL dograny jawnie), kod pocztowy; **deny-lista** (`data/pending/known_pii_denylist.yml`, exact-match, PII, gitignored, utrzymywana ręcznie przez operatora) domyka stałe wartości jednego użytkownika V1, których NER nie łapie niezawodnie. Pseudonimizacja jest spójna w obrębie dokumentu — ta sama wartość zawsze dostaje ten sam token. Prywatność jest tu klasy higienicznej, nie medycznej: PESEL i nazwisko trzymają się mocno, adres słabiej — ale to, co przecieka, to głównie gołe liczby (nr domu), których nie wolno redagować, bo nadpisałyby pomiary medyczne (PRD: produkt > prywatność miękka).

## Zakres / Definition of Done
- [x] Presidio z polskim NLP engine (spaCy `pl_core_news_lg`) — `src/anonymize.py`, `_build_analyzer()`
- [x] Encje: nazwiska (PERSON), adresy (LOCATION), telefony (PHONE_NUMBER, region PL dodany jawnie), PESEL (`PlPeselRecognizer` — wbudowany, walidacja sumy kontrolnej), e-mail (EMAIL_ADDRESS)
- [x] Pseudonimizacja spójna (ta sama wartość, case-insensitive → ten sam token w obrębie dokumentu) — zweryfikowana testem syntetycznym (`Jan Kowalski` → `PERSON_001` przy obu wystąpieniach)
- [x] Test jakości na próbce 5 realnych dokumentów (etap 2) — adresy PACJENTA (najbardziej wrażliwe) potwierdzone jako słabo wykrywane, patrz niżej
- [x] Pomiar recall na złotym zbiorze z etapu 2 (deny-lista wypełniona realnymi danymi pacjenta): **PESEL 100% (5/5), telefon 80% (4/5), nazwiska 80% (20/25), LOCATION łącznie 47% (21/45) — rozbite: adres placówki 57% (16/28) vs adres PACJENTA 29% (5/17)**. Metoda: `src/anonymize.py::score_document` — jednostka = słowo/liczba (≥2 znaki) ze złotej wartości, "zredagowana" = nie występuje w znormalizowanym wyjściu. Pozostałe 5/25 PERSON to nazwiska LEKARZY (zmienne per dokument → to zadanie NER-a, nie deny-listy — sufit deny-listy dla PERSON osiągnięty)
- [x] Adresy/nazwiska wykrywane słabo → **custom recognizer** (`PlAddressRecognizer`: kod pocztowy + wzorzec `ul./al./pl. Nazwa nr`, bez PII w kodzie) + **deny-lista** (`data/pending/known_pii_denylist.yml`, exact-match, PII, gitignored, wypełnia operator). Nazwisko domknięte (60%→80%). Adres pacjenta został na 29% — ale to metryka-straszak: z 12 przeciekających tokenów **6 to gołe liczby** (nr domu/mieszkania — NIE wolno blanket-redagować, nadpisałyby pomiary medyczne), **4 to pospolite słowa** (`Warszawa`/`lok`), **tylko 2 realnie identyfikują**. Nazwa ulicy i kod pocztowy SĄ redagowane. Deny-lista na bezpiecznym suficie — dalsze podnoszenie recall wymagałoby redakcji liczb, co łamie priorytet PRD (produkt > prywatność miękka)

## Notatki
<!-- Grupuj po temacie, nie po dacie (chronologię trzyma git). Każdy podpunkt
     w OSOBNYM akapicie (pusta linia między nimi). Dla każdego tematu:

### <Temat / czego dotyczy>

**Decyzja:** co ustalono.

**Dlaczego:** uzasadnienie, trade-offy.

**Jak działa:** mechanizm narzędzia pod spodem — sedno nauki.

**Pułapki:** co zaskoczyło, na co uważać.

Nie każdy temat wymaga wszystkich czterech podpunktów. To notatki do nauki, nie log czynności. -->

### Etykiety NER modelu pl_core_news_lg — Presidio ich nie zna z pudełka

**Decyzja:** własny `model_to_presidio_entity_mapping` w konfiguracji NLP engine, mapujący etykiety modelu na standardowe encje Presidio.

**Dlaczego:** domyślna konfiguracja Presidio (`default.yaml`) zna angielskie etykiety spaCy (`PERSON`, `LOC`, `GPE`, `ORG`). `pl_core_news_lg` (korpus NKJP) używa zupełnie innych: `persName`, `geogName`, `placeName`, `orgName`, `date`, `time`. Bez własnego mappingu `SpacyRecognizer` dostaje trafienia z NER-a, ale żadne nie pasuje do żadnego klucza w słowniku — więc PERSON/LOCATION wychodzą z zerowym recall, mimo że model poprawnie widzi nazwiska i miejsca.

**Jak działa:** `NlpEngineProvider(nlp_configuration={...})` przyjmuje `ner_model_configuration.model_to_presidio_entity_mapping` jako słownik `etykieta_modelu -> encja_presidio`. To jedyne miejsce, w którym te dwa światy się łączą.

**Pułapki:** tego nie da się wyczytać z ogólnej dokumentacji Presidio (pisanej pod angielskie modele) — trzeba było odpalić `nlp.get_pipe("ner").labels` na konkretnym modelu i zobaczyć na oczy, że etykiety są inne. Reguła ogólna: przy integracji dwóch bibliotek NLP nie zakładaj wspólnego słownictwa etykiet, sprawdź.

### PhoneRecognizer domyślnie nie zna Polski

**Decyzja:** dodanie osobnej instancji `PhoneRecognizer(supported_regions=("PL",))` do rejestru.

**Dlaczego:** `PhoneRecognizer.DEFAULT_SUPPORTED_REGIONS = ("US", "UK", "DE", "FR", "IL", "IN", "CA", "BR")` — Polski tam nie ma. `load_predefined_recognizers(languages=["pl"])` ładuje `PhoneRecognizer`, ale z tą samą domyślną listą regionów, więc polski numer telefonu nie dostaje ani jednego trafienia, mimo że recognizer jest "załadowany".

**Jak działa:** pod spodem `python-phonenumbers` (`PhoneNumberMatcher`) próbuje dopasować numer do wzorca KAŻDEGO regionu z listy po kolei — trzeba dograć swój region do listy, nie podmieniać całego recognizera.

**Pułapki:** "recognizer jest w rejestrze" ≠ "recognizer coś znajdzie" — trzeba sprawdzić parametry konstruktora, nie tylko czy klasa jest załadowana. Wykryte to samo empirycznie (smoke test na syntetycznym numerze), nie z dokumentacji.

### Recall LOCATION: agregat kłamie, bo miesza dwa różne ryzyka

**Decyzja:** raportować adres pacjenta i adres placówki OSOBNO, nie jako jedną kategorię LOCATION.

**Dlaczego:** złoty zbiór ma dwa rodzaje adresu pod tą samą encją Presidio: `ADDRESS_001` (adres zamieszkania pacjenta — to jest ryzyko z PRD) i `FACILITY_*_ADDRESS` (adres placówki LUX MED — publiczny, ten sam we wszystkich dokumentach z tego źródła, właściwie nie jest PII). Zagregowany wynik LOCATION 44% wygląda znośnie, ale to prawie wyłącznie adres placówki (57%) — adres pacjenta zostaje na 24%, praktycznie bez poprawy po dodaniu custom recognizera. Gdybym zaraportował tylko agregat, wyglądałoby to na "wystarczająco dobre", a nie jest.

**Pułapki:** ten sam typ encji Presidio (`LOCATION`) potrafi kryć pod sobą dane o zupełnie różnej wrażliwości — przy każdym pomiarze recall trzeba pytać "recall CZEGO dokładnie", nie ufać jednej zagregowanej liczbie.

### Custom recognizer vs deny-lista — różne narzędzia do różnych słabości

**Decyzja:** `PlAddressRecognizer` (regex: kod pocztowy `\d{2}-\d{3}` + wzorzec `ul./al./pl. Nazwa nr`) jako recognizer ogólny w kodzie; `data/pending/known_pii_denylist.yml` (exact-match, PII, gitignored, wypełnia operator) jako deny-lista dla stałych wartości.

**Dlaczego:** to dwa różne przypadki. Regex nadaje się do WZORCÓW, które są takie same niezależnie od pacjenta (format kodu pocztowego, prefiks ulicy) — bezpieczny do trzymania w kodzie, bo nie zawiera niczyich danych. Deny-lista nadaje się do STAŁYCH WARTOŚCI, które są unikalne dla tego wdrożenia (imię i adres KONKRETNEGO pacjenta) — nie da się ich uogólnić regexem, i nie powinny nigdy trafić do kodu (wersjonowanego, potencjalnie publicznego repo). V1 = jeden użytkownik, więc te wartości są stałe w każdym dokumencie z tego samego źródła — deny-lista exact-match jest tu tańsza i pewniejsza niż poprawianie NER-a.

**Jak działa:** `_load_denylist_recognizers()` czyta YAML z `data/pending/`, buduje `PatternRecognizer` z `re.escape()` na każdej wartości (żeby np. kropka w "ul." nie działała jak wildcard), score 0.95. Plik z pustymi listami = zero efektu, pipeline działa identycznie jak bez niego (zweryfikowane).

**Pułapki:** deny-lista jest case-insensitive z automatu (Presidio ustawia globalnie `re.IGNORECASE | DOTALL | MULTILINE`) — warianty WIELKIE/małe litery to śmieć. Liczy się to, czego IGNORECASE nie ogarnia: kolejność słów (imię-nazwisko vs nazwisko-imię), interpunkcja skrótów (`lok.` vs `lok`), spacje (OCR rozdziela `11B` → `11 B`) i sam token nazwy ulicy. Konsekwencja dla etapu 5: `data/interim/narrative-anon/*.presidio.md` to artefakt z bieżącym stanem deny-listy — po każdej zmianie `known_pii_denylist.yml` odpalić `uv run python src/anonymize.py` ponownie.

### Więcej wariantów w deny-liście ≠ wyższy recall — trzeba wiedzieć CO przecieka

**Decyzja:** zatrzymać rozbudowę deny-listy adresu; residualny wyciek jest strukturalnie niebezpieczny do redakcji, nie brakiem wariantów.

**Dlaczego:** rozszerzenie deny-listy LOCATION z 6 do 14 wpisów (token ulicy, interpunkcja, spacje) podniosło recall adresu pacjenta o **dokładnie zero**. Diagnoza tokenowa (zamiast ufać jednej liczbie): z 12 przeciekających tokenów adresu 6 to gołe liczby (nr domu/mieszkania), 4 to pospolite słowa (`Warszawa`, `lok`), tylko 2 realnie identyfikują. Nazwa ulicy i kod pocztowy SĄ redagowane. „29% recall" jest pesymistyczne — liczy nr domu i miasto na równi z nazwiskiem. Domknięcie: LOCATION przycięte z powrotem 14 → **1 wpis** (sam bare token ulicy) przy recall bajt-w-bajt identycznym — dowód, że 13 wpisów było martwym balastem, bo formy strukturalne i kod pocztowy pokrywa już regex `PlAddressRecognizer`.

**Jak działa:** diagnostyka rozbija każdy token adresu na trzy kubełki: (a) nieobecny w surowym OCR — deny-lista nie ma czego łapać; (b) obecny w OCR, zniknął po anonimizacji — redakcja OK; (c) obecny w OCR, przeżył — realny leak. Dopiero (c), dalej rozbite na liczby/pospolite/identyfikujące, mówi czy jest co naprawiać. Wynik: identyfikujących leaków 2 na 4 dokumenty — szum, nie wzorzec.

**Pułapki:** blanket-redakcja gołych liczb (żeby złapać nr domu) nadpisałaby wartości pomiarów medycznych — czyli zniszczyła to, po co projekt istnieje. Koszt obliczeniowy dodania wariantów jest zerowy, ale koszt POPRAWNOŚCI nie: PRD stawia produkt (kompletność danych) nad prywatnością (miękką). Recall to zła pojedyncza metryka dla anonimizacji — bez rozbicia na wartość identyfikującą tokenu prowadzi do przeinżynierowania w złą stronę.

### Zasada zero-PII-w-kontekście-modelu — jak jest pilnowana w kodzie

**Decyzja:** żaden skrypt w tym etapie nie drukuje surowego tekstu dokumentu, wartości ze złotego zbioru ani zmapowanych fragmentów — tylko zagregowane liczby (recall %, nazwy kluczy, typy encji).

**Dlaczego:** reguła twarda z PRD obejmuje też samą sesję Claude Code (to też wywołanie API Anthropic) — każdy `print()` z realną wartością PII w wyniku narzędzia trafia do kontekstu modelu, czyli już poza lokalne środowisko. To nie jest teoretyczne ryzyko: we wcześniejszej części tej sesji `cat` na `*.golden.yml` (żeby zrozumieć format pliku) wysłał prawdziwe PESEL/adres/telefon do modelu, zanim ta zasada została odtworzona explicite dla etapu 4.

**Jak działa:** `score_document()` i `main()` liczą recall przez porównanie znormalizowanych tokenów, ale zwracają/drukują wyłącznie liczniki (`redacted/total`) i nazwy kluczy golden setu (np. `ADDRESS_001`) — same nazwy pól nie są PII, tylko to co się pod nimi kryje.

**Pułapki:** granica jest łatwa do przekroczyć przypadkiem — samo wczytanie pliku z PII (`Read`/`cat`) do zbadania jego STRUKTURY już łamie regułę, bo treść trafia do kontekstu niezależnie od tego, czy trafi do finalnej odpowiedzi. Bezpieczna operacja na PII to wyłącznie taka, która dzieje się w podprocesie (`uv run python ...`) i zwraca do rozmowy tylko agregaty.

