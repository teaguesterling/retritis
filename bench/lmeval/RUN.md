# Running the lmeval benchmark (turnkey)

8 questions × 6 local models = **48 local answers**, then **8** blind judge references
(one per question, reused across models) + **48** reviews. Not yet run — this is the procedure.

`gen-local` is the slow part: the local GPU models take ~1–5 min each (qwen3:14b was 273s
on one question), so 48 answers ≈ **1–4 hours**. Background it. The judge phases are fast
but cost Claude tokens (8 + 48 sub-agent calls).

## Steps (resumable at every stage)

1. **Pick a run tag** (groups a longitudinal run): `TAG=2026-05-26` (or any label).

2. **Generate local answers** — scriptable, slow, resumable (skips pairs already stored):
   ```
   python lmeval.py gen-local $TAG     # background it: run_in_background / nohup
   ```
   Re-run anytime to fill gaps (e.g. after adding a model or a crash). Errors are stored
   as `[ERROR: ...]` answers, not lost.

3. **See what the judge owes** (after some local answers exist):
   ```
   python lmeval.py pending $TAG       # -> references needed: [...]; reviews needed: [(q,model),...]
   ```

4. **Judge phase 1 — blind references** (orchestrator spawns one Agent sub-agent per
   pending question; the prompt MUST be `phase1_prompt(question)` — no review hint):
   ```python
   import lmeval as L
   q = next(x for x in L.questions() if x["id"]==QID)
   # spawn Agent(prompt=L.phase1_prompt(q["question"]))  -> the agent's answer text
   L.record_reference(TAG, QID, answer_text)
   ```

5. **Judge phase 2 — reviews** (one Agent sub-agent per pending (q,model); feed the
   committed reference + the candidate; the agent returns a JSON verdict on its last line):
   ```python
   ref  = L.get_reference(TAG, QID)
   cand = L.get_local_answer(TAG, QID, MODEL)
   # spawn Agent(prompt=L.phase2_prompt(q["question"], ref, cand)) -> parse trailing JSON
   L.record_review(TAG, QID, MODEL, verdict_dict)
   ```

6. **Report**:
   ```
   python lmeval.py report $TAG        # per-model: n, %correct, mean_completeness, %would_use, mean_latency
   python lmeval.py report             # all run_tags (longitudinal)
   ```

## Why the split
`gen-local` + the DuckDB store + `report` are deterministic and scriptable. The judge is a
Claude sub-agent (Agent tool), so steps 4–5 are orchestrated by the main agent, not a cron
script — the harness emits the exact prompts (`phase1_prompt`/`phase2_prompt`) and ingests
results (`record_reference`/`record_review`), tracking state so the whole thing is resumable.
Re-run with a new `$TAG` later to get longitudinal deltas (both `local_model` and
`judge_model` are stored, so a moved score is attributable).
