"""Issue #2: classify_bash inspected only the first pipeline stage, so
`cd x && git commit` went uncounted and adoption metrics undercounted."""
from __future__ import annotations

import pytest

from conftest import load_module


@pytest.fixture(scope="module")
def probe():
    return load_module("scripts/bypass_probe.py", "bypass_probe")


def test_first_stage_still_classified(probe):
    assert probe.classify_bash("git status") == "jetsam:status"
    assert probe.classify_bash("grep -rn foo src/") == "squackit:search"


def test_later_stage_after_cd_counted(probe):
    """Fails on the first-stage-only implementation."""
    assert probe.classify_bash("cd x && git commit -m msg") == "jetsam:commit"


def test_later_stage_after_semicolon_counted(probe):
    assert probe.classify_bash("cd /tmp; pytest -x") == "blq:run"


def test_pipe_filter_grep_still_excluded(probe):
    """Conservative exclusions survive: non-recursive grep as a pipe filter
    is not a bypass."""
    assert probe.classify_bash("git log --oneline | grep fix") is None


def test_read_only_git_still_excluded(probe):
    assert probe.classify_bash("cd x && git log") is None
    assert probe.classify_bash("git -C /repo status") is None
