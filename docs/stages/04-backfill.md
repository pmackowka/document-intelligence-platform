# Etap 4 — Backfill i weryfikacja Success Criteria

## Cel
Przetworzenie dokumentów strukturalnych z archiwum ~390 plików (szacunkowo ~30%, czyli ok. 100–120 — reszta to narracyjne, poza zakresem V1) i pomiar S1–S4 z PRD. Rozłożone w czasie — tempo ograniczone limitami abonamentu Pro (~3 dok./dzień wystarcza).

Sedno: to pierwszy etap, gdzie pipeline (etapy 0–3, już zbudowany i zwalidowany na 14 dokumentach) spotyka się z realną skalą i realnym czasem — nie „czy działa", tylko „czy przeżyje przerwanie w połowie, czy policzy dokumenty nieczytelne zamiast je przemilczeć, i czy operator nie zniechęci się zatwierdzaniem". PRD ma to nazwane wprost w tabeli ryzyk: „zatwierdzanie ręczne zniechęci po backfillu → front-load, słownik nasyca się na pierwszych ~50 dokumentach" — stąd pierwsza partia to ~50, nie cały wolumen naraz.

Trzy strumienie pracy: (1) domknięcie brakujących mechanizmów DoD w kodzie (licznik odrzuconych, wznawianie Warstwy 3 po przerwaniu) — zbudowane i przetestowane PRZED dotknięciem realnych danych; (2) pierwsza partia ~50 dokumentów, przetworzona i zmierzona pod S1; (3) test S3 (nowy dokument end-to-end ≤15 min) na pojedynczym realnym pliku.

## Zakres / Definition of Done
- [x] Partia wsadowa: kolejkowanie (numerowany postęp `[i/N]`, stała kolejność `sorted()`), wznawianie po przerwaniu (Warstwa 3 odzyskuje propozycje z `pending/aliases.yml` zamiast pytać Haiku drugi raz), licznik dokumentów odrzuconych (próg `MIN_OCR_CHARS=500`, kalibrowany na realnych danych) — `src/structural_pipeline.py`, oba mechanizmy przetestowane jednostkowo (mock Haiku, syntetyczny pending) przed uruchomieniem na realnych danych; zero regresji na 14 istniejących dokumentach (114 rekordów, bez zmian)
- [x] S1: 100% markerów zmapowanych (216 rekordów, 0 nieznanych) na 39 dokumentach pierwszej partii; 31/39 (79%) dało realne rekordy, **8/39 (21%) świadomie odrzucone** (trzeci, nierozpoznany format — pojedyncze testy bez tabeli/ICD-9/nawiasów, decyzja operatora po sprawdzeniu struktury: nie inżynierować kolejnego parsera dla garstki jednorazowych przypadków, patrz notatka „8 odrzuconych dokumentów")
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

