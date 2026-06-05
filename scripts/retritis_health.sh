#!/usr/bin/env bash
# retritis_health.sh — run all three quality checks in sequence.
#
# Composes the three feedback-loop scripts so an operator can ask "is the
# suite OK?" with a single command:
#
#   1. retritis_doctor.py        integrity (installs, MCP spawn, SKILL.md presence)
#   2. skill_drift_lint.py        accuracy   (SKILL.md ↔ live MCP schema)
#   3. trigger_analysis.py        triggers   (Skill invocation rates from transcripts)
#
# Exit codes:
#   0  every check passed
#   1  at least one check failed (HARD — broken install, hallucination,
#                                 or BYPASSED plugin)
#   2  warnings only (kibitzer disabled, low sample, etc.)
#
# Usage:
#   scripts/retritis_health.sh             # all three
#   scripts/retritis_health.sh --doctor    # just integrity
#   scripts/retritis_health.sh --lint      # just drift
#   scripts/retritis_health.sh --triggers  # just triggers
#   scripts/retritis_health.sh --json      # machine-readable (combined)

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

run_doctor=true
run_lint=true
run_triggers=true
json_mode=false

# Flag parsing — selectors are exclusive (if any selector is given, run only that)
selected_any=false
for arg in "$@"; do
    case "$arg" in
        --doctor)   run_doctor=true;  run_lint=false; run_triggers=false; selected_any=true ;;
        --lint)     run_doctor=false; run_lint=true;  run_triggers=false; selected_any=true ;;
        --triggers) run_doctor=false; run_lint=false; run_triggers=true;  selected_any=true ;;
        --all)      run_doctor=true;  run_lint=true;  run_triggers=true ;;
        --json)     json_mode=true ;;
        -h|--help)
            sed -n '2,/^$/p' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *)
            echo "unknown flag: $arg" >&2
            exit 64
            ;;
    esac
done

# Combine subsequent selector flags by OR if --all is mixed in. Simple enough
# that we just let the last one win — common case is no flags = run all.

worst_rc=0
hr() { printf '\n────────────────────────────────────────────────────────────────────\n'; }

run_step() {
    local name="$1"; shift
    if ! $json_mode; then
        hr
        echo "▶ $name"
        hr
    fi
    "$@"
    local rc=$?
    # Exit-code ordering: 1 (FAIL) is worse than 2 (WARN) is worse than 0 (OK).
    # Each script uses its own convention; normalize here.
    if [ $rc -eq 1 ]; then
        worst_rc=1
    elif [ $rc -eq 2 ] && [ $worst_rc -eq 0 ]; then
        worst_rc=2
    fi
}

if $json_mode; then
    # JSON-combined output: emit a {steps: [...]} object with each step's output.
    printf '{\n  "steps": [\n'
    first=true
    emit() {
        local name="$1"; shift
        local out
        out=$("$@" --json 2>&1)
        local rc=$?
        if ! $first; then printf ',\n'; fi
        first=false
        printf '    {"step": "%s", "exit": %d, "output": %s}' \
            "$name" "$rc" "${out:-null}"
        if [ $rc -eq 1 ]; then worst_rc=1
        elif [ $rc -eq 2 ] && [ $worst_rc -eq 0 ]; then worst_rc=2
        fi
    }
    $run_doctor   && emit doctor   python3 "$ROOT/scripts/retritis_doctor.py"
    $run_lint     && emit lint     python3 "$ROOT/scripts/skill_drift_lint.py"
    $run_triggers && emit triggers python3 "$ROOT/scripts/trigger_analysis.py" --recent 7
    printf '\n  ],\n  "exit": %d\n}\n' "$worst_rc"
    exit $worst_rc
fi

$run_doctor   && run_step "doctor"   python3 "$ROOT/scripts/retritis_doctor.py"
$run_lint     && run_step "lint"     python3 "$ROOT/scripts/skill_drift_lint.py"
$run_triggers && run_step "triggers" python3 "$ROOT/scripts/trigger_analysis.py" --recent 7

hr
case $worst_rc in
    0) echo "✅ retritis health: all checks passed" ;;
    1) echo "❌ retritis health: at least one hard failure" ;;
    2) echo "⚠️  retritis health: warnings only" ;;
esac
hr
exit $worst_rc
