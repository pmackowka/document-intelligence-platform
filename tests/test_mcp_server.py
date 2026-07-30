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
