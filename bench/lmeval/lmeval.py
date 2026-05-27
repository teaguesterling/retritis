"""Local-model evaluation harness with Claude sub-agent judges (longitudinal).

The loop (one row per question x local-model x run):
  1. a LOCAL model (ollama, e.g. qwen3:14b-iq4xs) answers the question.
  2. a Claude SUB-AGENT judge, BLIND, answers the same question itself first and commits
     to it (phase 1) — then reviews the local model's answer against its own (phase 2).
     The answer-first ordering is the bias control: the judge commits a reference before
     it ever sees the local attempt. (Orchestrated by the caller via the Agent tool +
     SendMessage — see README.)
  3. everything is persisted to DuckDB so runs compare LONGITUDINALLY.

Persisted per the eval-design notes:
  - the judge's OWN answer verbatim (contract data: the reference moves as the judge model
    drifts, so you need it to interpret a delta — not throwaway scratch).
  - both `local_model` AND `judge_model` ids (either can move; "score went up" is ambiguous
    without knowing which model changed).
  - a structured rubric, pinned up front (no free-form stars — judges drift on those):
      correct (bool), completeness (0-3), judge_would_use_local (bool), notes (str).
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

import duckdb

HERE = Path(__file__).parent
DB = HERE / "results" / "lmeval.duckdb"
OLLAMA = "http://localhost:11434/api/chat"

_DDL = """
CREATE TABLE IF NOT EXISTS evals (
    run_ts                 TIMESTAMP,
    question_id            VARCHAR,
    question               VARCHAR,
    local_model            VARCHAR,
    judge_model            VARCHAR,
    local_answer           VARCHAR,
    judge_answer           VARCHAR,   -- the judge's own blind reference answer (verbatim)
    correct                BOOLEAN,   -- judge's verdict on the local answer
    completeness           INTEGER,   -- 0..3
    judge_would_use_local  BOOLEAN,
    notes                  VARCHAR,
    local_latency_s        DOUBLE
)
"""


def _db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB))
    con.execute(_DDL)
    return con


def ollama_answer(model: str, question: str, timeout: int = 600) -> tuple[str, float]:
    """The local model under test answers the question. Returns (answer, latency_s)."""
    payload = {"model": model, "messages": [{"role": "user", "content": question}], "stream": False}
    t = time.time()
    req = urllib.request.Request(OLLAMA, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    resp = json.load(urllib.request.urlopen(req, timeout=timeout))
    return resp["message"]["content"], round(time.time() - t, 1)


def save_eval(*, question_id, question, local_model, judge_model, local_answer,
              judge_answer, correct, completeness, judge_would_use_local, notes,
              local_latency_s=None) -> None:
    con = _db()
    con.execute(
        "INSERT INTO evals VALUES (now(), ?,?,?,?,?,?,?,?,?,?,?)",
        [question_id, question, local_model, judge_model, local_answer, judge_answer,
         bool(correct), int(completeness), bool(judge_would_use_local), notes, local_latency_s],
    )
    con.close()


def compare(question_id: str | None = None):
    """Longitudinal view: per (question, local_model, judge_model) over time."""
    con = _db()
    where = "WHERE question_id = ?" if question_id else ""
    rows = con.execute(
        f"""SELECT run_ts, question_id, local_model, judge_model, correct, completeness,
                   judge_would_use_local, left(notes, 80) AS notes
            FROM evals {where} ORDER BY question_id, local_model, run_ts""",
        [question_id] if question_id else [],
    ).fetchall()
    con.close()
    return rows


if __name__ == "__main__":
    import sys
    if sys.argv[1:] and sys.argv[1] == "compare":
        for r in compare(*sys.argv[2:3]):
            print(r)
    else:
        print(f"DB: {DB} (exists={DB.exists()})")
