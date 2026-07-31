"""Testy jednostkowe warstwy 1/3 (PRD V4) — czysta logika src/agent.py, zero wywołań
sieciowych/API. Weryfikacja realnego wywołania query() (warstwy 2 i 3) jest ręczna,
udokumentowana w Notatkach docs/v4/01-agent.md, nie w tym pliku."""
from __future__ import annotations

import sys
from datetime import date

import agent


def test_slugify_polish_diacritics():
    assert agent.slugify("Ferrytyna wg Łukasza") == "ferrytyna-wg-lukasza"


def test_slugify_punctuation_and_spaces_become_hyphens():
    assert agent.slugify("jak wygląda mój poziom ferrytyny w czasie?") == \
        "jak-wyglada-moj-poziom-ferrytyny-w-czasi"


def test_slugify_truncates_to_max_len():
    slug = agent.slugify("a" * 100, max_len=10)
    assert slug == "a" * 10


def test_slugify_empty_after_strip_falls_back():
    assert agent.slugify("???") == "zapytanie"


def test_output_path_no_collision(tmp_path):
    path = agent.output_path("ferrytyna", directory=tmp_path, today=date(2026, 7, 31))
    assert path.name == "2026-07-31-ferrytyna.md"


def test_output_path_collision_appends_counter(tmp_path):
    today = date(2026, 7, 31)
    (tmp_path / "2026-07-31-ferrytyna.md").write_text("istniejący", encoding="utf-8")
    path = agent.output_path("ferrytyna", directory=tmp_path, today=today)
    assert path.name == "2026-07-31-ferrytyna-2.md"


def test_output_path_two_collisions_appends_next_counter(tmp_path):
    today = date(2026, 7, 31)
    (tmp_path / "2026-07-31-ferrytyna.md").write_text("istniejący", encoding="utf-8")
    (tmp_path / "2026-07-31-ferrytyna-2.md").write_text("istniejący", encoding="utf-8")
    path = agent.output_path("ferrytyna", directory=tmp_path, today=today)
    assert path.name == "2026-07-31-ferrytyna-3.md"


def test_build_options_disables_builtin_tools():
    options = agent.build_options()
    assert options.tools == []


def test_build_options_mcp_servers_points_at_v2_server():
    options = agent.build_options()
    assert set(options.mcp_servers) == {"document-intelligence-platform"}
    server = options.mcp_servers["document-intelligence-platform"]
    assert server["type"] == "stdio"
    assert server["command"] == sys.executable
    assert server["args"] == [str(agent.MCP_SERVER_PATH)]


def test_build_options_allowed_tools_exactly_two_v2_tools():
    options = agent.build_options()
    assert options.allowed_tools == [
        "mcp__document-intelligence-platform__get_marker_trend",
        "mcp__document-intelligence-platform__compare_markers",
    ]


def test_build_options_no_settings_sources():
    options = agent.build_options()
    assert options.setting_sources == []


def test_build_options_system_prompt_excludes_dynamic_sections():
    options = agent.build_options()
    assert options.system_prompt == {
        "type": "preset",
        "preset": "claude_code",
        "exclude_dynamic_sections": True,
    }
