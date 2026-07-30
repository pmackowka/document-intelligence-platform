"""Wspólny moduł logiki domenowej — magazyn NDJSON, reużywany przez report.py i serwer MCP.

Wydzielony, żeby serwer MCP (etap 3) nie musiał importować ze skryptu CLI (report.py) —
PRD V2, Tech Constraints, "Reużycie kodu".
"""
from __future__ import annotations

import json
from difflib import get_close_matches
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "data" / "store" / "structural-backfill.ndjson"
LABELS = ROOT / "config" / "marker_labels.yml"


def load_records(store_path: Path = STORE) -> list[dict]:
    if not store_path.exists():
        return []
    with store_path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def load_labels() -> dict[str, str]:
    data = yaml.safe_load(LABELS.read_text(encoding="utf-8")) if LABELS.exists() else {}
    return (data or {}).get("labels", {})


class MarkerNotFound(Exception):
    """Identyfikator markera (kod kanoniczny lub polska etykieta) nie został rozpoznany."""

    def __init__(self, identifier: str, suggestions: list[str]):
        self.identifier = identifier
        self.suggestions = suggestions
        hint = f" Czy chodziło o: {', '.join(suggestions)}?" if suggestions else ""
        super().__init__(f"Nieznany marker: {identifier!r}.{hint}")


def resolve_marker(identifier: str, labels: dict[str, str] | None = None) -> str:
    """Zwraca kanoniczny kod markera dla podanego kodu lub polskiej etykiety (marker_labels.yml).

    Dopasowanie bez rozróżniania wielkości liter. Nierozpoznany identyfikator rzuca
    MarkerNotFound z podpowiedzią najbliższych dopasowań — nigdy cicha pusta lista,
    żeby literówki nie myliły się z "marker istnieje, zero pomiarów".
    """
    if labels is None:
        labels = load_labels()

    query_lower = (identifier or "").strip().lower()
    code_by_lower = {code.lower(): code for code in labels}
    label_by_lower = {label.strip().lower(): code for code, label in labels.items()}

    if query_lower in code_by_lower:
        return code_by_lower[query_lower]
    if query_lower in label_by_lower:
        return label_by_lower[query_lower]

    candidates = {**code_by_lower, **label_by_lower}
    close = get_close_matches(query_lower, candidates.keys(), n=3, cutoff=0.6)
    suggestions = sorted({candidates[c] for c in close})
    raise MarkerNotFound(identifier, suggestions)
