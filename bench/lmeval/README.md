# lmeval — local-model evaluation with Claude sub-agent judges (longitudinal)

Steps around driving a live Claude agent: instead, **local models** (ollama on
longbottom's GPU) are the agents under test, and **Claude sub-agents** are the judges,
under a bias-control protocol, with everything persisted for **longitudinal** comparison.

## The protocol (one row per question × local-model × run)
1. **Local answer.** The local model (e.g. `qwen3:14b-iq4xs`) answers the question via
   ollama (`lmeval.ollama_answer`).
2. **Blind judge reference (phase 1).** A Claude sub-agent is given *only the question*
   and told to answer and commit — no hint that a review or another model exists. This is
   the bias control: the judge fixes a reference **before** it can be anchored by the
   candidate. Its answer is saved **verbatim** (it's contract data — the reference moves as
   the judge model drifts, so you need it to interpret a delta later).
3. **Review (phase 2).** A reviewer is given (question, the committed reference, the
   candidate) and returns a **pinned structured rubric** — no free-form stars (judges drift
   on those un-recalibratably):
   `{correct: bool, completeness: 0-3, judge_would_use_local: bool, notes: str}`.
4. **Persist.** `lmeval.save_eval` writes a row to `results/lmeval.duckdb` with **both**
   `local_model` and `judge_model` ids (either can move; "score went up" is ambiguous
   without knowing which model changed), the candidate + the judge's own answer, the
   rubric, and local latency.
5. **Compare longitudinally.** `python lmeval.py compare [question_id]` →
   per (question, local_model, judge_model) over time.

## Orchestration
`lmeval.py` is the scriptable, deterministic half (ollama call, DuckDB store, compare).
The judge is a Claude sub-agent driven by the orchestrator via the **Agent tool**:
phase 1 = spawn with the answer-only prompt (blind); phase 2 = a reviewer given the
committed reference + candidate (or `SendMessage` to continue the same agent where that
tool is available — both preserve the blind property, since the reference was fixed in
phase 1). The judge's verbatim reference is kept (`results/_judge_answer.txt` is scratch;
the durable copy is the `judge_answer` column).

## Run
See **RUN.md** for the turnkey procedure (`gen-local` → blind references → reviews → report).
The set: 8 questions x 6 models (`questions.jsonl`, `models.txt`).

- Add questions to `questions.jsonl` (`{"id","question"}`). Pick tasks with **non-obvious
  correct answers** or suite-domain depth — NOT the phase-4 bench scenarios (the judge
  knows their fixes, which breaks the blind-reference property).
- Local answer: `python -c "import lmeval,json; q=json.loads(open('questions.jsonl').readline()); print(lmeval.ollama_answer('qwen3:14b-iq4xs', q['question']))"`
- Judge phases: orchestrated via the Agent tool (see above).
- `python lmeval.py compare`

## First result (2026-05-26)
`q_movavg_offbyone` — a moving-average function with a loop-range off-by-one.
`qwen3:14b-iq4xs` (273s): **correct=true, completeness=2, would-use=true** — it produced
the right bug conclusion + a correct fix, but via a **wrong mechanism** ("the initial
window is not appended" — false; the original code does append it). The judge caught the
reasoning flaw despite the correct output. Exactly the discrimination the protocol exists
to capture.
