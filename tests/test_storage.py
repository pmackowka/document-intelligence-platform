"""Testy jednostkowe czystej logiki storage.py — niezależne od realnych plików
(marker_labels.yml, magazynu NDJSON); etykiety i rekordy to literały syntetyczne."""
from __future__ import annotations

import pytest

from storage import MarkerNotFound, group_by_unit, resolve_marker

LABELS = {
    "HGB": "Hemoglobina",
    "FERR": "Ferrytyna",
    "WBC": "Leukocyty",
}


def test_resolve_marker_by_code():
    assert resolve_marker("HGB", LABELS) == "HGB"


def test_resolve_marker_by_code_case_insensitive():
    assert resolve_marker("hgb", LABELS) == "HGB"


def test_resolve_marker_by_label():
    assert resolve_marker("Ferrytyna", LABELS) == "FERR"


def test_resolve_marker_by_label_case_insensitive():
    assert resolve_marker("ferrytyna", LABELS) == "FERR"


def test_resolve_marker_unknown_raises_with_suggestion():
    with pytest.raises(MarkerNotFound) as exc_info:
        resolve_marker("Ferytyna", LABELS)  # literówka w etykiecie

    assert exc_info.value.suggestions == ["FERR"]


def test_resolve_marker_unknown_raises_without_suggestion():
    with pytest.raises(MarkerNotFound) as exc_info:
        resolve_marker("zupelnie_nieznany_marker_xyz", LABELS)

    assert exc_info.value.suggestions == []


# Etykiety krótkiego skrótu przed nawiasem — regres realnego bugu: "OB" (przykład
# z PRD, S2) nie pasował ani do kodu (ESR), ani do difflib (2 znaki vs 24-znakowa
# etykieta, zbyt duża różnica długości dla cutoff=0.6).
PREFIX_LABELS = {
    "ESR": "OB (odczyn Biernackiego)",
    "PTH": "PTH (parathormon)",
    "PTH_1_84": "PTH (1-84)",
}


def test_resolve_marker_by_bracket_prefix():
    assert resolve_marker("OB", PREFIX_LABELS) == "ESR"


def test_resolve_marker_by_bracket_prefix_case_insensitive():
    assert resolve_marker("ob", PREFIX_LABELS) == "ESR"


def test_resolve_marker_code_wins_over_ambiguous_prefix():
    # "PTH" to kod markera PTH — mimo że etykieta PTH_1_84 dałaby ten sam prefiks "pth",
    # dokładne dopasowanie kodu ma pierwszeństwo, więc nie ma tu niejednoznaczności
    assert resolve_marker("PTH", PREFIX_LABELS) == "PTH"


def test_resolve_marker_ambiguous_prefix_not_silently_guessed():
    # "PTH (1-84)" dałoby prefiks "pth", który koliduje z kodem innego markera (PTH) —
    # ten prefiks nie powinien trafić do aliasów; PTH_1_84 wciąż rozpoznawalny po kodzie
    assert resolve_marker("PTH_1_84", PREFIX_LABELS) == "PTH_1_84"


def test_group_by_unit_single_real_unit_merges_missing_unit():
    records = [
        {"unit": "g/dl", "value": 13.5},
        {"unit": None, "value": 14.0},  # parser nie znalazł jednostki w tym dokumencie
        {"unit": "g/dl", "value": 14.2},
    ]

    groups = group_by_unit(records)

    assert list(groups.keys()) == ["g/dl"]
    assert len(groups["g/dl"]) == 3


def test_group_by_unit_multiple_real_units_splits_and_isolates_missing():
    records = [
        {"unit": "%", "value": 55.0},
        {"unit": "tys/µl", "value": 3.1},
        {"unit": None, "value": 99.0},  # nie zgadujemy, do której skali należy
    ]

    groups = group_by_unit(records)

    assert set(groups.keys()) == {"%", "tys/µl", None}
    assert len(groups["%"]) == 1
    assert len(groups["tys/µl"]) == 1
    assert len(groups[None]) == 1
