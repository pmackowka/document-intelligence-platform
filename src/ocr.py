"""Wspólny silnik OCR (Apple Vision, pl-PL) — używany przez pipeline strukturalny i narracyjny.

Wymuszony pełny OCR (`force_full_page_ocr`) — decyzja z etapu 1 (zepsuta warstwa tekstowa w źródłach).
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import OcrMacOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, ImageFormatOption, PdfFormatOption

Image.MAX_IMAGE_PIXELS = None  # własne pliki — wyłącz strażnik decompression-bomb (duże skany)

DOC_EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".heic", ".tif", ".tiff"}

_CONV: DocumentConverter | None = None


def _converter() -> DocumentConverter:
    opts = PdfPipelineOptions()
    opts.do_ocr = True
    opts.ocr_options = OcrMacOptions(lang=["pl-PL"])
    opts.ocr_options.force_full_page_ocr = True
    return DocumentConverter(format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=opts),
        InputFormat.IMAGE: ImageFormatOption(pipeline_options=opts),
    })


def ocr_markdown(doc: Path, cache_dir: Path) -> str:
    """OCR dokumentu -> markdown; cache w cache_dir (re-run pomija OCR)."""
    global _CONV
    cached = cache_dir / (doc.stem + ".md")
    if cached.exists():
        return cached.read_text(encoding="utf-8")
    if _CONV is None:
        _CONV = _converter()
    md = _CONV.convert(str(doc)).document.export_to_markdown()
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached.write_text(md, encoding="utf-8")
    return md
