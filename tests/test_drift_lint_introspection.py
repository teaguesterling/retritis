"""Regression tests: the drift lint fails a plugin whose MCP server will not start.

A failed `tools/list` used to become a note, and the plugin still got ✅. On
2026-11-10 fledgling and lackpy both showed ✅ while their servers crashed at
startup, so the verb check for those skills never ran and nothing said so.
A plugin that ships a server the lint cannot start is unverified, not clean.

These run without the `mcp` package: `list_mcp_tools` is replaced.
"""
from __future__ import annotations

import asyncio

import pytest

from conftest import load_module


@pytest.fixture(scope="module")
def lint():
    return load_module("scripts/skill_drift_lint.py", "skill_drift_lint")


def test_server_that_will_not_start_is_an_error(lint, monkeypatch):
    async def crash(command, args):
        raise ExceptionGroup("unhandled errors in a TaskGroup",
                             [ConnectionError("Connection closed")])

    monkeypatch.setattr(lint, "list_mcp_tools", crash)
    finding = asyncio.run(lint.lint_plugin("jetsam"))
    assert finding.has_errors
    _, exit_code = lint.render_text([finding])
    assert exit_code == 1


def test_error_names_the_leaf_exception(lint, monkeypatch):
    """"1 sub-exception" tells the reader nothing; the cause must show."""
    async def crash(command, args):
        raise ExceptionGroup("unhandled errors in a TaskGroup",
                             [ConnectionError("Connection closed")])

    monkeypatch.setattr(lint, "list_mcp_tools", crash)
    finding = asyncio.run(lint.lint_plugin("jetsam"))
    body, _ = lint.render_text([finding])
    assert "ConnectionError: Connection closed" in body


def test_plugin_without_a_server_stays_a_note(lint):
    """test-failure-investigator ships no .mcp.json: nothing to start, so
    nothing failed. Only "has a server, could not start it" is an error."""
    finding = asyncio.run(lint.lint_plugin("test-failure-investigator"))
    assert not finding.has_errors
