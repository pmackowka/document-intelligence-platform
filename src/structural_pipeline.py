"""Etap 3 — pipeline strukturalny: OCR-owany markdown badania -> kanoniczny NDJSON.

Warstwa 1: aliasy (config/aliases.yml, panel-aware) -> kanoniczna nazwa markera.
Warstwa 2: regex -> wartość liczbowa/jakościowa; jednostka (units.yml); zakres MIN/MAX z dokumentu.
Warstwa 3: nieznana nazwa -> `claude -p --model haiku` -> propozycja do data/pending/aliases.yml.

Pipeline czyta WYŁĄCZNIE zatwierdzone aliasy z config/. Parsowanie jest LOKALNE
(regex/słownik). Do API idzie wyłącznie sama nazwa markera (Warstwa 3) — bez PII.

Parsowanie tabel jest POZYCYJNE (kolumny: nazwa | wynik | jedn. | MIN | MAX),
nie po nagłówkach — bo OCR gubi nagłówki niespójnie między stronami (wniosek etapu 1).
"""
from __future__ import annotations

import html
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml

from ocr import ocr_markdown as _ocr_markdown
from ocr import DOC_EXTS

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
RAW = ROOT / "data" / "raw" / "structural"
OCR_CACHE = ROOT / "data" / "interim" / "structural-ocr"
STORE = ROOT / "data" / "store"
PENDING = ROOT / "data" / "pending"

# Etap 4 (backfill): próg odrzucenia "nieczytelny OCR". Kalibrowany na realnych danych —
# najkrótszy prawdziwy dokument w próbce etapu 2 miał 710 znaków; puste/nieczytelne
# dokumenty (placeholder OCR) obserwowane w projekcie miały 14-394 znaków. 500 leży
# bezpiecznie w przerwie między obiema grupami (margines ~200 w obie strony).
MIN_OCR_CHARS = 500

# --- normalizacja klucza: lowercase, bez polskich diakrytyków, bez gwiazdek, spacje zwarte ---
_DIACR = str.maketrans("ąćęłńóśźż", "acelnoszz")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().translate(_DIACR).replace("*", "").strip())


def load_yaml(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}


ALIASES = load_yaml(CONFIG / "aliases.yml")
UNITS = load_yaml(CONFIG / "units.yml").get("aliases", {})
PANELS = ALIASES.get("panels", {})

# Panele tabelaryczne: kod ICD-9 z nagłówka -> nazwa panelu (ustawia bieżący panel).
TABLE_PANEL_BY_ICD = {
    icd: name for name, p in PANELS.items()
    if p.get("format") == "table" for icd in p.get("icd9", [])
}
# Panele sekcyjne, których nagłówek (z kodem ICD) wprowadza markery-dzieci: serologia, lipidogram.
SECTION_PANEL_BY_ICD = {
    icd: name for name, p in PANELS.items()
    if p.get("format") == "section" for icd in p.get("icd9", [])
}
# Markery sekcyjne rozpoznawane po NAZWIE (kod ICD bywa popsuty: "-", "055"):
#   znormalizowana nazwa -> (panel, kod kanoniczny). Nazwy są unikalne między panelami sekcyjnymi.
SECTION_MARKERS = {
    key: (name, canon) for name, p in PANELS.items()
    if p.get("format") == "section" for key, canon in p.get("markers", {}).items()
}
# Fallback bez podziału na panel/format — WYŁĄCZNIE dla tabel, którym nigdy nie udało się
# ustalić panelu (nowy lab, tabela bez rozpoznawalnego nagłówka ICD-9). Używany tylko gdy
# `panel is None` przez cały dokument — jeśli panel JEST znany, ale klucz nie ma w nim wpisu,
# to nadal trafia do `unknown` (nie zgadujemy między panelami, gdy kontekst jest jednoznaczny).
ALL_MARKERS = {
    key: (name, canon) for name, p in PANELS.items()
    for key, canon in p.get("markers", {}).items()
}

_NUM = re.compile(r"^([<>]?\s*\d+(?:[.,]\d+)?)(?:\s+[HLNhln*])?$")  # liczba, opcjonalnie z flagą "H"/"L" (OCR bywa łączy z granicą zakresu w jednej linii, np. "190,00 H")
_ICD9 = re.compile(r"ICD-9:\s*([A-Z]\d+)")            # ścisły: kod panelu w komórce tabeli
_ICD9_LOOSE = re.compile(r"\(ICD-9:\s*([^)]*)\)")     # luźny: dowolny kod inline (też "-", "055")
_BRACKET_CODE = re.compile(r"^\[[A-Z0-9]+\]\s*\S")    # inny lab, wewnętrzny kod jako PREFIKS: "[L23] Fosforany"
_RANGE = re.compile(r"^(\d+(?:[.,]\d+)?)\s+(\d+(?:[.,]\d+)?)(?:\s+[HLNhln*])?$")  # "115,00 190,00 H"
# Etap 4 (backfill): pierwotnie tylko jeden format jednego labu ("Data wykonania: DD.MM.YYYY").
# Inne laby piszą tę samą informację innym słowem/formatem — 27% rekordów zostawało bez daty,
# mimo że data była wprost w tekście. Kolejność ma znaczenie: pierwsze trafienie wygrywa, więc
# oryginalny wzorzec zostaje pierwszy (zero ryzyka regresji na już poprawnie działających dok.).
_DATE_FORMATS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"Data wykonania\s*:?\s*(\d{2})\.(\d{2})\.(\d{4})"), "dmy"),
    (re.compile(r"Data(?:/godz\.?)?\s*(?:rejestracji|pobrania)\s*:?\s*(\d{4})-(\d{2})-(\d{2})"), "ymd"),
    (re.compile(r"data i godz(?:ina)?\.?\s*pobrania\s*:?\s*(\d{2})-(\d{2})-(\d{4})"), "dmy"),
    (re.compile(r"data i godz\.?\s*przyj[ęe]cia\s*:?\s*(\d{2})-(\d{2})-(\d{4})"), "dmy"),  # fallback: kolekcji "nie podano"
]


def to_num(cell: str):
    """Zwraca float, jeśli cała komórka jest liczbą; inaczej None (chroni przed cyframi z dat)."""
    cell = cell.strip()
    m = _NUM.match(cell)
    if m:
        return float(re.sub(r"[<>\s]", "", m.group(1)).replace(",", "."))
    return None


# Etap 4 (backfill): niektóre laby nie mają osobnych kolumn jednostka|MIN|MAX — zakres
# referencyjny przychodzi jako JEDNA komórka ("17,1 — 77,6" albo jednostronnie "< 5,61"),
# czasem w miejscu, gdzie pozycyjny parser oczekuje jednostki. Bez tej detekcji taka komórka
# była cicho zapisywana jako "jednostka" (dane błędne, nie tylko brakujące — gorsze niż NULL).
# Limit 1-3 cyfr przed przecinkiem odróżnia realny zakres referencyjny od zlepionej przez OCR
# daty w sąsiedniej kolumnie (np. "14-52026" ma 5 cyfr po myślniku -> odrzucone, nie zakres).
_RANGE_CELL = re.compile(r"^(-?\d{1,3}(?:[.,]\d+)?)\s*[-—–]\s*(-?\d{1,3}(?:[.,]\d+)?)$")
_BOUND_CELL = re.compile(r"^([<>≤≥])\s*(\d{1,3}(?:[.,]\d+)?)$")


def _range_from_cell(cell: str | None) -> tuple[float | None, float | None]:
    """Rozpoznaje komórkę-zakres ('17,1 — 77,6') albo jednostronną granicę ('< 5,61').
    Zwraca (lo, hi) albo (None, None), jeśli komórka nie ma takiego kształtu."""
    if not cell:
        return None, None
    # Dopisek w nawiasie ("(Parametr nieakredytowany)", przed albo po liczbach) łamał ścisłe
    # dopasowanie całej komórki — usuwamy go, zakres zostaje ("0,00 - 0,01 (Parametr...)" -> "0,00 - 0,01").
    c = re.sub(r"\([^)]*\)", "", cell).strip()
    m = _RANGE_CELL.match(c)
    if m:
        return to_num(m.group(1)), to_num(m.group(2))
    m = _RANGE.match(c)               # zakres rozdzielony samą spacją, bez myślnika ("1,005 1,030") —
    if m:                               # ten sam kształt co _RANGE w formacie sekcyjnym, tu brakował
        return float(m.group(1).replace(",", ".")), float(m.group(2).replace(",", "."))
    m = _BOUND_CELL.match(c)
    if m:
        op, num = m.groups()
        val = to_num(num)
        return (None, val) if op in "<≤" else (val, None)
    return None, None


def canon_unit(cell: str):
    cell = html.unescape(cell).strip()  # Docling escapuje '|' (delimiter tabeli) jako &#124;
    return UNITS.get(norm(cell), cell or None) if cell else None


def exam_date(text: str):
    for pattern, order in _DATE_FORMATS:
        m = pattern.search(text)
        if not m:
            continue
        y, mo, d = m.groups() if order == "ymd" else m.groups()[::-1]
        return f"{y}-{mo}-{d}"
    return None


def split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def is_separator(cells: list[str]) -> bool:
    return all(set(c) <= set("-: ") for c in cells)


# Linie-szum nagłówka/stopki (żeby nie wziąć ich za marker ani za wartość jakościową).
# Rozszerzone o etap 4 (backfill, nowy format labu): nr księgi rejestrowej, daty przyjęcia/
# pobrania próbki, materiał badany (material/materiał, w tym warianty OCR "materiat"/"materia"),
# opis metody/procedury (w tym OCR M->V: "vetoda"), adnotacje "uwaga:", linia autoryzacji
# (bywa niesie fragment nazwiska lekarza + nr PWZ — realnie znaleziony przypadek, za krótki
# na zaporę PII w Warstwie 3, więc musi być odcięty tutaj, wcześniej), oraz BARE nazwy sekcji/
# paneli tego labu (BIOCHEMIA, HEMATOLOGIA, KOAGULOLOGIA, SUROWICA jako typ próbki, Komentarz) —
# to tytuły grup, nigdy nazwy pojedynczego markera. `^` na początku chroni realne markery typu
# "Magnez - surowica" (nie zaczyna się od "surowica", więc nie łapie).
_NOISE = re.compile(
    r"^(data|badanie wykonano|dot\. materia|kod |oddzial|adres|pesel|plec|"
    r"wynik|jedn|min|max|flaga|pacjent|badanie|lek\.kier|odbiorca|dok\.|"
    r"nr ksiegi|materia|metoda|vetoda|procedura|uwaga|autoryzowa|nazwa badania|"
    r"wykonano|biochemia|hematologia|koagulologia|surowica|komentarz|morfologia|"
    r"<!--|"                                    # placeholder Docling dla obrazu/grafiki, nigdy wynik
    r"bilirubina wolna \(posrednia\))", re.I     # nagłówek GRUPY (3 markery-dzieci pod spodem), nie wynik
)

# Podzbiór _NOISE: etykiety, po których w źródle następuje CZYJEŚ nazwisko (nie wynik badania).
# Używane w parse_section_chunk do wygaszenia linii BEZPOŚREDNIO PO takiej etykiecie.
_PERSON_LABEL = re.compile(r"^(pacjent|lek\.kier|odbiorca|autoryzowa)", re.I)


def resolve(panel, key):
    return PANELS.get(panel, {}).get("markers", {}).get(key) if panel else None


def resolve_section(key):
    """Marker sekcyjny po nazwie -> (panel, kod kanoniczny) lub None (nazwa rozstrzyga, nie kod ICD)."""
    return SECTION_MARKERS.get(key)


def is_noise(text_line: str) -> bool:
    s = norm(text_line.lstrip("#").strip())
    return not s or "icd-9" in s or bool(_NOISE.match(s))


def _valid_code(code: str) -> bool:
    """Czy kod ICD wygląda 'realnie' (litera+cyfry) — do decyzji o flagowaniu nieznanego markera.
    Grupujące nagłówki bez wyniku ("PSA wskaźnik (ICD-9: -)") mają kod-śmieć i nie są flagowane."""
    return bool(re.fullmatch(r"[A-Z0-9]{2,4}", code)) and any(ch.isdigit() for ch in code)


def _num(cell: str):
    """float z tokenu liczbowego (po HTML-unescape, tolerując >/<); None jeśli to nie liczba."""
    s = html.unescape(cell).strip()
    m = _NUM.match(s)
    if m:
        return float(re.sub(r"[<>\s]", "", m.group(1)).replace(",", "."))
    return None


_THRESHOLD_NOTE = re.compile(r"^[≥≤<>]\s*=?\s*\d")  # "≥ 40 mg/dl zgodnie z..." / "<100 mg/dl - dla..."


def parse_section_chunk(chunk: list[str], inline_val: str | None):
    """Z linii NALEŻĄCYCH do markera sekcyjnego wyciąga (value, value_text, unit, lo, hi, note).

    Format sekcyjny: wartość/jednostka/zakres rozrzucone w kolejnych liniach, przeplecione
    szumem (daty, opis metody, tekst referencyjny). Zbieramy zachłannie, pomijając szum.
    Zakres bierzemy WYŁĄCZNIE z linii czysto-liczbowych — prozę z liczbami ("Poniżej 150 mg/dl")
    ignorujemy, żeby nie zassać liczb z tekstu referencyjnego.

    `note`: niektóre panele (lipidogram) podają zalecany próg jako zdanie, nie czysty zakres
    ("≥ 40 mg/dl zgodnie z zaleceniami PTK i PTDL", czasem dwa progi zależne od kategorii
    ryzyka pacjenta) — takiej prozy nie da się bezpiecznie sparsować na lo/hi bez zgadywania,
    więc trafia surowo do `note` (tylko gdy lo/hi finalnie puste), zamiast zniknąć bez śladu.
    """
    value = value_text = unit = None
    range_nums: list[float] = []
    dash_range: tuple[float | None, float | None] | None = None
    note_parts: list[str] = []
    if inline_val:                       # wartość w tej samej linii co nazwa ("Kwas moczowy (...) 5,6")
        value = _num(inline_val)
        value_text = None if value is not None else inline_val

    after_person_label = False
    for raw in chunk:
        s = html.unescape(raw.strip()).lstrip("#").strip()
        if not s:
            continue
        if is_noise(raw):
            # zapamiętaj: linia BYŁA etykietą osoby (Pacjent:/Lekarz/Odbiorca/Autoryzował) ->
            # następna niepusta linia to najpewniej nazwisko, nie wynik (patrz niżej).
            after_person_label = bool(_PERSON_LABEL.match(norm(s)))
            continue
        if after_person_label:
            # wartość bezpośrednio po etykiecie osobowej — imię/nazwisko (bywa formatowane
            # jako nagłówek markdown, ".lstrip('#')" wyżej to ukrywa) — nigdy wynik badania.
            # Realny przypadek: kreatynina dostała wartość "MAĆKÓWKA PIOTR" z powtórzonego
            # nagłówka pacjenta na 2. stronie PDF. Nie filtrujemy WSZYSTKICH nagłówków w
            # chunku ogólnie — "## nie wykryto" bywa prawdziwym wynikiem jakościowym.
            after_person_label = False
            continue
        if unit is None and norm(s) in UNITS:            # jednostka
            unit = UNITS[norm(s)]
            continue
        mr = _RANGE.match(s)                             # "115,00 190,00 H" -> para MIN/MAX
        if mr:
            range_nums += [float(mr.group(1).replace(",", ".")), float(mr.group(2).replace(",", "."))]
            continue
        if dash_range is None:
            mrc = _RANGE_CELL.match(s)                   # "2,15 - 2,50" -> zakres myślnikowy, inny kształt
            if mrc:                                       # niż "MIN MAX" wyżej (był już obsłużony w tabeli,
                dash_range = (to_num(mrc.group(1)), to_num(mrc.group(2)))  # brakował w sekcji)
                continue
        if re.fullmatch(r"\d{6,}", s):                   # PESEL / ID / telefon — nigdy wynik ani zakres
            continue
        n = _num(s)                                      # pojedyncza liczba
        if n is not None:
            if value is None and value_text is None:
                value = n
                if s.startswith((">", "<")):
                    value_text = s
            else:
                range_nums.append(n)
            continue
        if value is None and value_text is None and len(s) <= 30 and len(s.split()) <= 3:
            value_text = s                               # wynik jakościowy (serologia: "niereaktywny")
            break                                        # jakościowy nie ma jedn./zakresu — stop (chroni przed PII w trailerze)
        if _THRESHOLD_NOTE.match(s):                      # próg wpleciony w zdanie — zachowaj surowo, nie parsuj
            note_parts.append(s)

    lo = hi = None
    if dash_range is not None:
        lo, hi = dash_range
    elif len(range_nums) >= 2:
        lo, hi = sorted(range_nums[:2])                  # OCR bywa odwraca kolejność MIN/MAX -> sortuj
    elif len(range_nums) == 1:
        hi = range_nums[0]                               # pojedynczy próg referencyjny -> górna granica
    note = " / ".join(note_parts) if (lo is None and hi is None and note_parts) else None
    return value, value_text, unit, lo, hi, note


def _record(panel, marker, name_raw, value, value_text, unit, lo, hi, date, source, note=None) -> dict:
    return {
        "panel": panel, "marker": marker,
        "marker_raw": name_raw, "value": value, "value_text": value_text,
        "unit": unit, "reference_low": lo, "reference_high": hi, "reference_note": note,
        "exam_date": date, "source_file": source,
    }


def parse_document(text: str, source: str) -> tuple[list[dict], list[tuple[str, str]], list[tuple[str, str]]]:
    """Zwraca (rekordy, nieznane, wątpliwe_wiersze). Dwie ścieżki, wybierane per-linia:

    - TABELA (linia zaczyna się od '|'): parsowanie pozycyjne nazwa|wynik|jedn|MIN|MAX.
    - SEKCJA (format luźny): marker to linia z inline '(ICD-9: kod)' albo nazwa-dziecko pod
      nagłówkiem sekcji; wartość/jednostka/zakres zbierane z kolejnych linii (Pass 2).

    Gwarancja S1 (nie gubić po cichu): nierozpoznana nazwa w tabeli oraz nierozpoznana linia
    markera z realnym kodem ICD w sekcji trafiają do `unknown` (Warstwa 3), nigdy nie znikają.
    `wątpliwe_wiersze` to inny przypadek: nazwa markera ROZPOZNANA, ale komórka z wynikiem
    pusta/nietypowa (nietypowy układ tabeli) — do ręcznego przeglądu, nie do Warstwy 3.
    """
    date = exam_date(text)
    lines = text.splitlines()
    panel = None
    section_active = False
    records, unknown, bad_rows = [], [], []
    anchors: list[tuple[int, str, str, str, str | None]] = []  # (idx, panel, kanon, nazwa_raw, inline_val)

    for i, line in enumerate(lines):
        stripped = line.strip()

        # --- wiersz tabeli: parsowanie pozycyjne ---
        if stripped.startswith("|"):
            section_active = False          # tabela kończy region sekcyjny
            cells = split_row(line)
            for c in cells:                 # nagłówek panelu bywa w komórce ("Morfologia krwi (ICD-9: C55)")
                mm = _ICD9.search(c)
                if mm and mm.group(1) in TABLE_PANEL_BY_ICD:
                    panel = TABLE_PANEL_BY_ICD[mm.group(1)]
            if len(cells) < 2 or is_separator(cells):
                continue
            name_raw = cells[0]
            key = norm(name_raw)
            if not key or is_noise(name_raw):
                continue
            marker = resolve(panel, key)
            row_panel = panel
            if marker is None and panel is None:  # tabela bez ustalonego panelu -> spróbuj po wszystkich
                hit = ALL_MARKERS.get(key)         # NIE nadpisuje `panel` globalnie dla reszty
                if hit:                             # dokumentu — każdy wiersz próbuje fallback osobno,
                    row_panel, marker = hit          # żeby jeden trafiony marker nie "zablokował"
            if marker is None:                      # fallbacku dla innych paneli w tej samej tabeli
                unknown.append((row_panel or "?", name_raw))
                continue
            value = to_num(cells[1])
            value_text = None if value is not None else (cells[1] or None)
            if value is not None and cells[1].strip().startswith(("<", ">")):
                # to_num() świadomie usuwa "<"/">" przy parsowaniu liczby (np. "<1" -> 1.0) —
                # bez tego wynik poniżej progu wykrywalności wyglądałby jak dokładny pomiar.
                # Zachowaj oryginalny zapis do wyświetlenia (fmt_value w report.py go preferuje).
                value_text = cells[1].strip()
            if value is None and value_text is None:
                # kolumna "wynik" pusta — u niektórych labów realny wynik przesuwa się do sąsiedniej
                # komórki (obserwowane: wiersze oflagowane jako poza normą, etap 4 backfill). Nie
                # zgadujemy, która komórka to naprawdę wynik — do ręcznego przeglądu, nie pusty rekord.
                bad_rows.append((source, name_raw))
                continue
            cell2 = cells[2] if len(cells) > 2 else None
            cell3 = cells[3] if len(cells) > 3 else None
            if cell2 == cells[1]:              # kolumna "jednostka" bywa zduplikowanym wynikiem, nie
                cell2 = None                    # jednostką (nietypowa 5-kolumnowa tabela, np. kał) —
                                                 # widoczny błąd: pH 6,0 dostawał unit="6,0" ("6 6,0" w raporcie)
            lo, hi = _range_from_cell(cell2)
            if (lo, hi) != (None, None):
                unit = None                              # kolumna "jednostka" niosła zakres, nie jednostkę
            else:
                lo, hi = _range_from_cell(cell3)
                unit = canon_unit(cell2) if cell2 else None
                if (lo, hi) == (None, None):               # ani cell2 ani cell3 nie wygląda na zakres ->
                    lo = to_num(cell3) if cell3 else None    # oryginalna logika: MIN/MAX jako 2 osobne liczby
                    hi = to_num(cells[4]) if len(cells) > 4 else None
            records.append(_record(row_panel, marker, name_raw, value, value_text, unit, lo, hi, date, source))
            continue

        # --- linia z inline '(ICD-9: kod)': nagłówek panelu / marker sekcyjny / nagłówek grupy ---
        m = _ICD9_LOOSE.search(line)
        if m:
            code = html.unescape(m.group(1)).strip()
            name_before = line[:m.start()].lstrip("#").strip()
            key = norm(name_before)
            if code in TABLE_PANEL_BY_ICD:            # (a) nagłówek panelu tabelarycznego
                panel, section_active = TABLE_PANEL_BY_ICD[code], False
                continue
            if code in SECTION_PANEL_BY_ICD:          # (b) nagłówek sekcji z dziećmi — kod ICD rozstrzyga PRZED
                panel, section_active = SECTION_PANEL_BY_ICD[code], True   # nazwą, bo nazwa nagłówka bywa == nazwie
                continue                              # markera (np. "Krew utajona w kale (ICD-9: A17)" -> FOB)
            hit = resolve_section(key)                # (c) marker sekcyjny inline (nazwa rozstrzyga)
            if hit:
                panel, canon = hit
                section_active = True
                tail = line[m.end():].strip()
                # Pojedynczy znak po kodzie ICD (cyfra, apostrof) to odnośnik do przypisu/stopki
                # ("Fosfor nieorganiczny (ICD-9: L23) 2" -> przypis 2, nie wynik) — realny wynik
                # inline ("Kwas moczowy (...) 5,6") ma zawsze >=2 znaki. Bez tego progu przypis
                # podmieniał prawdziwy wynik (z dalszej linii chunku) na samą cyfrę odnośnika.
                inline_val = tail if len(tail) >= 2 else None
                anchors.append((i, panel, canon, name_before, inline_val))
                continue
            # (d) nierozpoznana linia markera z ICD -> flaguj, o ile kod wygląda realnie (nie "-")
            section_active = True
            if name_before and not is_noise(name_before) and _valid_code(code):
                unknown.append((panel or "?", name_before))
            continue

        # --- linia z prefiksem '[XXX]': wewnętrzny kod innego labu, nie (ICD-9: ...) ---
        # Zawsze pojedynczy marker (ten lab nie używa tej notacji na nagłówki paneli/sekcji),
        # więc — inaczej niż wyżej — nie ma gałęzi (a)/(b) na dopasowanie panelu.
        clean = stripped.lstrip("#").strip()  # pogrubiona nazwa markera bywa renderowana jako nagłówek Markdown ("## [I99] ...")
        if _BRACKET_CODE.match(clean) and not is_noise(clean):
            section_active = True
            key = norm(clean)
            hit = resolve_section(key)
            if hit:
                panel, canon = hit
                anchors.append((i, panel, canon, clean, None))
            else:
                unknown.append((panel or "?", clean))
            continue

        # --- luźna linia w aktywnej sekcji: potencjalny marker-dziecko (nazwa rozstrzyga) ---
        if section_active and stripped and not is_noise(stripped):
            hit = resolve_section(norm(stripped.lstrip("#").strip()))
            if hit:
                panel, canon = hit
                anchors.append((i, panel, canon, stripped.lstrip("#").strip(), None))
            # bare nieznane -> nieodróżnialne od prozy/szumu; pomijamy (ograniczenie udokumentowane)

    # --- Pass 2: wartość/jednostka/zakres dla markerów sekcyjnych (chunk = do następnego markera) ---
    idxs = [a[0] for a in anchors]
    for n, (i, p, canon, name_raw, inline_val) in enumerate(anchors):
        end = idxs[n + 1] if n + 1 < len(anchors) else len(lines)
        value, value_text, unit, lo, hi, note = parse_section_chunk(lines[i + 1:end], inline_val)
        if value is None and value_text is None:
            if unit is not None or lo is not None or hi is not None or note is not None:
                # jednostka/zakres znalezione, ale sam wynik nie -> realny problem parsowania
                # (etap 4 audyt: CRP z jednostką "ng/ml" i pustym wynikiem), do ręcznego przeglądu
                bad_rows.append((source, name_raw))
            continue  # inaczej: anchor-widmo (nazwa markera powtórzona w nagłówku) — brak treści, cichy pomiń
        records.append(_record(p, canon, name_raw, value, value_text, unit, lo, hi, date, source, note))

    return records, unknown, bad_rows


_CODE_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,29}")


def sanitize_alias(out: str) -> str:
    """Przyjmij WYŁĄCZNIE pojedynczy token wyglądający jak kod; zdania/odmowy -> NEEDS_REVIEW.
    Haiku bywa zwraca prozę ('Nie ma takiego markera w configu...') zamiast kodu — odrzucamy ją,
    żeby do pending nie trafiały śmieci wymagające ręcznego czyszczenia."""
    token = out.strip().splitlines()[0].strip().strip("`'\"").strip() if out.strip() else ""
    return token if _CODE_RE.fullmatch(token) else "NEEDS_REVIEW"


_PII_DIGIT_RUN = re.compile(r"\d{9,}")  # PESEL (11 cyfr) / telefon (9 cyfr) — marker nigdy nie ma tak długiego ciągu


def _looks_like_pii(name_raw: str) -> bool:
    """Ostatnia lokalna zapora tuż przed wysyłką do API (Warstwa 3).

    is_noise() filtruje linie nagłówka/stopki PRZED ekstrakcją (po prefiksie: pesel/adres/pacjent/...);
    to dodatkowa kontrola na już wyciągniętym stringu, na wypadek gdyby zniekształcony OCR albo
    rozjechany layout tabeli (udokumentowane w etapie 1) wpuścił fragment nagłówka jako name_raw
    mimo to. Progi kalibrowane na realnym słowniku: najdłuższy istniejący marker ma 39 znaków/6 słów
    (`config/aliases.yml`) — 60/8 to bezpieczny margines, nie odetnie prawdziwych kandydatów.
    """
    return bool(_PII_DIGIT_RUN.search(name_raw)) or len(name_raw) > 60 or len(name_raw.split()) > 8


def propose_alias_haiku(panel: str, name_raw: str) -> str:
    """Warstwa 3: Haiku proponuje kanoniczny kod dla nieznanej nazwy. Wysyła TYLKO nazwę markera.

    Kandydat wyglądający kształtem jak PII (patrz _looks_like_pii) nigdy nie trafia do API —
    wraca NEEDS_REVIEW lokalnie, operator rozstrzyga ręcznie w pending/aliases.yml.
    """
    if _looks_like_pii(name_raw):
        print(f"[BLOCKED] {panel}: kandydat odrzucony przed wysyłką do API (kształt PII) -> NEEDS_REVIEW", flush=True)
        return "NEEDS_REVIEW"
    prompt = (
        f"Zwróć kanoniczny kod markera laboratoryjnego dla polskiej nazwy "
        f"'{name_raw}' (panel '{panel}'). Preferuj międzynarodowy skrót (np. WBC, CRP), "
        f"inaczej krótki angielski snake_case. ODPOWIEDZ WYŁĄCZNIE jednym tokenem bez spacji "
        f"i bez wyjaśnień. Jeśli nie masz pewności, zwróć dokładnie: NEEDS_REVIEW"
    )
    out = subprocess.run(
        ["claude", "-p", prompt, "--model", "haiku"],
        capture_output=True, text=True, timeout=60, check=True,
    ).stdout
    return sanitize_alias(out)


def ocr_markdown(doc: Path) -> str:
    """OCR dokumentu -> markdown; cache w OCR_CACHE (re-run pomija OCR). Silnik: src/ocr.py."""
    return _ocr_markdown(doc, OCR_CACHE)


def _load_pending_panels(path: Path) -> dict[str, dict[str, str]]:
    """Surowa struktura {panel: {nazwa: kod}} z pending/aliases.yml — punkt startowy do
    dopisywania nowych propozycji, żeby zapis po każdym markerze nie kasował poprzednich."""
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("pending_panels") or {}


def load_existing_proposals(path: Path) -> dict[tuple[str, str], str]:
    """Wczytuje pending/aliases.yml z poprzedniego (możliwe że przerwanego) runu.

    Klucz: (panel, znormalizowana nazwa) -> już zaproponowany kod. Pozwala Warstwie 3
    ominąć ponowne pytanie Haiku o marker, który już czeka na zatwierdzenie — bez tego
    przerwany w połowie backfill marnowałby wywołania API przy każdym wznowieniu.
    """
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    lookup = {}
    for panel, markers in (data.get("pending_panels") or {}).items():
        for name, code in (markers or {}).items():
            lookup[(panel, norm(name))] = code
    return lookup


def main() -> int:
    docs = sorted(p for p in RAW.iterdir() if p.is_file() and p.suffix.lower() in DOC_EXTS) if RAW.exists() else []
    if not docs:
        print(f"Brak dokumentów w {RAW}", file=sys.stderr)
        return 1
    STORE.mkdir(parents=True, exist_ok=True)
    PENDING.mkdir(parents=True, exist_ok=True)

    all_records, all_unknown, rejected, silent_zero, all_bad_rows = [], {}, [], [], []
    for i, doc in enumerate(docs, 1):
        text = ocr_markdown(doc)
        if len(text) < MIN_OCR_CHARS:
            rejected.append(doc.name)
            print(f"[{i}/{len(docs)}] {doc.name[:40]:40s} ODRZUCONY — OCR {len(text)} znaków (< {MIN_OCR_CHARS})", flush=True)
            continue
        recs, unknown, bad_rows = parse_document(text, doc.stem)
        all_records.extend(recs)
        all_bad_rows.extend(bad_rows)
        for panel, name in unknown:
            all_unknown.setdefault((panel, norm(name)), (panel, name))
        if not recs and not unknown:
            # ani rozpoznanych rekordów, ani flagi "nieznany" — dokument spoza obu znanych
            # formatów (tabela / sekcja z ICD-9), np. bare markery bez kodu. Cichy dotąd (etap 3:
            # "ograniczenie udokumentowane") -> teraz WIDOCZNY, żeby nie łamać S1 po cichu.
            silent_zero.append(doc.name)
            print(f"[{i}/{len(docs)}] {doc.name[:40]:40s} rekordów=  0 nieznanych= 0  ⚠ SPRAWDŹ RĘCZNIE (nierozpoznany format)", flush=True)
        else:
            print(f"[{i}/{len(docs)}] {doc.name[:40]:40s} rekordów={len(recs):3d} nieznanych={len(unknown):2d}", flush=True)

    # Migawka datowana — NIGDY nie nadpisuje zaufanego magazynu (structural-backfill.ndjson).
    # Scalenie ("promocja" kandydata do zaufanego pliku) wymaga ręcznej weryfikacji
    # operatora (raport wygenerowany z tej migawki) i jest wykonywane osobno.
    out = STORE / f"{date.today().isoformat()}-structural.ndjson"
    with out.open("w", encoding="utf-8") as fh:
        for r in all_records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    trusted = STORE / "structural-backfill.ndjson"
    print(f"\nZapisano {len(all_records)} rekordów -> {out} (KANDYDAT, nie zaufany magazyn)")
    print(f"Podejrzyj raport z tej migawki: uv run python src/report.py {out}")
    print(f"Po weryfikacji poproś o scalenie z {trusted}")
    if rejected:
        print(f"Odrzuconych (nieczytelny OCR): {len(rejected)}/{len(docs)} -> {', '.join(rejected)}")
    if silent_zero:
        print(f"Bez treści rozpoznanej (sprawdź ręcznie): {len(silent_zero)}/{len(docs)} -> {', '.join(silent_zero)}")
    if all_bad_rows:
        listing = ", ".join(f"{src}: {name}" for src, name in all_bad_rows)
        print(f"⚠ Wiersze z rozpoznanym markerem, ale bez możliwego do ustalenia wyniku (sprawdź układ tabeli w OCR): {len(all_bad_rows)} -> {listing}")

    # Warstwa 3: propozycje aliasów dla nieznanych -> pending/ (odporne na wznowienie po przerwaniu)
    pend = PENDING / "aliases.yml"
    if all_unknown:
        current_keys = {(panel, norm(name)) for panel, name in all_unknown.values()}
        proposals: dict[str, dict[str, str]] = {}
        for panel, markers in _load_pending_panels(pend).items():
            for name, code in (markers or {}).items():
                if (panel, norm(name)) in current_keys:  # przenieś tylko to, co WCIĄŻ jest nieznane
                    proposals.setdefault(panel, {})[name] = code  # (np. is_noise() mógł kod poprawić i zawęzić zbiór)
        reused = failed = 0
        print(f"Warstwa 3: {len(all_unknown)} nieznanych nazw -> Haiku proponuje aliasy...")
        existing = load_existing_proposals(pend)
        for panel, name in all_unknown.values():
            key = (panel, norm(name))
            if key in existing:
                reused += 1
                continue  # już w proposals z inicjalizacji powyżej — nic do zrobienia
            try:
                code = propose_alias_haiku(panel, name)
            except Exception as e:  # noqa: BLE001 — jeden padnięty marker nie może ubić pozostałych 95
                code, failed = "NEEDS_REVIEW", failed + 1
                print(f"  [BŁĄD] '{name}' ({panel}): {type(e).__name__} -> NEEDS_REVIEW, kontynuuję", flush=True)
            proposals.setdefault(panel, {})[name] = code
            pend.write_text(yaml.safe_dump({"pending_panels": proposals}, allow_unicode=True, sort_keys=False),
                            encoding="utf-8")  # zapis PO KAŻDYM markerze — crash w środku nie kasuje reszty
        # zapis końcowy ZAWSZE — jeśli wszystko zostało odzyskane (zero nowych wywołań), pętla
        # wyżej ani razu nie zapisała na dysk przefiltrowanego stanu (stare, usunięte klucze
        # np. przez rozszerzenie is_noise() zostałyby błędnie na dysku bez tego zapisu)
        pend.write_text(yaml.safe_dump({"pending_panels": proposals}, allow_unicode=True, sort_keys=False),
                        encoding="utf-8")
        if reused:
            print(f"  (w tym {reused} odzyskanych z poprzedniego runu — bez ponownego pytania Haiku)")
        if failed:
            print(f"  (w tym {failed} nieudanych wywołań -> NEEDS_REVIEW, do ręcznego uzupełnienia)")
        print(f"Propozycje -> {pend} (operator zatwierdza, przenosząc do config/aliases.yml)")
    else:
        print("Brak nieznanych markerów — wszystkie zmapowane.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
