# Etap 4 — Backfill i weryfikacja Success Criteria

## Cel
Przetworzenie dokumentów strukturalnych z archiwum ~390 plików (szacunkowo ~30%, czyli ok. 100–120 — reszta to narracyjne, poza zakresem V1) i pomiar S1–S4 z PRD. Rozłożone w czasie — tempo ograniczone limitami abonamentu Pro (~3 dok./dzień wystarcza).

Sedno: to pierwszy etap, gdzie pipeline (etapy 0–3, już zbudowany i zwalidowany na 14 dokumentach) spotyka się z realną skalą i realnym czasem — nie „czy działa", tylko „czy przeżyje przerwanie w połowie, czy policzy dokumenty nieczytelne zamiast je przemilczeć, i czy operator nie zniechęci się zatwierdzaniem". PRD ma to nazwane wprost w tabeli ryzyk: „zatwierdzanie ręczne zniechęci po backfillu → front-load, słownik nasyca się na pierwszych ~50 dokumentach" — stąd pierwsza partia to ~50, nie cały wolumen naraz.

Trzy strumienie pracy: (1) domknięcie brakujących mechanizmów DoD w kodzie (licznik odrzuconych, wznawianie Warstwy 3 po przerwaniu) — zbudowane i przetestowane PRZED dotknięciem realnych danych; (2) pierwsza partia ~50 dokumentów, przetworzona i zmierzona pod S1; (3) test S3 (nowy dokument end-to-end ≤15 min) na pojedynczym realnym pliku.

## Zakres / Definition of Done
- [x] Partia wsadowa: kolejkowanie (numerowany postęp `[i/N]`, stała kolejność `sorted()`), wznawianie po przerwaniu (Warstwa 3 odzyskuje propozycje z `pending/aliases.yml` zamiast pytać Haiku drugi raz), licznik dokumentów odrzuconych (próg `MIN_OCR_CHARS=500`, kalibrowany na realnych danych) — `src/structural_pipeline.py`, oba mechanizmy przetestowane jednostkowo (mock Haiku, syntetyczny pending) przed uruchomieniem na realnych danych; zero regresji na 14 istniejących dokumentach (114 rekordów, bez zmian)
- [ ] S1: ≥95% dokumentów strukturalnych w kanonicznym JSON, 100% markerów zmapowanych lub świadomie odrzuconych
- [ ] S3: nowy dokument przechodzi pipeline end-to-end w ≤15 min pracy operatora — pomiar na realnym pliku (upload do `data/raw/structural/` → `uv run python src/structural_pipeline.py` → zatwierdzenie ew. aliasów w `pending/` → zapis NDJSON). Bez orkiestratora — uruchomienie z terminala (n8n usunięty z V1, patrz PRD)
- [ ] Pomiar i zapis wyników S1–S4 w tym pliku
- [ ] Retrospektywa: co poprawić przy bieżącym napływie nowych dokumentów (2–3/mies.)

## Wyniki S1–S4
<!-- uzupełniane po backfillu -->

## Notatki
<!-- Grupuj po temacie, nie po dacie (chronologię trzyma git). Każdy podpunkt
     w OSOBNYM akapicie (pusta linia między nimi). Dla każdego tematu:

### <Temat / czego dotyczy>

**Decyzja:** co ustalono.

**Dlaczego:** uzasadnienie, trade-offy.

**Jak działa:** mechanizm narzędzia pod spodem — sedno nauki.

**Pułapki:** co zaskoczyło, na co uważać.

Nie każdy temat wymaga wszystkich czterech podpunktów. To notatki do nauki, nie log czynności. -->

### OTWARTE — nowy lab, kod markera w nawiasach kwadratowych `[XXX]`, nie `(ICD-9: XXX)`

**Status: NIEDOKOŃCZONE.** Zacznij tutaj następną sesję nad etapem 4, zanim cokolwiek innego.

**Decyzja (do zrobienia, nie zrobiona):** parser (`parse_document()`, `_ICD9_LOOSE` regex) rozpoznaje wyłącznie inline kod w formacie `(ICD-9: kod)`. Część dokumentów z pierwszego realnego backfillu (39 plików: `188572094.pdf`, `190111920.pdf`, `Pierwiastki w krwi.pdf`, `Pierwiastki w moczu.pdf`, jeden marker w `Lipidogram.pdf`, jeden w drugim pliku endokrynologicznym) koduje markery w nawiasach KWADRATOWYCH: `[L23] Fosforany`, `[N45] Potas w moczu` itd. Ten format nigdy nie ustawia `section_active = True`, więc żadna linia w takim dokumencie nie trafia do sprawdzenia słownika — **niezależnie od tego, czy alias istnieje w config**.

**Dlaczego to nie jest "brakujący alias":** 47 aliasów dla dokładnie tych markerów już jest zatwierdzonych w `config/aliases.yml` (commit `b13e11a`) — pochodzą z realnych propozycji Haiku, zweryfikowanych ręcznie (włącznie ze sprawdzeniem, z którego pliku źródłowego pochodzi każdy niepewny przypadek krew/mocz). Mimo to po dodaniu aliasów i ponownym uruchomieniu pipeline'u te same 51 markerów **nadal** wypada jako nieznane — dowód, że problem jest w rozpoznawaniu formatu kodu, nie w słowniku. Weryfikacja: `data/pending/aliases.yml` (`git diff` niepotrzebny, plik poza gitem) — WSZYSTKIE 51 pozostałych wpisów ma już kod inny niż `NEEDS_REVIEW` (bo mechanizm wznawiania z etapu 4 poprawnie je odzyskał), tylko nigdy nie docierają do sprawdzenia w `config/`.

**Plan naprawy (nierozpoczęty):** dodać do `parse_document()` drugi wzorzec rozpoznawania inline-kodu, analogiczny do `_ICD9_LOOSE = re.compile(r"\(ICD-9:\s*([^)]*)\)")`, ale dla `\[([A-Z0-9]+)\]` — i podpiąć go w tym samym miejscu co obecny (ustawia `section_active = True`, próbuje `resolve_section()` po nazwie, w razie porażki flaguje jako `unknown`). Nazwy markerów w `pending`/`config` już zawierają prefiks `[XXX]` jako część klucza (bo tak wyszły z parsera) — po naprawie mogą wymagać przepisania na czystą nazwę bez nawiasu, do zdecydowania przy implementacji (zależy, czy nowy regex ma wycinać prefiks z `name_raw`, czy zostawiać jak dziś).

**Stan po zatrzymaniu (koniec sesji, limit czasu):** `data/store/structural.ndjson` ma 164 rekordy (z 149 przed tą sesją). `data/pending/aliases.yml` ma 51 wpisów czekających — bezpieczne, nic nie zgubione, zadziałają automatycznie po naprawie regexu bez ponownego pytania Haiku (mechanizm wznawiania już to obsługuje).

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

