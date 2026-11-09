"""The public site must never publish internal material.

`docs/` holds the site source next to internal working files: briefs (with
SSH hops and session links), superpowers specs/plans, and RFCs. Sphinx
publishes every source it is not told to exclude, so an exclusion that drifts
would put those files on helpfledgling.ai. `scripts/check_site_leaks.py` scans
the BUILT html and fails the Pages deploy on any leak. An empty build must not
pass either: absence of output is not success.
"""
from __future__ import annotations

import subprocess
import sys

import pytest

from conftest import REPO, load_module

SCRIPT = REPO / "scripts/check_site_leaks.py"


@pytest.fixture(scope="module")
def csl():
    return load_module("scripts/check_site_leaks.py", "check_site_leaks")


def _site(tmp_path, files):
    for rel, text in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return tmp_path


def test_clean_tree_has_no_leaks(csl, tmp_path):
    root = _site(tmp_path, {"index.html": "<p>the retritis suite</p>"})
    assert csl.find_leaks(root) == []


@pytest.mark.parametrize("folder", ["briefs", "superpowers", "rfcs"])
def test_excluded_folder_is_a_leak(csl, tmp_path, folder):
    root = _site(tmp_path, {"index.html": "ok", f"{folder}/x.html": "ok"})
    leaks = csl.find_leaks(root)
    assert len(leaks) == 1 and f"{folder}/" in leaks[0]


@pytest.mark.parametrize("marker", [
    "run it via ssh snape ssh ionos then rsync",
    "see https://claude.ai/code/session_01ABC for details",
])
def test_content_marker_is_a_leak(csl, tmp_path, marker):
    # A chapter that is allowed to publish, but quotes internal material.
    root = _site(tmp_path, {"index.html": "ok", "book/03.html": marker})
    leaks = csl.find_leaks(root)
    assert len(leaks) == 1 and "book/03.html" in leaks[0]


def test_content_marker_in_sources_txt_is_a_leak(csl, tmp_path):
    root = _site(tmp_path, {"index.html": "ok",
                            "_sources/book/03.md.txt": "ssh ionos"})
    assert len(csl.find_leaks(root)) == 1


def _cli(root):
    return subprocess.run([sys.executable, str(SCRIPT), str(root)],
                          capture_output=True, text=True)


def test_cli_exits_2_without_index(tmp_path):
    r = _cli(tmp_path)
    # Exit 2 alone is ambiguous (python exits 2 for a missing script), so
    # also require the script's own reason.
    assert r.returncode == 2 and "no index.html" in r.stderr


def test_cli_exits_1_on_leak(tmp_path):
    root = _site(tmp_path, {"index.html": "ok", "briefs/b.html": "x"})
    r = _cli(root)
    assert r.returncode == 1 and "briefs/b.html" in r.stdout


def test_cli_exits_0_and_counts(tmp_path):
    root = _site(tmp_path, {"index.html": "ok"})
    r = _cli(root)
    assert r.returncode == 0 and "ok: 1 files scanned" in r.stdout
