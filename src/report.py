"""Etap 3 — raport Markdown "do lekarza": trendy markerów strukturalnych.

Czyta data/store/structural-backfill.ndjson (zaufany magazyn), grupuje rekordy wg panelu
i markera, sortuje po dacie badania i zapisuje czytelny raport do data/reports/.

Grupowanie wewnątrz markera dzieli się po jednostce TYLKO gdy dla danego markera
istnieją >=2 realne (niepuste) jednostki w danych — niektóre markery (różnicowanie
morfologii: NEU/LYM/MONO/EOS/BASO) występują w źródle w DWÓCH jednostkach na ten sam
kod (% i tys/µl, odsetek vs wartość bezwzględna); zlanie ich w jeden ciąg trendu
pomieszałoby dwie różne skale. Gdy realna jednostka jest tylko jedna, rekordy bez
jednostki (parser jej nie znalazł w konkretnym dokumencie) dołączają do tej jednej —
inaczej ta sama seria rozpadała się na kilka osobnych tabel bez powodu klinicznego.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "data" / "store" / "structural-backfill.ndjson"
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


def load_records(store_path: Path = STORE) -> list[dict]:
    if not store_path.exists():
        return []
    with store_path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def load_labels() -> dict:
    data = yaml.safe_load(LABELS.read_text(encoding="utf-8")) if LABELS.exists() else {}
    return (data or {}).get("labels", {})


def fmt_value(r: dict, group_unit: str | None = None) -> str:
    if r["value"] is not None:
        unit = r["unit"] or group_unit  # rekord bez własnej jednostki -> jednostka reszty serii
        return f"{r['value']:g} {unit}" if unit else f"{r['value']:g}"
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
    by_panel: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for r in records:
        by_panel[r["panel"]][r["marker"]].append(r)

    lines = [f"# Raport trendów — badania strukturalne", "", f"Wygenerowano: {date.today().isoformat()}", ""]

    for panel in sorted(by_panel, key=lambda p: PANEL_LABELS.get(p, p)):
        lines.append(f"## {PANEL_LABELS.get(panel, panel)}")
        lines.append("")
        marker_rows = by_panel[panel]
        for marker in sorted(marker_rows, key=lambda m: labels.get(m, m)):
            rows = marker_rows[marker]
            # Ta sama seria bywa ma jednostkę tylko w części dokumentów (parser jej tam nie
            # znalazł) — dopóki dla markera istnieje TYLKO JEDNA realna (niepusta) jednostka,
            # scalamy rekordy bez jednostki do niej zamiast rozbijać trend na kilka tabel.
            # Gdy realnych jednostek jest >=2 (np. NEU w % i w tys/µl — różne skale), zostają
            # rozdzielone jak dotąd — nie zgadujemy, do której skali należy brakująca jednostka.
            real_units = {r["unit"] for r in rows if r["unit"]}
            if len(real_units) <= 1:
                sub_groups = {next(iter(real_units), None): rows}
            else:
                sub_groups = defaultdict(list)
                for r in rows:
                    sub_groups[r["unit"]].append(r)
            for unit, sub_rows in sorted(sub_groups.items(), key=lambda kv: kv[0] or ""):
                sub_rows = sorted(sub_rows, key=lambda r: r["exam_date"] or "")
                label = labels.get(marker, marker)
                numeric = [r["value"] for r in sub_rows if r["value"] is not None]
                arrow = trend_arrow(numeric)
                unit_suffix = f" ({unit})" if unit and any(r["value"] is not None for r in sub_rows) else ""
                lines.append(f"### {label}{unit_suffix}{arrow}")
                lines.append("")
                lines.append("| Data | Wartość | Zakres ref. | Źródło |")
                lines.append("|---|---|---|---|")
                for r in sub_rows:
                    lines.append(f"| {r['exam_date'] or 'brak daty'} | {fmt_value(r, unit)} | {fmt_range(r)} | {r['source_file']} |")
                lines.append("")

    return "\n".join(lines)


def main() -> int:
    # Bez argumentu: zaufany magazyn (STORE). Z argumentem: podejrzenie dowolnej
    # migawki-kandydata (`data/store/YYYY-MM-DD-structural.ndjson`) przed scaleniem.
    store_path = Path(sys.argv[1]) if len(sys.argv) > 1 else STORE
    records = load_records(store_path)
    if not records:
        print(f"Brak rekordów w {store_path} — najpierw uruchom structural_pipeline.py")
        return 1
    labels = load_labels()
    report = build_report(records, labels)

    REPORTS.mkdir(parents=True, exist_ok=True)
    out = REPORTS / f"{date.today().isoformat()}-trendy.md"
    out.write_text(report, encoding="utf-8")

    n_panels = len({r["panel"] for r in records})
    n_series = len({(r["panel"], r["marker"], r["unit"]) for r in records})
    mode = "zaufany magazyn" if store_path == STORE else "KANDYDAT"
    print(f"Raport ({mode}, źródło: {store_path.name}): {len(records)} rekordów, {n_panels} paneli, {n_series} serii marker/jednostka -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
