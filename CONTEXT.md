# Document Intelligence Platform

Lokalna platforma do przetwarzania osobistej dokumentacji medycznej (badania krwi/moczu) z analizą trendów w czasie. Jeden użytkownik, zero UI.

## Language

**Marker**:
Pojedynczy oznaczany parametr medyczny (np. ferrytyna, CRP, hemoglobina) śledzony na osi czasu przez wiele pomiarów. Ma kod kanoniczny (np. `HGB`, `WBC`) i polską etykietę do raportów (`marker_labels.yml`).
_Avoid_: parametr, wynik, badanie (badanie to zbiór markerów, nie pojedynczy marker)

**Panel**:
Grupa markerów zdefiniowana przez typ badania (np. morfologia, biochemia, lipidogram). Ten sam surowy napis znaczy różne rzeczy zależnie od panelu ("Leukocyty" w morfologii ≠ "Leukocyty" w moczu) — dlatego aliasy są scoped per panel, nie globalne.
_Avoid_: badanie, kategoria

**Alias**:
Mapowanie surowej nazwy markera z dokumentu źródłowego (`marker_raw`) na kod kanoniczny (`marker`), zatwierdzane przez operatora (human-in-the-loop) zanim trafi do `config/aliases.yml`. Propozycje nieznanych nazw czekają w `data/pending/aliases.yml`.
_Avoid_: mapowanie, słownik (słownik to zbiór aliasów, nie pojedynczy wpis)

**Rekord**:
Pojedynczy pomiar w magazynie: `panel`, `marker`, `marker_raw`, `value`, `value_text`, `unit`, `reference_low`/`reference_high`, `reference_note`, `exam_date`, `source_file`. Płaski, schemat BigQuery-ready.
_Avoid_: wpis, wiersz

**Seria pomiarowa**:
Ciąg rekordów tego samego markera **i tej samej jednostki** (para `marker` + `unit`), uporządkowany po `exam_date`. Grupowanie tylko po `marker` myli różne serie pod tym samym kodem (np. NEU w % i NEU w tys/µl to dwie różne serie).
_Avoid_: trend (trend to interpretacja serii, nie sama sekwencja danych), historia markera

**Zaufany magazyn**:
`data/store/structural-backfill.ndjson` — jedyny plik czytany domyślnie przez raport i BigQuery. Zmienia się wyłącznie przez ręczne scalenie potwierdzonej migawki, nigdy przez bezpośredni zapis pipeline'u.
_Avoid_: magazyn, store, baza danych

**Migawka-kandydat**:
`data/store/YYYY-MM-DD-structural.ndjson` — wynik pojedynczego przebiegu `structural_pipeline.py`, niezweryfikowany. Nie staje się zaufanym magazynem automatycznie — wymaga jawnej prośby operatora po weryfikacji raportu.
_Avoid_: snapshot, backup

## Kontekst V2 — MCP server

**Klient MCP**:
Aplikacja świadomie skonfigurowana przez operatora do rozmowy z serwerem (Claude Code, Claude Desktop, inne) — nie dowolny proces w systemie. Serwer udostępnia wyłącznie odczyt zaufanego magazynu; mechanika zatwierdzania aliasów zostaje plikowa, jak w V1. Decyzje techniczne (transport, SDK) w `docs/adr/`.
_Avoid_: użytkownik (użytkownik to operator; klient to aplikacja, przez którą operator się łączy)
