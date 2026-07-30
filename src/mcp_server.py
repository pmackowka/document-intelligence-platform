from mcp.server.fastmcp import FastMCP

from storage import MarkerNotFound, load_records, marker_series, resolve_marker

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


if __name__ == "__main__":
    mcp.run()
