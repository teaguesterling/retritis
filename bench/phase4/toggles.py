"""How each integration is realized OFF (baseline) vs ON.

The A/B is only meaningful if these toggles are clean — see the table in
vision/phase-4-calibration.md section B. Most ON paths reference integrations
that don't exist yet (Phase 4 builds them); those are TODO and currently raise
NotImplementedError so a misconfigured ON run fails loudly instead of silently
measuring the OFF behavior.
"""
from __future__ import annotations

from pathlib import Path


def env_for(integrations: dict[str, bool], fixture: Path) -> dict[str, str]:
    """Return the environment overlay that realizes the requested toggle set.

    OFF is always the current shipped behavior (in-memory fledgling, config-only
    kibitzer policy, no ratchet consumer). ON wires the Phase 4 deliverable.
    """
    env: dict[str, str] = {}

    # C - persistent fact substrate
    if integrations.get("C"):
        # ON: file-backed fledgling cache (Phase 4 workstream C).
        # env["FLEDGLING_PERSIST"] = str(fixture / ".fledgling/cache.duckdb")
        raise NotImplementedError("toggle C ON: persistent cache not built yet (workstream C)")
    # OFF: nothing -> fledgling.connect(persist=None), in-memory rebuild.

    # B - one policy, two enforcers
    if integrations.get("B"):
        # ON: compiled umwelt policy present -> kibitzer PolicyConsumer.from_db + lackpy source.
        # env["KIBITZER_POLICY_DB"] = str(fixture / ".umwelt/policy.db")
        raise NotImplementedError("toggle B ON: compiled policy.db wiring not built yet (workstream B)")
    # OFF: kibitzer config.toml only (PolicyConsumer.from_db -> None).

    # A - learn loop
    if integrations.get("A"):
        # ON: seeded-then-frozen ratchet store + a RatchetConsumer in kibitzer/lackpy.
        # env["RIGGS_RATCHET_DB"] = str(fixture / ".retritis/riggs.duckdb"); env["RIGGS_FROZEN"] = "1"
        raise NotImplementedError("toggle A ON: ratchet consumer not built yet (workstream A)")
    # OFF: empty/absent ratchet store.

    return env
