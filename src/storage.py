"""Wspólny moduł logiki domenowej — magazyn NDJSON, reużywany przez report.py i serwer MCP.

Wydzielony, żeby serwer MCP (etap 3) nie musiał importować ze skryptu CLI (report.py) —
PRD V2, Tech Constraints, "Reużycie kodu".
"""
from __future__ import annotations

import json
from collections import defaultdict
from difflib import get_close_matches
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "data" / "store" / "structural-backfill.ndjson"
LABELS = ROOT / "config" / "marker_labels.yml"
REPORTS = ROOT / "data" / "reports"


def load_records(store_path: Path = STORE) -> list[dict]:
    if not store_path.exists():
        return []
    with store_path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def load_labels() -> dict[str, str]:
    data = yaml.safe_load(LABELS.read_text(encoding="utf-8")) if LABELS.exists() else {}
    return (data or {}).get("labels", {})


def latest_report(reports_dir: Path = REPORTS) -> Path | None:
    """Najnowszy raport wg nazwy pliku (`YYYY-MM-DD-trendy.md` — sortowanie leksykograficzne
    == chronologiczne dzięki formatowi ISO). None, gdy katalog nie istnieje albo jest pusty —
    wywołujący decyduje, jak to zakomunikować (nigdy cicha pustka bez wyjaśnienia, ta sama
    zasada co przy MarkerNotFound)."""
    if not reports_dir.exists():
        return None
    reports = sorted(reports_dir.glob("*.md"))
    return reports[-1] if reports else None


class MarkerNotFound(Exception):
    """Identyfikator markera (kod kanoniczny lub polska etykieta) nie został rozpoznany."""

    def __init__(self, identifier: str, suggestions: list[str]):
        self.identifier = identifier
        self.suggestions = suggestions
        hint = f" Czy chodziło o: {', '.join(suggestions)}?" if suggestions else ""
        super().__init__(f"Nieznany marker: {identifier!r}.{hint}")


def _prefix_aliases(labels: dict[str, str], code_by_lower: dict[str, str]) -> dict[str, str]:
    """Skrót przed nawiasem w etykiecie (np. "OB (odczyn Biernackiego)" -> "ob") jako
    dodatkowy alias — dla skrótów, które są krótsze niż cała etykieta i przez to
    zbyt odległe dla dopasowania rozmytego (difflib porównuje długości całych ciągów).
    Prefiks pomijany, jeśli koliduje z kodem innego markera — nie zgadujemy, o który
    marker chodziło (np. "PTH (1-84)" dałoby prefiks "pth", który już jest kodem
    markera "PTH" — inna etykieta, "PTH (parathormon)")."""
    prefix_by_lower: dict[str, str] = {}
    ambiguous: set[str] = set()
    for code, label in labels.items():
        if " (" not in label:
            continue
        prefix = label.split(" (", 1)[0].strip().lower()
        existing = prefix_by_lower.get(prefix) or code_by_lower.get(prefix)
        if existing and existing != code:
            ambiguous.add(prefix)
        else:
            prefix_by_lower[prefix] = code
    return {k: v for k, v in prefix_by_lower.items() if k not in ambiguous}


def resolve_marker(identifier: str, labels: dict[str, str] | None = None) -> str:
    """Zwraca kanoniczny kod markera dla podanego kodu, polskiej etykiety (marker_labels.yml)
    lub skrótu przed nawiasem w etykiecie (np. "OB" dla "OB (odczyn Biernackiego)").

    Dopasowanie bez rozróżniania wielkości liter. Nierozpoznany identyfikator rzuca
    MarkerNotFound z podpowiedzią najbliższych dopasowań — nigdy cicha pusta lista,
    żeby literówki nie myliły się z "marker istnieje, zero pomiarów".
    """
    if labels is None:
        labels = load_labels()

    query_lower = (identifier or "").strip().lower()
    code_by_lower = {code.lower(): code for code in labels}
    label_by_lower = {label.strip().lower(): code for code, label in labels.items()}
    prefix_by_lower = _prefix_aliases(labels, code_by_lower)

    if query_lower in code_by_lower:
        return code_by_lower[query_lower]
    if query_lower in label_by_lower:
        return label_by_lower[query_lower]
    if query_lower in prefix_by_lower:
        return prefix_by_lower[query_lower]

    candidates = {**code_by_lower, **label_by_lower, **prefix_by_lower}
    close = get_close_matches(query_lower, candidates.keys(), n=3, cutoff=0.6)
    suggestions = sorted({candidates[c] for c in close})
    raise MarkerNotFound(identifier, suggestions)


def group_by_unit(records: list[dict]) -> dict[str | None, list[dict]]:
    """Grupuje rekordy jednego markera po jednostce.

    Rekordy bez jednostki (parser jej nie znalazł w konkretnym dokumencie) dołączają
    do jedynej realnej (niepustej) jednostki, jeśli marker ma tylko jedną — inaczej
    ta sama seria rozpadałaby się na kilka tabel bez powodu klinicznego. Gdy realnych
    jednostek jest >=2 (różne skale pod tym samym kodem, np. NEU w % i w tys/µl),
    rekordy bez jednostki zostają w osobnej grupie (klucz None) — nie zgadujemy,
    do której skali należą.
    """
    real_units = {r["unit"] for r in records if r["unit"]}
    if len(real_units) <= 1:
        return {next(iter(real_units), None): records}
    groups: dict[str | None, list[dict]] = defaultdict(list)
    for r in records:
        groups[r["unit"]].append(r)
    return dict(groups)


SERIES_FIELDS = (
    "exam_date",
    "value",
    "value_text",
    "unit",
    "reference_low",
    "reference_high",
    "reference_note",
    "source_file",
)


def marker_series(code: str, records: list[dict]) -> list[dict]:
    """Zwraca serie już rozpoznanego kodu markera, pogrupowane po jednostce.

    Wejściem jest pełny magazyn (`load_records()`) — funkcja sama filtruje po kodzie.
    Wyjście to surowe rekordy (PRD V2: zero interpretacji — kierunek trendu, delta itd.
    to rola modelu wywołującego narzędzie MCP, nie tej funkcji), posortowane po dacie
    badania w obrębie każdej jednostki.
    """
    marker_records = [r for r in records if r["marker"] == code]
    groups = group_by_unit(marker_records)
    return [
        {
            "unit": unit,
            "records": [
                {field: r.get(field) for field in SERIES_FIELDS}
                for r in sorted(rows, key=lambda r: r["exam_date"] or "")
            ],
        }
        for unit, rows in sorted(groups.items(), key=lambda kv: kv[0] or "")
    ]
