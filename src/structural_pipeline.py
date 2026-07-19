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

_NUM = re.compile(r"^[<>]?\s*\d+(?:[.,]\d+)?$")       # cała komórka to liczba: 13.2, 0,18, <1
_ICD9 = re.compile(r"ICD-9:\s*([A-Z]\d+)")            # ścisły: kod panelu w komórce tabeli
_ICD9_LOOSE = re.compile(r"\(ICD-9:\s*([^)]*)\)")     # luźny: dowolny kod inline (też "-", "055")
_RANGE = re.compile(r"^(\d+(?:[.,]\d+)?)\s+(\d+(?:[.,]\d+)?)(?:\s+[HLNhln*])?$")  # "115,00 190,00 H"
_DATE = re.compile(r"Data wykonania\s*:?\s*(\d{2})\.(\d{2})\.(\d{4})")


def to_num(cell: str):
    """Zwraca float, jeśli cała komórka jest liczbą; inaczej None (chroni przed cyframi z dat)."""
    cell = cell.strip()
    if _NUM.match(cell):
        return float(re.sub(r"[<>\s]", "", cell).replace(",", "."))
    return None


def canon_unit(cell: str):
    cell = html.unescape(cell).strip()  # Docling escapuje '|' (delimiter tabeli) jako &#124;
    return UNITS.get(norm(cell), cell or None) if cell else None


def exam_date(text: str):
    m = _DATE.search(text)
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def is_separator(cells: list[str]) -> bool:
    return all(set(c) <= set("-: ") for c in cells)


# Linie-szum nagłówka/stopki (żeby nie wziąć ich za marker ani za wartość jakościową).
_NOISE = re.compile(
    r"^(data |badanie wykonano|dot\. materia|kod |oddzial|adres|pesel|plec|"
    r"wynik|jedn|min|max|flaga|pacjent|badanie|lek\.kier|odbiorca|dok\.)", re.I
)


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
    if _NUM.match(s):
        return float(re.sub(r"[<>\s]", "", s).replace(",", "."))
    return None


def parse_section_chunk(chunk: list[str], inline_val: str | None):
    """Z linii NALEŻĄCYCH do markera sekcyjnego wyciąga (value, value_text, unit, lo, hi).

    Format sekcyjny: wartość/jednostka/zakres rozrzucone w kolejnych liniach, przeplecione
    szumem (daty, opis metody, tekst referencyjny). Zbieramy zachłannie, pomijając szum.
    Zakres bierzemy WYŁĄCZNIE z linii czysto-liczbowych — prozę z liczbami ("Poniżej 150 mg/dl")
    ignorujemy, żeby nie zassać liczb z tekstu referencyjnego.
    """
    value = value_text = unit = None
    range_nums: list[float] = []
    if inline_val:                       # wartość w tej samej linii co nazwa ("Kwas moczowy (...) 5,6")
        value = _num(inline_val)
        value_text = None if value is not None else inline_val

    for raw in chunk:
        s = html.unescape(raw.strip()).lstrip("#").strip()
        if not s or is_noise(raw):
            continue
        if unit is None and norm(s) in UNITS:            # jednostka
            unit = UNITS[norm(s)]
            continue
        mr = _RANGE.match(s)                             # "115,00 190,00 H" -> para MIN/MAX
        if mr:
            range_nums += [float(mr.group(1).replace(",", ".")), float(mr.group(2).replace(",", "."))]
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

    lo = hi = None
    if len(range_nums) >= 2:
        lo, hi = sorted(range_nums[:2])                  # OCR bywa odwraca kolejność MIN/MAX -> sortuj
    elif len(range_nums) == 1:
        hi = range_nums[0]                               # pojedynczy próg referencyjny -> górna granica
    return value, value_text, unit, lo, hi


def _record(panel, marker, name_raw, value, value_text, unit, lo, hi, date, source) -> dict:
    return {
        "record_type": "structural", "panel": panel, "marker": marker,
        "marker_raw": name_raw, "value": value, "value_text": value_text,
        "unit": unit, "reference_low": lo, "reference_high": hi,
        "exam_date": date, "source_file": source,
    }


def parse_document(text: str, source: str) -> tuple[list[dict], list[tuple[str, str]]]:
    """Zwraca (rekordy, nieznane). Dwie ścieżki, wybierane per-linia:

    - TABELA (linia zaczyna się od '|'): parsowanie pozycyjne nazwa|wynik|jedn|MIN|MAX.
    - SEKCJA (format luźny): marker to linia z inline '(ICD-9: kod)' albo nazwa-dziecko pod
      nagłówkiem sekcji; wartość/jednostka/zakres zbierane z kolejnych linii (Pass 2).

    Gwarancja S1 (nie gubić po cichu): nierozpoznana nazwa w tabeli oraz nierozpoznana linia
    markera z realnym kodem ICD w sekcji trafiają do `unknown` (Warstwa 3), nigdy nie znikają.
    """
    date = exam_date(text)
    lines = text.splitlines()
    panel = None
    section_active = False
    records, unknown = [], []
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
            if marker is None:
                unknown.append((panel or "?", name_raw))
                continue
            value = to_num(cells[1])
            records.append(_record(
                panel, marker, name_raw, value,
                None if value is not None else (cells[1] or None),
                canon_unit(cells[2]) if len(cells) > 2 else None,
                to_num(cells[3]) if len(cells) > 3 else None,
                to_num(cells[4]) if len(cells) > 4 else None,
                date, source))
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
                anchors.append((i, panel, canon, name_before, line[m.end():].strip() or None))
                continue
            # (d) nierozpoznana linia markera z ICD -> flaguj, o ile kod wygląda realnie (nie "-")
            section_active = True
            if name_before and not is_noise(name_before) and _valid_code(code):
                unknown.append((panel or "?", name_before))
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
        value, value_text, unit, lo, hi = parse_section_chunk(lines[i + 1:end], inline_val)
        if value is None and value_text is None and unit is None and lo is None and hi is None:
            continue  # anchor-widmo (np. nazwa markera powtórzona w nagłówku sekcji) — brak treści, pomiń
        records.append(_record(p, canon, name_raw, value, value_text, unit, lo, hi, date, source))

    return records, unknown


_CODE_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,29}")


def sanitize_alias(out: str) -> str:
    """Przyjmij WYŁĄCZNIE pojedynczy token wyglądający jak kod; zdania/odmowy -> NEEDS_REVIEW.
    Haiku bywa zwraca prozę ('Nie ma takiego markera w configu...') zamiast kodu — odrzucamy ją,
    żeby do pending nie trafiały śmieci wymagające ręcznego czyszczenia."""
    token = out.strip().splitlines()[0].strip().strip("`'\"").strip() if out.strip() else ""
    return token if _CODE_RE.fullmatch(token) else "NEEDS_REVIEW"


def propose_alias_haiku(panel: str, name_raw: str) -> str:
    """Warstwa 3: Haiku proponuje kanoniczny kod dla nieznanej nazwy. Wysyła TYLKO nazwę markera."""
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


def main() -> int:
    docs = sorted(p for p in RAW.iterdir() if p.is_file() and p.suffix.lower() in DOC_EXTS) if RAW.exists() else []
    if not docs:
        print(f"Brak dokumentów w {RAW}", file=sys.stderr)
        return 1
    STORE.mkdir(parents=True, exist_ok=True)
    PENDING.mkdir(parents=True, exist_ok=True)

    all_records, all_unknown = [], {}
    for doc in docs:
        recs, unknown = parse_document(ocr_markdown(doc), doc.stem)
        all_records.extend(recs)
        for panel, name in unknown:
            all_unknown.setdefault((panel, norm(name)), (panel, name))
        print(f"{doc.name[:46]:46s} rekordów={len(recs):3d} nieznanych={len(unknown):2d}", flush=True)

    # zapis NDJSON (dev: nadpisujemy; produkcyjnie append-only)
    out = STORE / "structural.ndjson"
    with out.open("w", encoding="utf-8") as fh:
        for r in all_records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nZapisano {len(all_records)} rekordów -> {out}")

    # Warstwa 3: propozycje aliasów dla nieznanych -> pending/
    if all_unknown:
        print(f"Warstwa 3: {len(all_unknown)} nieznanych nazw -> Haiku proponuje aliasy...")
        proposals = {}
        for panel, name in all_unknown.values():
            proposals.setdefault(panel, {})[name] = propose_alias_haiku(panel, name)
        pend = PENDING / "aliases.yml"
        pend.write_text(yaml.safe_dump({"pending_panels": proposals}, allow_unicode=True, sort_keys=False),
                        encoding="utf-8")
        print(f"Propozycje -> {pend} (operator zatwierdza, przenosząc do config/aliases.yml)")
    else:
        print("Brak nieznanych markerów — wszystkie zmapowane.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
