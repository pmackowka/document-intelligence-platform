"""Spike OCR (etap 1): Docling na próbce strukturalnej i narracyjnej.

Kod spike'owy — celem są twarde wnioski o jakości OCR, nie produkcyjna elegancja.

Wejście:  data/raw/{structural,narrative}/*
Wyjście:  data/interim/ocr-spike/{structural,narrative}/<nazwa>.md + .json
Na końcu: tabela podsumowania (format, strony, znaki, tabele, czas, status).

Skrypt jest w pełni lokalny — żaden tekst nie opuszcza maszyny (reguła: nic do
zewnętrznego API przed Presidio).
"""
from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

from docling.document_converter import DocumentConverter

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "interim" / "ocr-spike"

CLASSES = ["structural", "narrative"]
EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".heic", ".tif", ".tiff"}


def gather() -> list[tuple[str, Path]]:
    """Zbiera pliki z obu podfolderów klasy, zachowując etykietę klasy."""
    files: list[tuple[str, Path]] = []
    for cls in CLASSES:
        d = RAW / cls
        if not d.exists():
            continue
        for f in sorted(d.iterdir()):
            if f.is_file() and f.suffix.lower() in EXTS:
                files.append((cls, f))
    return files


def main() -> int:
    files = gather()
    if not files:
        print("Brak plików w data/raw/{structural,narrative}/", file=sys.stderr)
        return 1

    # Jeden konwerter dla całej próbki — modele ładują się raz.
    conv = DocumentConverter()
    rows = []

    for cls, f in files:
        outdir = OUT / cls
        outdir.mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        status, pages, chars, ntables = "OK", 0, 0, 0
        try:
            res = conv.convert(str(f))
            doc = res.document
            md = doc.export_to_markdown()
            data = doc.export_to_dict()
            (outdir / (f.stem + ".md")).write_text(md, encoding="utf-8")
            (outdir / (f.stem + ".json")).write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            pages = len(getattr(doc, "pages", []) or [])
            chars = len(md)
            ntables = len(getattr(doc, "tables", []) or [])
        except Exception as e:  # spike: łapiemy wszystko, zapisujemy traceback obok
            status = f"FAIL:{type(e).__name__}"
            (outdir / (f.stem + ".error.txt")).write_text(
                traceback.format_exc(), encoding="utf-8"
            )
        dt = time.time() - t0
        rows.append((cls, f.name, f.suffix.lower(), pages, chars, ntables, dt, status))
        print(
            f"[{status:14s}] {cls:10s} {f.name[:45]:45s} "
            f"strony={pages:2d} znaki={chars:6d} tabele={ntables:2d} {dt:6.1f}s",
            flush=True,
        )

    print("\n==== PODSUMOWANIE ====")
    print(f"{'klasa':10s} {'plik':45s} {'fmt':6s} {'str':>3s} {'znaki':>7s} {'tab':>3s} {'czas':>7s} status")
    for cls, name, ext, pages, chars, ntables, dt, status in rows:
        print(f"{cls:10s} {name[:45]:45s} {ext:6s} {pages:3d} {chars:7d} {ntables:3d} {dt:6.1f}s {status}")
    ok = sum(1 for r in rows if r[-1] == "OK")
    print(f"\nOK: {ok}/{len(rows)}  |  wyjście: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
