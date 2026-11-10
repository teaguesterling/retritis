"""Regression tests: SKILL.md files name tools by the ids Claude Code registers.

Claude Code serves a plugin's MCP tools as
`mcp__plugin_<plugin>_<server>__<tool>`, where `<server>` is the key in the
plugin's `.mcp.json`. When the tools moved behind that prefix, the skills
kept the old `mcp__jetsam__*` / `mcp__blq_mcp__*` spellings, and the drift
lint stayed green: it compared only the verb after the last `__`, so
`mcp__jetsam__save` matched the live `save`. An agent that copies an id from a
routing table into a dispatch spec, a permission rule, or a ToolSearch
`select:` gets a name that matches nothing, and nothing says so.

These checks are static (no MCP server is started), so they run on every PR.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import REPO, load_module


@pytest.fixture(scope="module")
def lint():
    return load_module("scripts/skill_drift_lint.py", "skill_drift_lint")


def _plugin(root: Path, name: str, servers: list[str]) -> None:
    d = root / name
    d.mkdir(parents=True)
    (d / ".mcp.json").write_text(json.dumps(
        {s: {"command": "x", "args": []} for s in servers}
    ))


def test_prefixes_come_from_plugin_and_server_key(lint, tmp_path):
    """The server key, not the plugin name, is the second segment: blq's
    server is `blq_mcp`, which is why its ids carry blq twice."""
    _plugin(tmp_path, "jetsam", ["jetsam"])
    _plugin(tmp_path, "blq", ["blq_mcp"])
    (tmp_path / "duckeye").mkdir()  # CLI plugin: no .mcp.json, no prefix
    assert lint.registered_prefixes(tmp_path) == {
        "mcp__plugin_jetsam_jetsam__",
        "mcp__plugin_blq_blq_mcp__",
    }


def test_old_prefix_is_flagged_even_when_the_verb_exists(lint):
    """The failure that went unseen: right verb, dead prefix."""
    valid = {"mcp__plugin_jetsam_jetsam__", "mcp__plugin_blq_blq_mcp__"}
    text = (
        "| `git commit` | `mcp__jetsam__save` |\n"
        "| run tests | `mcp__blq_mcp__run` |\n"
        "| `git push` | `mcp__plugin_jetsam_jetsam__sync` |\n"
        "call mcp__plugin_blq_blq_mcp__register_command(...)\n"
    )
    assert lint.wrong_prefix_refs(text, valid) == [
        "mcp__blq_mcp__run",
        "mcp__jetsam__save",
    ]


def test_placeholders_are_not_references(lint):
    """`mcp__plugin_<plugin>_<server>__<tool>` documents the shape; it is
    not a claim about a tool."""
    assert lint.wrong_prefix_refs(
        "ids follow `mcp__plugin_<plugin>_<server>__<tool>`", set()
    ) == []


def test_every_repo_skill_uses_a_registered_prefix(lint):
    """Permanent guard over every SKILL.md under plugins/, including skills
    of plugins that ship no MCP server and name other plugins' tools
    (test-failure-investigator), which the live lint skips."""
    valid = lint.registered_prefixes(REPO / "plugins")
    bad = {}
    for skill in sorted((REPO / "plugins").glob("*/skills/*/SKILL.md")):
        refs = lint.wrong_prefix_refs(skill.read_text(), valid)
        if refs:
            bad[str(skill.relative_to(REPO))] = refs
    assert bad == {}
