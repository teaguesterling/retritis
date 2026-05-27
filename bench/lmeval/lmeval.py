"""Local-model evaluation benchmark with Claude sub-agent judges (longitudinal).

The loop, per (question x local-model), grouped by `run_tag`:
  1. LOCAL ANSWER  — the local model (ollama) answers (scriptable; `gen_local`, resumable).
  2. JUDGE REFERENCE (blind) — a Claude sub-agent answers the SAME question with no hint
     of any review/other model, committing a reference (bias control). ONE per question,
     reused to review every model's candidate. (Agent-tool orchestrated; `phase1_prompt`,
     `record_reference`.)
  3. REVIEW — a Claude sub-agent scores the candidate against the committed reference with
     a pinned rubric (no stars). (`phase2_prompt`, `record_review`.)
  4. PERSIST — one `evals` row per (run_tag, question, local_model) with BOTH model ids,
     the candidate AND the judge's own answer verbatim, and the rubric.
  5. REPORT  — `report(run_tag)`: per-model %correct / mean-completeness / would-use-rate.

Scriptable half = ollama gen + DuckDB store + report. Judge phases = the orchestrator
(main agent) spawning Agent sub-agents; the harness emits the prompts and ingests results,
and tracks state so a run is RESUMABLE (re-run gen-local; only-pending references/reviews).
See RUN.md for the turnkey procedure. Nothing here calls a live `claude` agent.
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import date
from pathlib import Path

import duckdb

HERE = Path(__file__).parent
DB = HERE / "results" / "lmeval.duckdb"
OLLAMA = "http://localhost:11434/api/chat"
DEFAULT_JUDGE = "claude-opus-4-7 (general-purpose subagent)"

_DDL = [
 # raw local-model answers (scriptable producer; resumable staging)
 """CREATE TABLE IF NOT EXISTS local_answers (
        run_tag VARCHAR, question_id VARCHAR, local_model VARCHAR,
        answer VARCHAR, latency_s DOUBLE, ts TIMESTAMP,
        PRIMARY KEY (run_tag, question_id, local_model))""",
 # judge's blind reference answer — one per (run_tag, question)
 """CREATE TABLE IF NOT EXISTS refs (
        run_tag VARCHAR, question_id VARCHAR, judge_model VARCHAR,
        answer VARCHAR, ts TIMESTAMP,
        PRIMARY KEY (run_tag, question_id))""",
 # final per-(question, local_model) eval record (longitudinal)
 """CREATE TABLE IF NOT EXISTS evals (
        run_tag VARCHAR, run_ts TIMESTAMP, question_id VARCHAR, question VARCHAR,
        local_model VARCHAR, judge_model VARCHAR, local_answer VARCHAR, judge_answer VARCHAR,
        correct BOOLEAN, completeness INTEGER, judge_would_use_local BOOLEAN,
        notes VARCHAR, local_latency_s DOUBLE,
        PRIMARY KEY (run_tag, question_id, local_model))""",
]


def _db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB))
    for ddl in _DDL:
        con.execute(ddl)
    return con


def questions() -> list[dict]:
    return [json.loads(l) for l in (HERE / "questions.jsonl").read_text().splitlines() if l.strip()]


def models() -> list[str]:
    return [l.strip() for l in (HERE / "models.txt").read_text().splitlines()
            if l.strip() and not l.startswith("#")]


# ── 1. local answers (scriptable, resumable) ─────────────────────────────────
def ollama_answer(model: str, question: str, timeout: int = 900) -> tuple[str, float]:
    payload = {"model": model, "messages": [{"role": "user", "content": question}], "stream": False}
    t = time.time()
    req = urllib.request.Request(OLLAMA, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    resp = json.load(urllib.request.urlopen(req, timeout=timeout))
    return resp["message"]["content"], round(time.time() - t, 1)


def gen_local(run_tag: str, only_models: list[str] | None = None,
              only_questions: list[str] | None = None) -> dict:
    """Generate every missing (question x model) local answer for run_tag. Resumable:
    skips pairs already stored. Returns {done, generated, remaining}. SLOW — run backgrounded."""
    con = _db()
    qs = [q for q in questions() if not only_questions or q["id"] in only_questions]
    ms = [m for m in models() if not only_models or m in only_models]
    have = {(r[0], r[1]) for r in con.execute(
        "SELECT question_id, local_model FROM local_answers WHERE run_tag = ?", [run_tag]).fetchall()}
    todo = [(q, m) for q in qs for m in ms if (q["id"], m) not in have]
    generated = 0
    for q, m in todo:
        try:
            ans, lat = ollama_answer(m, q["question"])
        except Exception as e:
            ans, lat = f"[ERROR: {type(e).__name__}: {e}]", None
        con.execute("INSERT OR REPLACE INTO local_answers VALUES (?,?,?,?,?,now())",
                    [run_tag, q["id"], m, ans, lat])
        generated += 1
        print(f"[gen_local] {q['id']} x {m}: {len(ans)} chars, {lat}s", flush=True)
    n_have = con.execute("SELECT count(*) FROM local_answers WHERE run_tag=?", [run_tag]).fetchone()[0]
    con.close()
    return {"done": n_have, "generated": generated, "remaining": 0}


# ── 2/3. judge phases (orchestrated via the Agent tool) ──────────────────────
def phase1_prompt(question: str) -> str:
    """BLIND reference prompt — no mention of review, comparison, or another model."""
    return ("You are answering a technical question as an expert. Answer it directly and "
            "completely, and commit to a final answer — this is your definitive response. "
            "Do not hedge, do not ask for clarification.\n\nQuestion:\n" + question)


def phase2_prompt(question: str, reference: str, candidate: str) -> str:
    """Review prompt — judge scores the candidate against its committed reference."""
    return f"""You previously answered the question below and committed to your own answer
(your REFERENCE, verbatim). Another AI model also answered it (the CANDIDATE). Review the
CANDIDATE against your REFERENCE and actual correctness.

Return ONLY a JSON object on the last line, exactly:
{{"correct": <true|false>, "completeness": <0|1|2|3>, "judge_would_use_local": <true|false>, "notes": "<1-2 sentences; cite any reasoning/code error even if the final answer is right>"}}
- correct: does the CANDIDATE reach the right answer/fix?
- completeness: 0=wrong/misses it, 1=core idea only, 2=correct + complete, 3=correct + rigor/edge-cases.
- judge_would_use_local: would you ship/rely on the CANDIDATE as-is?

=== QUESTION ===
{question}

=== YOUR REFERENCE ANSWER ===
{reference}

=== CANDIDATE ANSWER (other model) ===
{candidate}
"""


def pending_references(run_tag: str) -> list[str]:
    """question_ids that have >=1 local answer but no judge reference yet."""
    con = _db()
    rows = con.execute(
        """SELECT DISTINCT la.question_id FROM local_answers la
           LEFT JOIN refs r ON r.run_tag=la.run_tag AND r.question_id=la.question_id
           WHERE la.run_tag=? AND r.question_id IS NULL ORDER BY la.question_id""", [run_tag]).fetchall()
    con.close()
    return [r[0] for r in rows]


def pending_reviews(run_tag: str) -> list[tuple[str, str]]:
    """(question_id, local_model) with a local answer AND a reference but no eval yet."""
    con = _db()
    rows = con.execute(
        """SELECT la.question_id, la.local_model FROM local_answers la
           JOIN refs r ON r.run_tag=la.run_tag AND r.question_id=la.question_id
           LEFT JOIN evals e ON e.run_tag=la.run_tag AND e.question_id=la.question_id
                             AND e.local_model=la.local_model
           WHERE la.run_tag=? AND e.question_id IS NULL
           ORDER BY la.question_id, la.local_model""", [run_tag]).fetchall()
    con.close()
    return [(r[0], r[1]) for r in rows]


def get_local_answer(run_tag: str, question_id: str, model: str) -> str:
    con = _db()
    row = con.execute("SELECT answer FROM local_answers WHERE run_tag=? AND question_id=? AND local_model=?",
                      [run_tag, question_id, model]).fetchone()
    con.close()
    return row[0] if row else None


def get_reference(run_tag: str, question_id: str) -> str:
    con = _db()
    row = con.execute("SELECT answer FROM refs WHERE run_tag=? AND question_id=?",
                      [run_tag, question_id]).fetchone()
    con.close()
    return row[0] if row else None


def record_reference(run_tag: str, question_id: str, answer: str, judge_model: str = DEFAULT_JUDGE) -> None:
    con = _db()
    con.execute("INSERT OR REPLACE INTO refs VALUES (?,?,?,?,now())",
                [run_tag, question_id, judge_model, answer])
    con.close()


def record_review(run_tag: str, question_id: str, local_model: str, verdict: dict,
                  judge_model: str = DEFAULT_JUDGE) -> None:
    """Join the stored local answer + reference + this verdict into a final evals row."""
    con = _db()
    q = next((x for x in questions() if x["id"] == question_id), {"question": ""})
    la = con.execute("SELECT answer, latency_s FROM local_answers WHERE run_tag=? AND question_id=? AND local_model=?",
                     [run_tag, question_id, local_model]).fetchone()
    ref = con.execute("SELECT answer FROM refs WHERE run_tag=? AND question_id=?",
                      [run_tag, question_id]).fetchone()
    con.execute("INSERT OR REPLACE INTO evals VALUES (?,now(),?,?,?,?,?,?,?,?,?,?,?)",
        [run_tag, question_id, q["question"], local_model, judge_model,
         la[0] if la else None, ref[0] if ref else None,
         bool(verdict["correct"]), int(verdict["completeness"]),
         bool(verdict["judge_would_use_local"]), verdict.get("notes", ""), la[1] if la else None])
    con.close()


# ── 5. report ────────────────────────────────────────────────────────────────
def report(run_tag: str | None = None):
    con = _db()
    where = "WHERE run_tag=?" if run_tag else ""
    args = [run_tag] if run_tag else []
    per_model = con.execute(
        f"""SELECT local_model, count(*) n,
                   round(100.0*sum(correct::int)/count(*),0) pct_correct,
                   round(avg(completeness),2) mean_completeness,
                   round(100.0*sum(judge_would_use_local::int)/count(*),0) pct_would_use,
                   round(avg(local_latency_s),0) mean_latency_s
            FROM evals {where} GROUP BY local_model ORDER BY pct_correct DESC, mean_completeness DESC""",
        args).fetchall()
    con.close()
    return per_model


if __name__ == "__main__":
    import sys
    a = sys.argv[1:]
    if not a:
        print(f"DB {DB} (exists={DB.exists()}); {len(questions())} questions, {len(models())} models")
    elif a[0] == "gen-local":
        rt = a[1] if len(a) > 1 else str(date.today())
        print(json.dumps(gen_local(rt)))
    elif a[0] == "pending":
        rt = a[1] if len(a) > 1 else str(date.today())
        print("references needed:", pending_references(rt))
        print("reviews needed:", pending_reviews(rt))
    elif a[0] == "report":
        rt = a[1] if len(a) > 1 else None
        print("model | n | %correct | mean_completeness | %would_use | mean_latency_s")
        for r in report(rt):
            print("  ", r)
