# Etap 1 — OCR spike (Docling + Apple Vision)

## Cel
Ocena jakości OCR na realnej próbce obu klas dokumentów zanim zbudujemy cokolwiek dalej. To spike — kod może być brzydki, wnioski mają być twarde.

## Zakres / Definition of Done
- [ ] Docling przetwarza próbkę: 3–5 badań strukturalnych (PDF + skan) i 3–5 opisów narracyjnych
- [ ] Apple Vision jako backend OCR dla zdjęć (HEIC/JPG) — porównanie jakości
- [ ] Wyjście pośrednie Markdown + JSON ocenione ręcznie (tabele wyników! — czy struktura przeżywa)
- [ ] Decyzja: które formaty wejściowe wymagają specjalnego traktowania; lista dokumentów „nieczytelnych" (licznik do S1)

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

**Pułapki:** warstwa tekstowa PDF-a strukturalnego potrafi **nie** zawierać rozpoznawalnych markerów (0 trafień na oryginalnych `Badanie_lekarskie_*`), mimo że dokument to tabela wyników — sygnał, że przy pipeline strukturalnym (etap 3) nie można ślepo ufać natywnej warstwie tekstowej; spike ma pokazać, czy potrzebny jest OCR/ekstrakcja tabeli nawet gdy warstwa tekstowa istnieje.

