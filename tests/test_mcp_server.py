"""Testy jednostkowe kontraktu narzędzi MCP — kształt wyjścia get_marker_trend/
compare_markers. load_records podmieniony na literały syntetyczne (monkeypatch),
żeby testy nie zależały od prywatnego, niewersjonowanego magazynu NDJSON.
Identyfikacja markerów (resolve_marker) korzysta z realnego config/marker_labels.yml
— to plik domenowy bez PII, wersjonowany, ma już własne testy w test_storage.py."""
from __future__ import annotations

import mcp_server

# Pole wyjściowe z PRD V2 — literał niezależny od implementacji (storage.SERIES_FIELDS),
# żeby test pilnował kontraktu, nie powtarzał kodu producenta.
EXPECTED_RECORD_FIELDS = {
    "exam_date",
    "value",
    "value_text",
    "unit",
    "reference_low",
    "reference_high",
    "reference_note",
    "source_file",
}

SAMPLE_RECORDS = [
    {"marker": "HGB", "unit": "g/dl", "value": 14.1, "value_text": None,
     "reference_low": 12.1, "reference_high": 17.0, "reference_note": None,
     "exam_date": "2024-01-10", "source_file": "a.pdf"},
    {"marker": "HGB", "unit": "g/dl", "value": 14.5, "value_text": None,
     "reference_low": 12.1, "reference_high": 17.0, "reference_note": None,
     "exam_date": "2024-06-10", "source_file": "b.pdf"},
    {"marker": "NEU", "unit": "%", "value": 55.0, "value_text": None,
     "reference_low": None, "reference_high": None, "reference_note": None,
     "exam_date": "2024-01-10", "source_file": "a.pdf"},
    {"marker": "NEU", "unit": "tys/µl", "value": 3.2, "value_text": None,
     "reference_low": None, "reference_high": None, "reference_note": None,
     "exam_date": "2024-01-10", "source_file": "a.pdf"},
    {"marker": "FERR", "unit": "ng/ml", "value": 25.0, "value_text": None,
     "reference_low": 30.0, "reference_high": 400.0, "reference_note": None,
     "exam_date": "2024-03-01", "source_file": "c.pdf"},
]


def test_get_marker_trend_single_series_shape(monkeypatch):
    monkeypatch.setattr(mcp_server, "load_records", lambda: SAMPLE_RECORDS)

    result = mcp_server.get_marker_trend("HGB")

    assert result["status"] == "ok"
    assert result["marker"] == "HGB"
    assert len(result["series"]) == 1
    series = result["series"][0]
    assert series["unit"] == "g/dl"
    assert len(series["records"]) == 2
    assert set(series["records"][0].keys()) == EXPECTED_RECORD_FIELDS


def test_get_marker_trend_multi_series_shape(monkeypatch):
    monkeypatch.setattr(mcp_server, "load_records", lambda: SAMPLE_RECORDS)

    result = mcp_server.get_marker_trend("NEU")

    assert result["status"] == "ok"
    units = {s["unit"] for s in result["series"]}
    assert units == {"%", "tys/µl"}
    assert all(len(s["records"]) == 1 for s in result["series"])


def test_get_marker_trend_unknown_identifier_shape(monkeypatch):
    monkeypatch.setattr(mcp_server, "load_records", lambda: SAMPLE_RECORDS)

    result = mcp_server.get_marker_trend("zupelnie_nieznany_marker_xyz")

    assert result == {
        "status": "not_found",
        "identifier": "zupelnie_nieznany_marker_xyz",
        "suggestions": [],
    }


def test_compare_markers_two_known_returns_independent_series(monkeypatch):
    monkeypatch.setattr(mcp_server, "load_records", lambda: SAMPLE_RECORDS)

    result = mcp_server.compare_markers(["HGB", "FERR"])

    assert len(result["results"]) == 2
    by_identifier = {r["identifier"]: r for r in result["results"]}
    assert by_identifier["HGB"]["status"] == "ok"
    assert by_identifier["HGB"]["marker"] == "HGB"
    assert len(by_identifier["HGB"]["series"][0]["records"]) == 2
    assert by_identifier["FERR"]["status"] == "ok"
    assert by_identifier["FERR"]["marker"] == "FERR"
    assert len(by_identifier["FERR"]["series"][0]["records"]) == 1


def test_compare_markers_mix_of_known_and_unknown(monkeypatch):
    monkeypatch.setattr(mcp_server, "load_records", lambda: SAMPLE_RECORDS)

    result = mcp_server.compare_markers(["HGB", "zupelnie_nieznany_marker_xyz"])

    statuses = [r["status"] for r in result["results"]]
    assert statuses == ["ok", "not_found"]


# V5 — Resources i Prompts (docs/v5/prd.md). SAMPLE_LABELS syntetyczne, jak SAMPLE_RECORDS wyżej —
# markers_catalog nie powinien zależeć od prywatnego, niewersjonowanego marker_labels.yml w testach.
SAMPLE_LABELS = {"HGB": "Hemoglobina", "FERR": "Ferrytyna", "ESR": "OB (odczyn Biernackiego)"}


def test_markers_catalog_lists_all_labels_sorted(monkeypatch):
    monkeypatch.setattr(mcp_server, "load_labels", lambda: SAMPLE_LABELS)

    result = mcp_server.markers_catalog()

    assert result == "ESR: OB (odczyn Biernackiego)\nFERR: Ferrytyna\nHGB: Hemoglobina"


def test_report_latest_returns_newest_file_content(monkeypatch, tmp_path):
    report_file = tmp_path / "2026-07-31-trendy.md"
    report_file.write_text("# Raport\n\nTryb: zaufany magazyn", encoding="utf-8")
    monkeypatch.setattr(mcp_server, "latest_report", lambda: report_file)

    assert mcp_server.report_latest() == "# Raport\n\nTryb: zaufany magazyn"


def test_report_latest_empty_directory_returns_explicit_message(monkeypatch):
    monkeypatch.setattr(mcp_server, "latest_report", lambda: None)

    result = mcp_server.report_latest()

    assert "Brak wygenerowanych raportów" in result


def test_porownaj_markery_formats_template():
    assert mcp_server.porownaj_markery("Hemoglobina", "OB") == \
        "Porównaj moje wyniki Hemoglobina i OB w czasie."


def test_porownaj_markery_handles_special_characters_in_identifier():
    # Identyfikator ze skrótem w nawiasie (PRD, Threat Model) — prompt tylko formatuje
    # tekst, nie rozpoznaje markera, więc dowolny string przechodzi bez zmian.
    result = mcp_server.porownaj_markery("PTH (parathormon)", "Ca")
    assert result == "Porównaj moje wyniki PTH (parathormon) i Ca w czasie."
