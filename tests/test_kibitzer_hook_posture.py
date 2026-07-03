"""Advisory item 3 / issue #2: the kibitzer guard's failure posture must be
explicit, never a silent drop. Default: fail-open WITH a warning; opt-in
RETRITIS_FAIL_CLOSED=1: a missing kibitzer blocks (exit 2)."""
from __future__ import annotations

import os
import subprocess

from conftest import REPO

HOOK = REPO / "plugins/kibitzer/hooks/kibitzer-pre.sh"


def run_hook(**env_extra):
    env = dict(os.environ)
    # /bin/false as the "interpreter": every import check fails → simulates
    # a missing/broken kibitzer install regardless of the host machine.
    env["KIBITZER_PYTHON"] = "/bin/false"
    env.update(env_extra)
    return subprocess.run(
        ["bash", str(HOOK)], env=env, capture_output=True, text=True, timeout=15
    )


def test_missing_kibitzer_fails_open_with_warning():
    out = run_hook()
    assert out.returncode == 0
    assert "skipped" in out.stderr and "fail-open" in out.stderr


def test_fail_closed_mode_blocks_when_kibitzer_missing():
    out = run_hook(RETRITIS_FAIL_CLOSED="1")
    assert out.returncode == 2
    assert "blocking" in out.stderr
