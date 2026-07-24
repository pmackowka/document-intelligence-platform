# Etap 1 — OCR spike (Docling + Apple Vision)

## Cel
Ocena jakości OCR na realnej próbce dokumentów strukturalnych, zanim zbudujemy cokolwiek dalej. To spike — kod może być brzydki, wnioski mają być twarde.

To decyzja o silniku OCR, nie budowa modułu. Standaryzacja dostaje na wejściu dokładnie to, co wypluje OCR — zły OCR = pipeline parsuje śmieci. „Jakość" znaczy tu: czy tabela przeżywa (marker → wartość → jednostka → zakres w dobrych polach). Mojibake = nie ma czego parsować.

## Zakres / Definition of Done
- [x] Docling przetwarza próbkę 5 dokumentów strukturalnych — `src/ocr_spike.py`, wyjście MD+JSON w `data/interim/ocr-spike/`
- [x] Apple Vision jako backend OCR dla zdjęć (HEIC/JPG) — porównany (ocrmac, `lang=pl-PL`); **wyraźnie lepszy na polskim** (diakrytyki, jednostki, brak chińskich glifów), wyjście w `data/interim/ocr-spike-applevision/`. Rekomendacja: silnik podstawowy
- [x] Wyjście pośrednie Markdown + JSON ocenione ręcznie — sign-off właściciela: RapidOCR lepsze umiejscowienie komórek tabeli, Apple Vision lepszy polski; struktura tabel przeżywa pod wymuszonym OCR (domyślny Docling → mojibake)
- [x] Decyzja: silnik podstawowy **Apple Vision** (`pl-PL`); wymuszony OCR dla PDF-ów z zepsutą warstwą tekstową; duże zdjęcia = downscale/limit PIL; RapidOCR jako fallback (rewizja w etapie 2). Lista „nieczytelnych": zero

## Notatki

### Pułapka zepsutej warstwy tekstowej — Docling ufa jej domyślnie

**Decyzja:** dla PDF-ów laboratoryjnych wymuszamy pełny OCR strony (`ocr_options.force_full_page_ocr=True`). Domyślny pipeline Docling daje na nich **śmieci**.

**Dlaczego:** te PDF-y (LUX MED / Diagnostyka) mają warstwę tekstową w custom foncie bez mapy ToUnicode — ekstrakcja zwraca mojibake (`! " # $`). Docling domyślnie ufa istniejącej warstwie (szybko, ~1s) i nie OCR-uje → cała morfologia jako krzaki. Wymuszony OCR renderuje stronę do obrazu i czyta realnie (`284953992`: 1984 → 8227 znaków, pełna tabela marker/wartość/jednostka/zakres/flaga).

**Jak działa:** `do_ocr=True` OCR-uje tylko strony, które Docling uzna za bitmapę; `force_full_page_ocr=True` wymusza OCR całej renderowanej strony niezależnie od warstwy tekstowej. Wstrzykiwane przez `DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})`.

**Pułapki:** to **nie** „force OCR wszędzie" — dokument z dobrą natywną warstwą straciłby na jakości. Potrzebna reguła decyzyjna per plik: oceń jakość warstwy (udział znaków spoza alfabetu / brak rozpoznawalnych słów) → zepsuta lub brak → OCR; czysta → użyj jej.

### Wybór silnika: Apple Vision vs RapidOCR na polskim

**Decyzja:** jeden silnik — **Apple Vision** (`ocrmac`, `lang=['pl-PL']`). RapidOCR zostaje jako fallback (bez dual-run w V1). Domyślny `lang` w `OcrMacOptions` to `fr/de/es/en` — trzeba jawnie ustawić `pl-PL`, inaczej jakość spada.

**Dlaczego:** na tej samej morfologii Apple Vision poprawnie czyta diakrytyki (MAĆKÓWKA, MĘŻCZYZNA, Płytki) i jednostki (g/dl, fl, pg); RapidOCR (model chińsko-angielski PP-OCRv4) gubił ł/ę, mapował Ż→之 („ME之CZYZNA"), manglował g/dl→„IP/B". Jakość tekstu jest wtórna wobec `aliases.yml`/`units.yml`, które korygują błędy deterministycznie po nazwie markera — nienaprawialna jest tylko zgubiona wartość. RapidOCR był odrobinę lepszy w kompletności komórek, ale różnica mała, a jeden silnik jest prostszy i HITL łapie rzadki brak.

**Jak działa:** `ocrmac` woła macOS Vision (framework `vision`, tryb `accurate`) przez pyobjc; Docling podpina go jako `ocr_options`. Silnik natywny (Neural Engine) — szybki, bez pobierania modeli.

**Pułapki:** (1) na dużych zdjęciach ścieżka ocrmac→PIL wywala `DecompressionBombError` (>200 Mpx > limit PIL) — podnieść `Image.MAX_IMAGE_PIXELS` lub downscale'ować. (2) Apple Vision gubi pojedyncze komórki liczbowe w tabeli — stąd sign-off operatora na wartościach. (3) drobne reszty: „μl"→„u1", „śluzowa"→„sluzowa".

### Klasyfikacja kolumn niespójna — parsować pozycyjnie, nie po nagłówkach

**Decyzja:** nie ufać OCR-owanym nagłówkom tabeli; parsować pozycyjnie wg stałego layoutu labu (`laboratories.yml`).

**Pułapki:** klasyfikacja kolumn bywa niespójna **między stronami tego samego dokumentu** — na 1. stronie nagłówki (Wynik/Jedn/MIN/MAX) zostały luźnym tekstem nad tabelą, na 2. stronie tabela ma poprawny wiersz nagłówka. Skoro nawet w jednym pliku raz działa, raz nie — nagłówkom nie wolno ufać. Problem niezależny od silnika. Próbka to N=2 realne tabele — czy Apple Vision gubi komórki systematycznie, rozstrzyga etap 2.

### Formaty i wydajność

**Decyzja:** specjalnego traktowania wymagają PDF-y lab z zepsutą warstwą tekstową → wymuszony OCR; foto (do 5712×4284) i skany → OCR domyślny. Lista „nieczytelnych" w próbce: zero.

**Pułapki:** OCR na CPU jest wolny (10–24 s/plik dla obrazów). Przy backfillu ~115–120 plików to realny czas łącznie — rozłożyć w czasie / przetwarzać wsadowo poza godzinami pracy.

### PII w surowym wyjściu OCR

**Decyzja:** OCR-owany markdown zawiera pełne PII (nazwisko, adres, PESEL) w nagłówku/stopce — surowy tekst nigdy nie trafia do żadnego API.

**Dlaczego:** parsowanie (Warstwa 1+2, etap 2) jest w pełni lokalne — regex i słownik na tekście, bez wywołań zewnętrznych. Jedyne wywołanie LLM (Warstwa 3) wysyła wyłącznie pojedynczą nazwę markera, nigdy pełny dokument.
