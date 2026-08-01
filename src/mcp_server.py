from mcp.server.fastmcp import FastMCP

from storage import MarkerNotFound, latest_report, load_labels, load_records, marker_series, resolve_marker

mcp = FastMCP("document-intelligence-platform")


@mcp.tool()
def ping() -> str:
    """Narzędzie testowe spike'u — potwierdza, że transport stdio działa."""
    return "pong"


@mcp.tool()
def get_marker_trend(identyfikator: str) -> dict:
    """Zwraca serię pomiarów markera (kod kanoniczny, np. HGB, lub polska etykieta,
    np. Hemoglobina) z zaufanego magazynu. Gdy marker ma więcej niż jedną serię
    (różne jednostki pod tym samym kodem), zwraca wszystkie, pogrupowane po jednostce.
    Surowe rekordy — bez interpretacji (kierunek trendu, delta itd.)."""
    try:
        code = resolve_marker(identyfikator)
    except MarkerNotFound as e:
        return {"status": "not_found", "identifier": identyfikator, "suggestions": e.suggestions}

    series = marker_series(code, load_records())
    return {"status": "ok", "marker": code, "series": series}


@mcp.tool()
def compare_markers(identyfikatory: list[str]) -> dict:
    """Zwraca serie pomiarów dla wielu markerów naraz (kody kanoniczne lub polskie
    etykiety) — N niezależnych serii, świadomie bez łączenia po dacie badania
    (różne markery mogą mieć różne daty pomiarów; nie zgadujemy, które sobie
    odpowiadają). Ta sama logika identyfikacji i grupowania po jednostce co
    get_marker_trend, zastosowana do każdego identyfikatora z osobna."""
    records = load_records()
    results = []
    for identyfikator in identyfikatory:
        try:
            code = resolve_marker(identyfikator)
        except MarkerNotFound as e:
            results.append({"status": "not_found", "identifier": identyfikator, "suggestions": e.suggestions})
            continue
        series = marker_series(code, records)
        results.append({"status": "ok", "identifier": identyfikator, "marker": code, "series": series})
    return {"results": results}


@mcp.resource("markers://catalog")
def markers_catalog() -> str:
    """Katalog kodów kanonicznych i polskich etykiet markerów (marker_labels.yml) — wyłącznie
    metadane domenowe, zero wartości pomiarów, zero PII."""
    labels = load_labels()
    return "\n".join(f"{code}: {label}" for code, label in sorted(labels.items()))


@mcp.resource("report://latest")
def report_latest() -> str:
    """Treść najnowszego raportu Markdown z data/reports/ (nagłówek pliku niesie tryb —
    zaufany magazyn albo KANDYDAT). Jawny komunikat zamiast wyjątku, gdy folder jest pusty —
    ta sama zasada "nigdy cicha pustka" co przy nierozpoznanym identyfikatorze markera."""
    path = latest_report()
    if path is None:
        return "Brak wygenerowanych raportów w data/reports/ — najpierw uruchom report.py."
    return path.read_text(encoding="utf-8")


@mcp.prompt()
def porownaj_markery(marker1: str, marker2: str) -> str:
    """Gotowy szablon zapytania o porównanie dwóch markerów w czasie — zaszywa raz poprawnie
    działającą frazę, zamiast wymagać, żeby operator pamiętał ją za każdym razem."""
    return f"Porównaj moje wyniki {marker1} i {marker2} w czasie."


if __name__ == "__main__":
    mcp.run()
