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
from PIL import Image
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import OcrMacOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, ImageFormatOption, PdfFormatOption

Image.MAX_IMAGE_PIXELS = None  # własne pliki — wyłącz strażnik decompression-bomb (duże skany)

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
RAW = ROOT / "data" / "raw" / "structural"
OCR_CACHE = ROOT / "data" / "interim" / "structural-ocr"
STORE = ROOT / "data" / "store"
PENDING = ROOT / "data" / "pending"
DOC_EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".heic", ".tif", ".tiff"}

# --- normalizacja klucza: lowercase, bez polskich diakrytyków, bez gwiazdek, spacje zwarte ---
_DIACR = str.maketrans("ąćęłńóśźż", "acelnoszz")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().translate(_DIACR).replace("*", "").strip())


def load_yaml(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}


ALIASES = load_yaml(CONFIG / "aliases.yml")
UNITS = load_yaml(CONFIG / "units.yml").get("aliases", {})
PANELS = ALIASES.get("panels", {})
PANEL_BY_ICD = {icd: name for name, p in PANELS.items() for icd in p.get("icd9", [])}

_NUM = re.compile(r"^[<>]?\s*\d+(?:[.,]\d+)?$")       # cała komórka to liczba: 13.2, 0,18, <1
_ICD9 = re.compile(r"ICD-9:\s*([A-Z]\d+)")
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


def is_noise(text_line: str) -> bool:
    s = norm(text_line.lstrip("#").strip())
    return not s or "icd-9" in s or bool(_NOISE.match(s))


def _record(panel, marker, name_raw, value, value_text, unit, lo, hi, date, source) -> dict:
    return {
        "record_type": "structural", "panel": panel, "marker": marker,
        "marker_raw": name_raw, "value": value, "value_text": value_text,
        "unit": unit, "reference_low": lo, "reference_high": hi,
        "exam_date": date, "source_file": source,
    }


def parse_document(text: str, source: str) -> tuple[list[dict], list[tuple[str, str]]]:
    """Zwraca (rekordy, nieznane). Obsługuje tabele (pozycyjnie) i luźne linie (serologia jakościowa)."""
    date = exam_date(text)
    panel = None
    records, unknown = [], []
    lines = text.splitlines()

    for i, line in enumerate(lines):
        m = _ICD9.search(line)
        if m:
            panel = PANEL_BY_ICD.get(m.group(1))  # None, jeśli panel nieznany
        stripped = line.strip()

        if stripped.startswith("|"):  # --- wiersz tabeli: parsowanie pozycyjne ---
            cells = split_row(line)
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

        else:  # --- luźna linia: wynik jakościowy (serologia, krew utajona) ---
            key = norm(stripped.lstrip("#").strip())
            marker = resolve(panel, key)
            if marker is None:
                continue  # nieznanego markera nie odróżnimy od szumu w luźnej linii
            value_text = None
            for j in range(i + 1, min(i + 6, len(lines))):
                if lines[j].strip() and not is_noise(lines[j]):
                    value_text = lines[j].strip().lstrip("#").strip()
                    break
            records.append(_record(panel, marker, stripped.lstrip("#").strip(),
                                    None, value_text, None, None, None, date, source))
    return records, unknown


def propose_alias_haiku(panel: str, name_raw: str) -> str:
    """Warstwa 3: Haiku proponuje kanoniczny kod dla nieznanej nazwy. Wysyła TYLKO nazwę markera."""
    prompt = (
        f"Podaj kanoniczny kod markera laboratoryjnego dla polskiej nazwy "
        f"'{name_raw}' w panelu '{panel}'. Preferuj międzynarodowy skrót "
        f"(np. WBC, CRP), inaczej krótki angielski snake_case. Zwróć SAMĄ nazwę, bez wyjaśnień."
    )
    out = subprocess.run(
        ["claude", "-p", prompt, "--model", "haiku"],
        capture_output=True, text=True, timeout=60, check=True,
    ).stdout.strip()
    return out.splitlines()[0].strip() if out else "UNKNOWN"


_CONV = None


def _ocr_converter() -> DocumentConverter:
    """Apple Vision (pl-PL), wymuszony pełny OCR — decyzja z etapu 1 (zepsuta warstwa tekstowa)."""
    opts = PdfPipelineOptions()
    opts.do_ocr = True
    opts.ocr_options = OcrMacOptions(lang=["pl-PL"])
    opts.ocr_options.force_full_page_ocr = True
    return DocumentConverter(format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=opts),
        InputFormat.IMAGE: ImageFormatOption(pipeline_options=opts),
    })


def ocr_markdown(doc: Path) -> str:
    """OCR dokumentu -> markdown; cache w OCR_CACHE (re-run pomija OCR)."""
    global _CONV
    cached = OCR_CACHE / (doc.stem + ".md")
    if cached.exists():
        return cached.read_text(encoding="utf-8")
    if _CONV is None:
        _CONV = _ocr_converter()
    md = _CONV.convert(str(doc)).document.export_to_markdown()
    OCR_CACHE.mkdir(parents=True, exist_ok=True)
    cached.write_text(md, encoding="utf-8")
    return md


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
