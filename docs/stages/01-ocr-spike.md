# Etap 1 — OCR spike (Docling + Apple Vision)

## Cel
Ocena jakości OCR na realnej próbce dokumentów strukturalnych zanim zbudujemy cokolwiek dalej. To spike — kod może być brzydki, wnioski mają być twarde.

Sedno: to **decyzja o silniku i konfiguracji OCR**, nie budowa modułu. Od jakości OCR zależy wszystko dalej — standaryzacja dostaje na wejściu dokładnie to, co wypluje OCR. Zły OCR = pipeline parsuje śmieci. „Jakość" tu znaczy: czy tabela przeżywa — marker → wartość → jednostka → zakres w dobrych polach (mojibake = nie ma czego parsować).

## Zakres / Definition of Done
- [x] Docling przetwarza próbkę 5 dokumentów strukturalnych — `src/ocr_spike.py`, wyjście MD+JSON w `data/interim/ocr-spike/`
- [x] Apple Vision jako backend OCR dla zdjęć (HEIC/JPG) — porównany (ocrmac, `lang=pl-PL`); **wyraźnie lepszy na polskim** (diakrytyki, jednostki, brak chińskich glifów), wyjście w `data/interim/ocr-spike-applevision/`. Rekomendacja: silnik podstawowy
- [x] Wyjście pośrednie Markdown + JSON ocenione ręcznie — sign-off właściciela zrobiony: RapidOCR lepsze umiejscowienie komórek tabeli, Apple Vision lepszy polski; struktura tabel przeżywa pod wymuszonym OCR (domyślny Docling → mojibake)
- [x] Decyzja: silnik podstawowy **Apple Vision** (`pl-PL`); wymuszony OCR dla PDF-ów z zepsutą warstwą tekstową; duże zdjęcia = downscale/limit PIL; RapidOCR jako fallback (rewizja w etapie 2). Lista „nieczytelnych": zero

## Notatki
<!-- Grupuj po temacie, nie po dacie (chronologię trzyma git). Każdy podpunkt
     w OSOBNYM akapicie (pusta linia między nimi). Dla każdego tematu:

### <Temat / czego dotyczy>

**Decyzja:** co ustalono.

**Dlaczego:** uzasadnienie, trade-offy.

**Jak działa:** mechanizm narzędzia pod spodem — sedno nauki.

**Pułapki:** co zaskoczyło, na co uważać.

Nie każdy temat wymaga wszystkich czterech podpunktów. To notatki do nauki, nie log czynności. -->

### Pułapka zepsutej warstwy tekstowej — Docling ufa jej domyślnie

**Decyzja:** dla PDF-ów laboratoryjnych wymuszamy pełny OCR strony (`ocr_options.force_full_page_ocr=True`). Domyślny pipeline Docling daje na nich **śmieci**.

**Dlaczego:** te PDF-y (źródło: LUX MED / Diagnostyka) mają warstwę tekstową w custom foncie bez mapy ToUnicode — ekstrakcja zwraca mojibake (`! " # $`). Docling domyślnie **ufa** istniejącej warstwie (szybko, ~1s) i nie OCR-uje → cała morfologia jako krzaki. Wymuszony OCR renderuje stronę do obrazu i czyta realnie: `284953992` 1984 → 8227 znaków, pełna tabela marker/wartość/jednostka/zakres MIN-MAX/FLAGA (Leukocyty 5,1 tys/μl 4,2–9,1, Hemoglobina 14,1, …). Tabela przeżywa.

**Jak działa:** `PdfPipelineOptions.do_ocr=True` OCR-uje tylko strony, które Docling uzna za bitmapę; `ocr_options.force_full_page_ocr=True` wymusza OCR całej renderowanej strony niezależnie od warstwy tekstowej. Wstrzykiwane przez `DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})`.

**Pułapki:** to **nie** jest „force OCR wszędzie" — dokument z dobrą natywną warstwą tekstową straciłby na jakości pod wymuszonym OCR. Potrzebna reguła decyzyjna **per plik**: oceń jakość warstwy tekstowej (np. udział znaków spoza oczekiwanego alfabetu / brak rozpoznawalnych słów) → zepsuta lub brak → OCR; czysta → użyj jej.

### RapidOCR — jakość OCR na polskim

**Decyzja:** domyślny silnik OCR Docling 2.113 to **RapidOCR** (model PP-OCRv4, torch, CPU) — pobierany automatycznie przy pierwszym `convert`. Czyta polski użytecznie, ale z błędami; jakość do porównania z Apple Vision.

**Jak działa:** model jest chińsko-angielski — wykrywa i rozpoznaje tekst na renderowanym obrazie strony. Dla pisma łacińskiego działa, ale bez dedykowanej obsługi polskich znaków.

**Pułapki:** polskie diakrytyki bywają gubione (ł→t: „prawidtowe", „byto") lub mapowane na **chińskie glify** (Ż→之: „ME之CZYZNA", „之EL"); jednostki też mangną (g/dl → „IP/B"). Jednostka jest normalizowana deterministycznie przez `units.yml` po nazwie markera, więc błąd OCR jednostki jest odzyskiwalny — nienaprawialna jest tylko zgubiona wartość. Chińskie glify w nazwach własnych to argument, że Apple Vision (natywny polski) jest lepszym backendem.

### Apple Vision (ocrmac) vs RapidOCR — jakość na polskim

**Decyzja:** Apple Vision (backend `ocrmac`, `lang=['pl-PL']`) daje wyraźnie lepszą jakość na polskim niż RapidOCR — rekomendowany silnik podstawowy. Domyślny `lang` w `OcrMacOptions` to `fr/de/es/en` (bez polskiego) — trzeba jawnie ustawić `pl-PL`, inaczej jakość spada.

**Dlaczego:** na tej samej morfologii Apple Vision poprawnie czyta diakrytyki (MAĆKÓWKA, MĘŻCZYZNA, Płytki), jednostki (g/dl, fl, pg) i nie wstawia chińskich glifów; RapidOCR gubił ł/ę, mapował Ż→之, mangłał g/dl→„IP/B".

**Jak działa:** `ocrmac` woła macOS Vision (framework `vision`, tryb `accurate`) przez pyobjc; Docling podpina go jako `ocr_options = OcrMacOptions(...)`. Silnik natywny (Neural Engine) — szybki, bez pobierania modeli.

**Pułapki:** (1) na dużych zdjęciach ścieżka ocrmac→PIL wywala `DecompressionBombError` (duże skany/foto renderowane do >200 Mpx > limit PIL) — podnieść `Image.MAX_IMAGE_PIXELS` lub downscale'ować źródło. (2) Apple Vision gubi pojedyncze komórki liczbowe w tabeli (kilka wartości MIN/MAX, które RapidOCR złapał) — dlatego sign-off operatora na wartościach. (3) drobne reszty: „μl"→„u1/u|", „śluzowa"→„sluzowa", „Wałbrzyska"→„Watbrzyska".

### Wybór silnika OCR — decyzja

**Decyzja:** jeden silnik — **Apple Vision** (`ocrmac`, `lang=pl-PL`). RapidOCR zostaje zainstalowany jako fallback (bez dual-run w V1). Wymuszony OCR dla PDF-ów z zepsutą warstwą tekstową; duże zdjęcia = downscale / limit PIL.

**Dlaczego:** Apple Vision natywnie lepiej czyta polski (diakrytyki, jednostki) niż RapidOCR. Jakość tekstu jest tu wtórna wobec `aliases.yml`/`units.yml`, które korygują błędy deterministycznie po nazwie markera („Plytki"→„Płytki krwi", „IP/B"→„g/dl") — nienaprawialna jest tylko zgubiona wartość. RapidOCR-forced był odrobinę lepszy w kompletności komórek, ale różnica mała, a jeden silnik jest prostszy i human-in-the-loop łapie rzadki brak.

**Pułapki:** próbka to N=2 realne tabele — czy Apple Vision gubi komórki systematycznie, rozstrzyga etap 2. Klasyfikacja kolumn jest **niespójna między stronami tego samego dokumentu**: na 1. stronie nagłówki (Wynik/Jedn/MIN/MAX) nie przykleiły się do tabeli (zostały luźnym tekstem nad nią), na 2. stronie tabela ma poprawny wiersz nagłówka `Badanie|Wynik|Jedn.|MIN|MAX|FLAGA`. Skoro nawet w jednym pliku raz działa, raz nie — nie wolno ufać OCR-owanym nagłówkom; parsować pozycyjnie wg stałego layoutu labu (`laboratories.yml`). To problem niezależny od silnika.

### Jakość wyjścia — czy struktura przeżywa

**Decyzja:** struktura tabel przeżywa pod wymuszonym OCR. Ocena techniczna zrobiona — sign-off właściciela (porównanie z oryginałami) po Apple Vision.

**Jak działa:** TableFormer w Docling odtwarza siatkę tabeli z układu strony; przy wymuszonym OCR odzyskuje pełną tabelę marker/wartość/jednostka/zakres MIN-MAX/FLAGA (np. `284953992`: 1984 → 8227 znaków).

**Pułapki:** drobne szumy siatki — nagłówek „Data pobrania" wchodzi do wiersza tabeli, a przy kontynuacji na 2. stronie header rozjeżdża się na wszystkie kolumny. Do wyprostowania w standaryzacji (etap 2), nie blokuje.

### Formaty wymagające specjalnego traktowania

**Decyzja:** specjalnego traktowania wymagają PDF-y lab z zepsutą warstwą tekstową → wymuszony OCR; foto (JPEG do 5712×4284) i skany → OCR działa domyślnie. Lista „nieczytelnych" w próbce: zero.

**Pułapki:** OCR na CPU jest wolny (10–24 s/plik dla obrazów). Przy backfillu ~115–120 plików to realny czas łącznie — rozłożyć w czasie / przetwarzać wsadowo poza godzinami pracy.

### PII w surowym wyjściu OCR

**Decyzja:** OCR-owany markdown zawiera pełne PII (nazwisko, adres, PESEL) w nagłówku/stopce — surowy tekst nigdy nie trafia do żadnego API.

**Dlaczego:** parsowanie (Warstwa 1+2, etap 2) jest w pełni lokalne — regex i słownik na tekście, bez wywołań zewnętrznych. Jedyne wywołanie LLM w całym pipelinie (Warstwa 3) wysyła wyłącznie pojedynczą nazwę markera z komórki tabeli, nigdy pełny dokument.
