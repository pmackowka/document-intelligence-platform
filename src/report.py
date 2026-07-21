"""Etap 3 — raport Markdown "do lekarza": trendy markerów strukturalnych.

Czyta data/store/structural.ndjson (magazyn z etapu 2), grupuje rekordy wg panelu
i markera, sortuje po dacie badania i zapisuje czytelny raport do data/reports/.

Klucz grupowania to (marker, unit), nie sam marker — niektóre markery (różnicowanie
morfologii: NEU/LYM/MONO/EOS/BASO) występują w źródle w DWÓCH jednostkach na ten sam
kod (% i tys/µl, odsetek vs wartość bezwzględna); zlanie ich w jeden ciąg trendu
pomieszałoby dwie różne skale.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "data" / "store" / "structural.ndjson"
LABELS = ROOT / "config" / "marker_labels.yml"
REPORTS = ROOT / "data" / "reports"

# Nazwy paneli do nagłówków raportu — kody wewnętrzne (aliases.yml) -> czytelna polska nazwa.
PANEL_LABELS = {
    "morfologia": "Morfologia krwi",
    "biochemia": "Biochemia",
    "lipidy": "Lipidogram",
    "tarczyca": "Tarczyca",
    "psa": "PSA",
    "koprogram": "Koprogram (kał)",
    "mocz": "Badanie ogólne moczu",
    "krew_utajona": "Krew utajona w kale",
    "serologia_hbv": "Serologia HBV",
    "serologia_hcv": "Serologia HCV",
}


def load_records() -> list[dict]:
    if not STORE.exists():
        return []
    with STORE.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def load_labels() -> dict:
    data = yaml.safe_load(LABELS.read_text(encoding="utf-8")) if LABELS.exists() else {}
    return (data or {}).get("labels", {})


def fmt_value(r: dict) -> str:
    if r["value"] is not None:
        return f"{r['value']:g} {r['unit']}".strip()
    if r["value_text"] is not None:
        return str(r["value_text"])
    return "—"


def fmt_range(r: dict) -> str:
    lo, hi = r.get("reference_low"), r.get("reference_high")
    if lo is not None and hi is not None:
        return f"{lo:g}–{hi:g}"
    if hi is not None:
        return f"≤{hi:g}"
    if lo is not None:
        return f"≥{lo:g}"
    if r.get("reference_note"):  # brak czystego zakresu, ale źródło ma wytyczną w prozie — pokaż ją zamiast "—"
        return r["reference_note"]
    return "—"


def trend_arrow(values: list[float]) -> str:
    """Kierunek między pierwszym a ostatnim pomiarem liczbowym w serii (>=2 punkty)."""
    if len(values) < 2:
        return ""
    if values[-1] > values[0]:
        return " ↑"
    if values[-1] < values[0]:
        return " ↓"
    return " →"


def build_report(records: list[dict], labels: dict) -> str:
    by_panel: dict[str, dict[tuple[str, str | None], list[dict]]] = defaultdict(lambda: defaultdict(list))
    for r in records:
        by_panel[r["panel"]][(r["marker"], r["unit"])].append(r)

    lines = [f"# Raport trendów — badania strukturalne", "", f"Wygenerowano: {date.today().isoformat()}", ""]

    for panel in sorted(by_panel, key=lambda p: PANEL_LABELS.get(p, p)):
        lines.append(f"## {PANEL_LABELS.get(panel, panel)}")
        lines.append("")
        groups = by_panel[panel]
        for (marker, unit), rows in sorted(groups.items(), key=lambda kv: labels.get(kv[0][0], kv[0][0])):
            rows.sort(key=lambda r: r["exam_date"])
            label = labels.get(marker, marker)
            numeric = [r["value"] for r in rows if r["value"] is not None]
            arrow = trend_arrow(numeric)
            unit_suffix = f" ({unit})" if unit and rows[0]["value"] is not None else ""
            lines.append(f"### {label}{unit_suffix}{arrow}")
            lines.append("")
            lines.append("| Data | Wartość | Zakres ref. |")
            lines.append("|---|---|---|")
            for r in rows:
                lines.append(f"| {r['exam_date']} | {fmt_value(r)} | {fmt_range(r)} |")
            lines.append("")

    return "\n".join(lines)


def main() -> int:
    records = load_records()
    if not records:
        print("Brak rekordów w data/store/structural.ndjson — najpierw uruchom structural_pipeline.py")
        return 1
    labels = load_labels()
    report = build_report(records, labels)

    REPORTS.mkdir(parents=True, exist_ok=True)
    out = REPORTS / f"{date.today().isoformat()}-trendy.md"
    out.write_text(report, encoding="utf-8")

    n_panels = len({r["panel"] for r in records})
    n_series = len({(r["panel"], r["marker"], r["unit"]) for r in records})
    print(f"Raport: {len(records)} rekordów, {n_panels} paneli, {n_series} serii marker/jednostka -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
