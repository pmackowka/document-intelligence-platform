# Etap 1 — OCR spike (Docling + Apple Vision)

## Cel
Ocena jakości OCR na realnej próbce obu klas dokumentów zanim zbudujemy cokolwiek dalej. To spike — kod może być brzydki, wnioski mają być twarde.

Sedno: to **decyzja o silniku i konfiguracji OCR**, nie budowa modułu. Od jakości OCR zależy wszystko dalej — standaryzacja strukturalna i ekstrakcja narracyjna dostają na wejściu dokładnie to, co wypluje OCR. Zły OCR = pipeline parsuje śmieci.

„Jakość" znaczy co innego dla każdej klasy:
- **strukturalne** — czy tabela przeżywa: marker → wartość → jednostka → zakres w dobrych polach (mojibake = nie ma czego parsować);
- **narracyjne** — czy proza jest czytelna i kompletna (LLM nie wyciągnie ustaleń z krzaków).

## Zakres / Definition of Done
- [x] Docling przetwarza próbkę: 5 strukturalnych + 5 narracyjnych — `src/ocr_spike.py`, 10/10 OK, wyjście MD+JSON w `data/interim/ocr-spike/`
- [x] Apple Vision jako backend OCR dla zdjęć (HEIC/JPG) — porównany (ocrmac, `lang=pl-PL`); **wyraźnie lepszy na polskim** (diakrytyki, jednostki, brak chińskich glifów), wyjście w `data/interim/ocr-spike-applevision/`. Rekomendacja: silnik podstawowy
- [x] Wyjście pośrednie Markdown + JSON ocenione ręcznie — sign-off właściciela zrobiony: RapidOCR lepsze umiejscowienie komórek tabeli, Apple Vision lepszy polski i narracja; struktura tabel przeżywa pod wymuszonym OCR (domyślny Docling → mojibake)
- [x] Decyzja: silnik podstawowy **Apple Vision** (`pl-PL`); strukturalne = wymuszony OCR; narracyjne z dobrą warstwą = warstwa tekstowa; duże zdjęcia = downscale/limit PIL; RapidOCR jako fallback strukturalny (rewizja w etapie 3). Lista „nieczytelnych": 0/10

## Notatki
<!-- Grupuj po temacie, nie po dacie (chronologię trzyma git). Każdy podpunkt
     w OSOBNYM akapicie (pusta linia między nimi). Dla każdego tematu:

### <Temat / czego dotyczy>

**Decyzja:** co ustalono.

**Dlaczego:** uzasadnienie, trade-offy.

**Jak działa:** mechanizm narzędzia pod spodem — sedno nauki.

**Pułapki:** co zaskoczyło, na co uważać.

Nie każdy temat wymaga wszystkich czterech podpunktów. To notatki do nauki, nie log czynności. -->

### Organizacja próbki i ingestu: `data/raw/{structural,narrative}/`

**Decyzja:** dokumenty leżą w dwóch podfolderach `data/raw/` — `structural/` (tabele krew/mocz) i `narrative/` (opisy USG/MRI/TK). Klasę nadaje operator ręcznie: dla próbki spike'u wrzucając plik do właściwego folderu, docelowo — etykietą przy uploadzie przez n8n. Ten sam podział jest realnym układem ingestu (PRD v1.1, Scope pkt 3), nie tylko konwencją próbki.

**Dlaczego:** klasyfikacja automatyczna okazała się zawodna — heurystyka „markery/jednostki w warstwie tekstowej" nie rozpoznała realnych badań krwi (operator potwierdził klasę ręcznie). Operator rozpoznaje klasę bezbłędnie i tak jest w pętli, więc ręczna etykieta to najtańszy i najpewniejszy klasyfikator. Skutkiem decyzji jest usunięcie z V1 automatycznego klasyfikatora i konektora Google Drive (ingest wyłącznie ręczny).

**Pułapki:** warstwa tekstowa PDF-a strukturalnego potrafi **nie** zawierać rozpoznawalnych markerów (0 trafień na oryginalnych `Badanie_lekarskie_*`), mimo że dokument to tabela wyników — sygnał, że przy pipeline strukturalnym (etap 3) nie można ślepo ufać natywnej warstwie tekstowej. Spike to potwierdził (niżej).

### Pułapka zepsutej warstwy tekstowej — Docling ufa jej domyślnie

**Decyzja:** dla strukturalnych PDF-ów laboratoryjnych wymuszamy pełny OCR strony (`ocr_options.force_full_page_ocr=True`). Domyślny pipeline Docling daje na nich **śmieci**.

**Dlaczego:** te PDF-y (źródło: LUX MED / Diagnostyka) mają warstwę tekstową w custom foncie bez mapy ToUnicode — ekstrakcja zwraca mojibake (`! " # $`). Docling domyślnie **ufa** istniejącej warstwie (szybko, ~1s) i nie OCR-uje → cała morfologia jako krzaki. Wymuszony OCR renderuje stronę do obrazu i czyta realnie: `284953992` 1984 → 8227 znaków, pełna tabela marker/wartość/jednostka/zakres MIN-MAX/FLAGA (Leukocyty 5,1 tys/μl 4,2–9,1, Hemoglobina 14,1, …). Tabela przeżywa.

**Jak działa:** `PdfPipelineOptions.do_ocr=True` OCR-uje tylko strony, które Docling uzna za bitmapę; `ocr_options.force_full_page_ocr=True` wymusza OCR całej renderowanej strony niezależnie od warstwy tekstowej. Wstrzykiwane przez `DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})`.

**Pułapki:** to **nie** jest „force OCR wszędzie". Narracyjny PDF z DOBRĄ warstwą (Karta wizyty, źródło szpitalne) daje idealny polski z diakrytykami w 0,3s — wymuszony OCR by go popsuł. Potrzebna reguła decyzyjna **per plik, nie per klasa**: oceń jakość warstwy tekstowej (np. udział znaków spoza oczekiwanego alfabetu / brak rozpoznawalnych słów) → zepsuta lub brak → OCR; czysta → użyj jej. To realne wymaganie do modułu OCR (etap 3+), nie sama klasa dokumentu.

### RapidOCR — jakość OCR na polskim

**Decyzja:** domyślny silnik OCR Docling 2.113 to **RapidOCR** (model PP-OCRv4, torch, CPU) — pobierany automatycznie przy pierwszym `convert`. Czyta polski użytecznie, ale z błędami; jakość do porównania z Apple Vision.

**Jak działa:** model jest chińsko-angielski — wykrywa i rozpoznaje tekst na renderowanym obrazie strony. Dla pisma łacińskiego działa, ale bez dedykowanej obsługi polskich znaków.

**Pułapki:** polskie diakrytyki bywają gubione (ł→t: „prawidtowe", „byto") lub mapowane na **chińskie glify** (Ż→之: „ME之CZYZNA", „之EL"); jednostki też mangną (g/dl → „IP/B"). Dla narracji (LLM ekstrahuje sens) akceptowalne; dla strukturalnych jednostka jest normalizowana deterministycznie przez `units.yml` po nazwie markera, więc błąd OCR jednostki jest odzyskiwalny. Chińskie glify w nazwach własnych to argument, że Apple Vision (natywny polski) może być lepszym backendem.

### Apple Vision (ocrmac) vs RapidOCR — jakość na polskim

**Decyzja:** Apple Vision (backend `ocrmac`, `lang=['pl-PL']`) daje wyraźnie lepszą jakość na polskim niż RapidOCR — rekomendowany silnik podstawowy. Domyślny `lang` w `OcrMacOptions` to `fr/de/es/en` (bez polskiego) — trzeba jawnie ustawić `pl-PL`, inaczej jakość spada.

**Dlaczego:** na tej samej morfologii Apple Vision poprawnie czyta diakrytyki (MAĆKÓWKA, MĘŻCZYZNA, Płytki), jednostki (g/dl, fl, pg) i nie wstawia chińskich glifów; RapidOCR gubił ł/ę, mapował Ż→之, mangłał g/dl→„IP/B". W narracji Apple Vision jest niemal na poziomie natywnej warstwy tekstowej (pełne „krętego", „kątnicy", „wstępnicy").

**Jak działa:** `ocrmac` woła macOS Vision (framework `vision`, tryb `accurate`) przez pyobjc; Docling podpina go jako `ocr_options = OcrMacOptions(...)`. Silnik natywny (Neural Engine) — szybki, bez pobierania modeli.

**Pułapki:** (1) na dużych zdjęciach ścieżka ocrmac→PIL wywala `DecompressionBombError` (USG 5712×4284 renderowane do ~220 Mpx > limit PIL) — podnieść `Image.MAX_IMAGE_PIXELS` lub downscale'ować źródło. (2) Apple Vision gubi pojedyncze komórki liczbowe w tabeli (kilka wartości MIN/MAX, które RapidOCR złapał) — dlatego sign-off operatora na wartościach. (3) drobne reszty: „μl"→„u1/u|", „śluzowa"→„sluzowa", „Wałbrzyska"→„Watbrzyska".

### Wybór silnika OCR — decyzja

**Decyzja:** jeden silnik — **Apple Vision** (`ocrmac`, `lang=pl-PL`) — dla obu klas. RapidOCR zostaje zainstalowany jako fallback strukturalny (bez dual-run w V1). Strukturalne = wymuszony OCR; narracyjne z dobrą warstwą tekstową = warstwa (bez OCR); duże zdjęcia = downscale / limit PIL.

**Dlaczego:** narracyjne (70% wolumenu) Apple Vision oddaje niemal bezbłędnie, RapidOCR potrafił nie wyciągnąć całego opisu. Dla strukturalnych jakość tekstu jest wtórna — `aliases.yml`/`units.yml` korygują deterministycznie „Plytki"→„Płytki krwi", „IP/B"→„g/dl"; nienaprawialna jest tylko zgubiona wartość. RapidOCR-forced był tam odrobinę lepszy w kompletności komórek, ale różnica mała, a jeden silnik jest prostszy i human-in-the-loop łapie rzadki brak.

**Pułapki:** próbka strukturalna to N=2 realne tabele — czy Apple Vision gubi komórki systematycznie, rozstrzyga etap 3. Klasyfikacja kolumn jest **niespójna między stronami tego samego dokumentu**: na 1. stronie nagłówki (Wynik/Jedn/MIN/MAX) nie przykleiły się do tabeli (zostały luźnym tekstem nad nią), na 2. stronie tabela ma poprawny wiersz nagłówka `Badanie|Wynik|Jedn.|MIN|MAX|FLAGA`. Skoro nawet w jednym pliku raz działa, raz nie — nie wolno ufać OCR-owanym nagłówkom; parsować pozycyjnie wg stałego layoutu labu (`laboratories.yml`). To problem niezależny od silnika.

### Jakość wyjścia — czy struktura przeżywa

**Decyzja:** struktura tabel strukturalnych przeżywa pod wymuszonym OCR; narracyjne (skan i foto) czytelne i spójne. Ocena techniczna zrobiona — sign-off właściciela (porównanie z oryginałami) po Apple Vision.

**Jak działa:** TableFormer w Docling odtwarza siatkę tabeli z układu strony; przy wymuszonym OCR odzyskuje pełną tabelę marker/wartość/jednostka/zakres MIN-MAX/FLAGA (np. `284953992`: 1984 → 8227 znaków).

**Pułapki:** drobne szumy siatki — nagłówek „Data pobrania" wchodzi do wiersza tabeli, a przy kontynuacji na 2. stronie header rozjeżdża się na wszystkie kolumny. Do wyprostowania w standaryzacji (etap 3), nie blokuje.

### Formaty wymagające specjalnego traktowania

**Decyzja:** specjalnego traktowania wymagają: (1) strukturalne PDF-y lab z zepsutą warstwą tekstową → wymuszony OCR; (2) foto (JPEG do 5712×4284) i skany → OCR działa domyślnie. Lista „nieczytelnych": w próbce **0/10**.

**Pułapki:** OCR na CPU jest wolny (10–24 s/plik dla obrazów). Przy backfillu ~390 plików to minuty–godziny łącznie — rozłożyć w czasie / przetwarzać wsadowo poza godzinami pracy.

### PII w surowym wyjściu OCR

**Decyzja:** żaden output OCR nie trafia do LLM bez wcześniejszego Presidio.

**Dlaczego:** surowy markdown zawiera pełne PII — nazwisko, adres, PESEL widoczne wprost. Potwierdza twardą regułę kolejności anonimizacji: nic do zewnętrznego API przed Presidio.

