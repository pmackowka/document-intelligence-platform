"""Agent V4 — orkiestracja narzędzi MCP z V2 (`get_marker_trend`, `compare_markers`) w trybie jednorazowym.

Konfiguracja `ClaudeAgentOptions` zawężona świadomie: zero wbudowanych narzędzi Claude
Code, wyłącznie klient MCP do serwera z V2, wyłączone auto-memory. Zweryfikowane
empirycznie w rundzie review PRD (`docs/v4/prd.md`, Tech Constraints; `docs/v4/00-planning.md`).
"""
from __future__ import annotations

import asyncio
import re
import sys
from datetime import date
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

from storage import ROOT

MCP_SERVER_PATH = ROOT / "src" / "mcp_server.py"
OUTPUT_DIR = ROOT / "data" / "agent"
SERVER_NAME = "document-intelligence-platform"

_POLISH_DIACRITICS = str.maketrans(
    "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ",
    "acelnoszzACELNOSZZ",
)


def build_options() -> ClaudeAgentOptions:
    """Zwraca zawężoną konfigurację agenta V4.

    Pięć pól z PRD (Tech Constraints), każde świadomą barierą, nie ustawieniem domyślnym:
    `tools=[]` wyłącza wbudowane narzędzia Claude Code (Bash/Read/Write/Edit itd.);
    `mcp_servers` to jedyne źródło narzędzi — te same trzy z serwera V2; `allowed_tools`
    auto-zatwierdza dokładnie dwa z nich (bez tego jednorazowe wywołanie utyka na prośbie
    o uprawnienia — nikt nie może jej ręcznie zatwierdzić); `setting_sources=[]` pomija
    `CLAUDE.md`/ustawienia projektu; `system_prompt.exclude_dynamic_sections` usuwa
    auto-memory z promptu systemowego.
    """
    return ClaudeAgentOptions(
        tools=[],
        mcp_servers={
            SERVER_NAME: {
                "type": "stdio",
                "command": sys.executable,
                "args": [str(MCP_SERVER_PATH)],
            }
        },
        allowed_tools=[
            f"mcp__{SERVER_NAME}__get_marker_trend",
            f"mcp__{SERVER_NAME}__compare_markers",
        ],
        setting_sources=[],
        system_prompt={
            "type": "preset",
            "preset": "claude_code",
            "exclude_dynamic_sections": True,
        },
    )


def slugify(text: str, max_len: int = 40) -> str:
    """Slug z treści zapytania: polskie diakrytyki -> ASCII, reszta znaków -> myślnik."""
    ascii_text = text.translate(_POLISH_DIACRITICS).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    slug = slug[:max_len].rstrip("-")
    return slug or "zapytanie"


def output_path(topic_slug: str, directory: Path = OUTPUT_DIR, today: date | None = None) -> Path:
    """Ścieżka `{katalog}/YYYY-MM-DD-{slug}.md` z ochroną przed nadpisaniem.

    Przy kolizji nazwy (kolejne wywołanie tego samego dnia z tym samym slugiem)
    dopisuje licznik (`-2`, `-3`...) zamiast nadpisywać — nowy kod, więc ochrona
    wbudowana od początku (PRD V4, Scope, punkt 6), inaczej niż dyscyplina
    proceduralna wokół `report.py` (incydent 2026-07-22, `CLAUDE.md`).
    """
    today = today or date.today()
    base = f"{today.isoformat()}-{topic_slug}"
    candidate = directory / f"{base}.md"
    counter = 2
    while candidate.exists():
        candidate = directory / f"{base}-{counter}.md"
        counter += 1
    return candidate


async def run_agent(prompt: str) -> str:
    """Wywołuje `query()` z zawężoną konfiguracją V4, zwraca finalny tekst odpowiedzi."""
    result_text = ""
    async for message in query(prompt=prompt, options=build_options()):
        if isinstance(message, ResultMessage):
            result_text = message.result or ""
    return result_text


def main() -> int:
    if len(sys.argv) < 2:
        print("Użycie: uv run python src/agent.py <zapytanie>", file=sys.stderr)
        return 1

    prompt = " ".join(sys.argv[1:])
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result_text = asyncio.run(run_agent(prompt))
    path = output_path(slugify(prompt))
    path.write_text(result_text, encoding="utf-8")
    print(f"Zapisano: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
