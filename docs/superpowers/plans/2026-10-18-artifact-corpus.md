# artifact-corpus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete, kind-filterable inventory of Teague's published claude.ai artifacts, and a ZIM-backed SQL query surface over it for agents.

**Architecture:** Two new private repos. `artifact-corpus` holds the bash helpers, the SQL, the skill and the installer. `artifact-ledger` holds `ledger.csv` and `overrides.csv` (references only). Both become submodules of `~/.dotfiles`. Unauthenticated helpers harvest artifact ids from transcripts and sync the ledger through git. Authenticated reads happen only in a session, through a subagent that calls `Artifact read` and then `artifact-corpus-ingest`. `artifact-corpus-build` writes `corpus.zim` with duckdb_zim. `artifact-corpus-query` loads `sql/corpus.sql` macros over it.

**Tech Stack:** bash, DuckDB CLI v1.5.6, community extensions `zim` (aa7aea2) and `webbed` (1716034), git with a custom merge driver, a systemd user timer, `gh`.

**Spec:** `docs/superpowers/specs/2026-10-18-artifact-corpus-design.md` (read it with `docs/briefs/2026-10-18-artifact-corpus.md`).

## Global Constraints

- No artifact HTML and no ZIM in any git repo. The ledger holds references only.
- Cache root: `${ARTIFACT_CORPUS_CACHE:-$HOME/.cache/artifact-corpus}`, with `html/<canonical_id>.html` and `corpus.zim`.
- Ledger repo path: `${ARTIFACT_LEDGER:-$HOME/.dotfiles/artifact-ledger}`.
- Pin to served extensions: `INSTALL zim FROM community; INSTALL webbed FROM community;`. If a newer build is installed, re-measure the API.
- `COPY … (FORMAT zim)` never overwrites. Always write to `<out>.tmp.<pid>`, then `mv` it into place.
- **Gotcha 1:** evidence/caption pairs come from one indexed XPath per container, never from a parallel `unnest`.
- **Gotcha 2:** `//dd/text()` gives the value and `//dd/small` gives the unit. Never take `//dd` whole.
- **Gotcha 3:** a `zim_search` snippet is never returned as a value. Re-extract fields by XPath.
- Kind vocabulary: `explanation`, `board`, `app`, `design`, `unknown`. `kind_source`: `meta`, `inferred`, `model`, `override`.
- Id grammar: a short id matches `[A-Za-z0-9]{22}`; a UUID matches `[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}`. Anything else is rejected.
- Every helper exits non-zero, with a message on stderr, when it fails. No helper prints success it did not verify.
- Commits end with the session's `Co-Authored-By` and `Claude-Session` lines.

**Spec amendment made by this plan.** The design has `status=cached`. A shared ledger cannot know whether *this* machine has the file. The ledger therefore records `status=read` (the artifact was read at `version`), and *cached* is computed locally: the file exists and its sha256 matches. The design document is edited in Task 1 to match.

## Review Focus

1. **A `read` row whose HTML is missing on this machine** (after a fresh clone, or on the other host). Expected: the build skips it, status counts it as "needs local read", and the refresh work set includes it. → Task 4 test `build_skips_uncached`, Task 7 test `status_counts_uncached`.
2. **A page with no `.evidence`, no `dl.strip` and no footer** (a game). Expected: zero rows from those macros, and no error. → Task 6 test `empty_page_yields_no_rows`.
3. **A truncated id in a transcript** (`9a0a038d-`, found in the real data). Expected: rejected, with no stub row. → Task 2 test `harvest_rejects_fragment`.
4. **A title that contains a comma, a quote or a newline.** Expected: the CSV round-trips it unchanged through harvest, ingest and merge. → Task 3 test `ingest_title_csv_roundtrip`.
5. **A footer link that uses the UUID alias of an artifact whose canonical id is the short id.** Expected: `citations()` reports the canonical id. → Task 6 test `citations_normalize_alias`.

---

## File structure

```
~/Projects/artifact-corpus/            (repo: teaguesterling/artifact-corpus, private)
  bin/artifact-corpus-harvest          transcripts/seed → stub rows
  bin/artifact-corpus-ingest           saved read file → cache + ledger row
  bin/artifact-corpus-resolve          alias resolution → canonical_id
  bin/artifact-corpus-build            cache → corpus.zim
  bin/artifact-corpus-query            duckdb session with views + macros
  bin/artifact-corpus-status           coverage, counts, work set, merge candidates
  bin/artifact-corpus-sync             pull, harvest, commit, push
  bin/artifact-corpus-merge            git merge driver for ledger.csv
  lib/common.sh                        paths, die(), duckdb wrapper, id regex
  sql/ledger.sql                       ledger schema + upsert macros
  sql/corpus.sql                       query macros
  skill/SKILL.md                       routing table, refresh procedure, gotchas
  systemd/artifact-corpus-sync.{service,timer}
  install.sh                           links bin, skill, merge driver, timer
  test/run.sh                          runs test/t_*.sh, prints pass/fail counts
  test/lib.sh                          assert_eq, assert_contains, fixture setup
  test/fixtures/                       html pages, jsonl transcripts, seed file
~/Projects/artifact-ledger/            (repo: teaguesterling/artifact-ledger, private)
  ledger.csv  overrides.csv  .gitattributes  README.md
```

Ledger columns, in order: `id,canonical_id,title,kind,kind_source,project,first_seen,updated,version,sha256,seen_by,status,owner`.
`overrides.csv` columns: `id,field,value` (a field is one of `kind`, `canonical_id` or `status`).

---

### Task 1: Scaffold both repos, the test harness, and the fixtures

**Files:**
- Create: `~/Projects/artifact-corpus/{lib/common.sh,test/run.sh,test/lib.sh,test/fixtures/*}`, `README.md`, `.gitignore`
- Create: `~/Projects/artifact-ledger/{ledger.csv,overrides.csv,.gitattributes,README.md}`
- Modify: `docs/superpowers/specs/2026-10-18-artifact-corpus-design.md` (retritis worktree): replace `status=cached` with `read` in §5.2, and add the "cached is local" sentence. In §5.1a, replace the relative-symlink paragraph with "`.dotfiles/install.sh` gains `install_directory "artifact-corpus/skill" ".claude/skills/artifact-corpus"`; no skill is linked by install.sh today."

**Interfaces:**
- Produces, `lib/common.sh`: `AC_CACHE`, `AC_LEDGER_DIR`, `AC_ROOT` (repo root); `die MSG` (stderr, exit 1); `ac_duckdb SQL...` (runs `duckdb -batch -bail -c "LOAD zim; LOAD webbed; $SQL"`, exits non-zero on error); `AC_ID_RE` (the combined id regex from Global Constraints).
- Produces, `test/lib.sh`: `assert_eq EXPECTED ACTUAL NAME`, `assert_contains HAYSTACK NEEDLE NAME`, `fresh_env` (a temp `AC_CACHE` and a temp ledger dir seeded from the header-only CSVs; exports both env vars).
- Produces, fixtures:
  - `pages/AlphaShortId0000000000.html`: house style with `<meta name="artifact:kind" content="explanation">`, one `.ruling`, three `.evidence` (the 2nd has no `.cap`), `dl.strip` with `dt tests` / `dd 1,230<small>assertions</small>`, and a footer that links `https://claude.ai/code/artifact/0b0b0b0b-0000-4000-8000-000000000000` and `https://claude.ai/artifact/QJFXq5DRqdUstNdbt1dCh7`.
  - `pages/BetaGameShortId00000000.html`: `<canvas>` only.
  - `pages/GammaNoMetaShortId00000.html`: `.standfirst` and `.ruling`, but no meta tag.
  - `transcripts/-home-x-Projects-demo/s1.jsonl`: lines containing both URL forms, the fragment `claude.ai/code/artifact/9a0a038d-`, and a duplicate of one id.
  - `seed.txt`: one URL per line.
  - Saved-read files named the way `Artifact read` names them: `artifact-<id8>-<version>.html`.

- [ ] **Step 1:** `git init` both repos under `~/Projects/`. Write `ledger.csv` (header only) and `overrides.csv` (header only). Write `.gitattributes` with `ledger.csv merge=artifact-ledger`. Add `.gitignore` in artifact-corpus with `*.zim`, `cache/`.
- [ ] **Step 2:** Write `test/run.sh`. It sources `test/lib.sh`, runs each `test/t_*.sh` in a subshell, and prints `N passed, M failed`. It exits 1 if M > 0, **and also if N = 0** (absence of signal is not success).
- [ ] **Step 3:** Write `test/t_00_harness.sh`, which calls `assert_eq 1 1 harness`. Then run: `test/run.sh`. Expected: `1 passed, 0 failed`. Delete one assert and run it again. Expected: exit 1, `0 passed` (the guard fires).
- [ ] **Step 4:** Write `lib/common.sh` and the fixtures. Test `t_01_env.sh`: `ac_duckdb "SELECT 42"` prints `42`; `ac_duckdb "SELEC"` exits non-zero.
- [ ] **Step 5:** Run `test/run.sh`. Expected: all pass. Commit each repo (`chore: scaffold`). Commit the spec amendment in the retritis worktree.

### Task 2: Harvest — transcripts and seeds become stub rows

**Files:** Create `bin/artifact-corpus-harvest`, `sql/ledger.sql`; Test `test/t_10_harvest.sh`

**Interfaces:**
- Consumes: `lib/common.sh`.
- Produces: `artifact-corpus-harvest [--projects DIR] [--seed FILE] [--host NAME]`. The defaults are `~/.claude/projects` and `$(hostname -s)`. The command rewrites `$AC_LEDGER_DIR/ledger.csv` sorted by `id` and prints `harvest: +N new, M seen`.
- Produces, `sql/ledger.sql`: `ledger_upsert_seen(obs)`, a table macro over a relation `(id, project, seen_date, source)`. It returns the full merged ledger:
  - a new id gets `canonical_id=id`, `status='stub'`, `kind='unknown'`, `kind_source='inferred'`, `owner=''`;
  - an existing id gets only `seen_by` (a set union, `;`-joined, sorted) and `first_seen=min(...)`;
  - every other column is unchanged.

- [ ] **Step 1: Failing tests** in `t_10_harvest.sh`, using `fresh_env` and `--projects test/fixtures/transcripts --host snape`:
  - `harvest_finds_both_forms`: the ledger has exactly the short id and the UUID from the fixture (`assert_eq 2 rows`).
  - `harvest_rejects_fragment`: no row whose id starts with `9a0a038d`.
  - `harvest_idempotent`: a second run leaves the file byte-identical (compare `sha256sum`) and prints `+0 new`.
  - `harvest_merges_hosts`: running again with `--host longbottom` gives `seen_by` = `transcript:longbottom;transcript:snape`.
  - `harvest_seed`: `--seed test/fixtures/seed.txt` adds its ids with `seen_by` containing `manual`.
  - `harvest_keeps_read_rows`: after a row is set to `status=read,version=v1` by hand, harvest leaves both fields unchanged.
- [ ] **Step 2:** Run `test/run.sh`. Expected: these six FAIL (command not found).
- [ ] **Step 3:** Implement. Extract with `grep -rhoE 'claude\.ai/(code/)?artifact/[^"\\ )<>]+'`, then keep only the ids that fully match `AC_ID_RE`. The project is the transcript's parent dir name; `seen_date` is the file mtime date. Feed the observations to DuckDB and `COPY` the result to `ledger.csv.tmp`, then `mv` it into place.
- [ ] **Step 4:** Run `test/run.sh`. Expected: all pass.
- [ ] **Step 5:** Commit `feat(harvest): transcript and seed ids into stub ledger rows`.

### Task 3: Ingest — a saved read file goes to the cache and the ledger row

**Files:** Create `bin/artifact-corpus-ingest`; Modify `sql/ledger.sql`; Test `test/t_20_ingest.sh`

**Interfaces:**
- Consumes: `ledger.csv` written by Task 2.
- Produces: `artifact-corpus-ingest --id ID --owner mine|other [--updated DATE] [--kind-guess KIND] FILE`.
  - The version is parsed from FILE's name `artifact-<id8>-<version>.html`; die if the name does not match.
  - `owner=other`: set `status=foreign`, `owner=other`; no copy.
  - `owner=mine`: copy to `$AC_CACHE/html/<id>.html`. Set `version`, `sha256`, `title` (`//title`), `status=read`, `owner=mine`. Set `kind`/`kind_source` by the first match of:
    1. `//meta[@name="artifact:kind"]/@content` → `meta`;
    2. `.standfirst` or `.ruling` or (`.eyebrow` and `.byline`) → `explanation`/`inferred`;
    3. `--kind-guess` → `model`;
    4. otherwise `unknown`/`inferred`.
  - It prints one line: `id\ttitle\tversion\tstatus`. **It never prints HTML.**
- Produces, `sql/ledger.sql`: `ledger_set_read(...)`, used by the ingest step.

- [ ] **Step 1: Failing tests**:
  - `ingest_meta_kind`: Alpha → `kind=explanation,kind_source=meta`, `status=read`, sha matches `sha256sum` of the cached file.
  - `ingest_inferred_kind`: Gamma → `explanation/inferred`.
  - `ingest_model_guess`: Beta with `--kind-guess app` → `app/model`; Beta without the flag → `unknown/inferred`.
  - `ingest_foreign`: `--owner other` → `status=foreign`, and no file in the cache.
  - `ingest_bad_name`: a file named `x.html` → exit 1.
  - `ingest_title_csv_roundtrip`: a fixture whose `<title>` is `A, "quoted"\nTitle` reads back from `ledger.csv` byte-equal (Review Focus 4).
  - `ingest_output_has_no_html`: stdout has no `<`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement. The id may be new to the ledger: insert it with `seen_by='read'`.
- [ ] **Step 4:** Run. Expected: all pass.
- [ ] **Step 5:** Commit `feat(ingest): cache a saved read and record version, sha, kind`.

### Task 4: Resolve aliases and build the ZIM

**Files:** Create `bin/artifact-corpus-resolve`, `bin/artifact-corpus-build`; Test `test/t_30_resolve.sh`, `test/t_40_build.sh`

**Interfaces:**
- Produces: `artifact-corpus-resolve`. It rewrites `canonical_id` (spec §5.3):
  - a UUID row merges into a short-id row with an equal non-empty `version`; failing that, an equal non-empty `sha256`;
  - otherwise `canonical_id=id`;
  - `overrides.csv` `canonical_id` entries win.
  - It prints `resolve: N merged, M candidates` (a candidate is an equal title with no version or sha match).
- Produces: `artifact-corpus-build [--out PATH]` (default `$AC_CACHE/corpus.zim`).
  - It takes rows where `id = canonical_id`, `status='read'`, `owner='mine'`, the file exists, and the file's sha256 equals the ledger's `sha256`. It also applies `overrides.csv` `status=excluded`.
  - ZIM columns: `path=canonical_id`, `title`, `mimetype='text/html'`, `content`. Options: `TITLE 'Artifact Corpus', LANGUAGE 'eng', INDEX true`. The write goes to `PATH.tmp.$$`, then `mv`.
  - It prints `build: N pages, K skipped (uncached or stale)`.

- [ ] **Step 1: Failing tests**:
  - `resolve_by_version`: the UUID row and the Alpha row have the same version → the UUID's `canonical_id` is Alpha's id.
  - `resolve_by_sha`: different versions, same sha → merged.
  - `resolve_title_only_is_candidate`: same title only → not merged, output `1 candidates`.
  - `resolve_override_wins`.
  - `build_basic`: after ingesting Alpha, Beta and Gamma, `read_zim` lists 3 paths.
  - `build_twice`: running a second build succeeds (no-overwrite gotcha) and leaves no `*.tmp.*` file.
  - `build_skips_uncached` (Review Focus 1): delete Gamma's cached file → `2 pages, 1 skipped`.
  - `build_excludes_foreign_and_alias`: a foreign row and a merged UUID row do not appear.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement both.
- [ ] **Step 4:** Run. Expected: all pass.
- [ ] **Step 5:** Commit `feat(build): alias resolution and corpus.zim build`.

### Task 5: Query session and inventory

**Files:** Create `bin/artifact-corpus-query`, `sql/corpus.sql`; Test `test/t_50_query.sh`

**Interfaces:**
- Produces: `artifact-corpus-query [SQL]`. It starts DuckDB, loads both extensions, and creates temp objects:
  - `ledger`: the CSV with overrides applied;
  - `pages(id, title, html)`: materialized once from `read_zim` + `zim_get_text`;
  - `zim_path`: a one-row table holding the ZIM path, for `prior_art`.
  It then reads `sql/corpus.sql`. With SQL it runs and exits; without it, it is interactive.
- Produces macros: `inventory(kind_filter := NULL)` → `(canonical_id, title, kind, kind_source, project, updated, status, aliases VARCHAR[], cached BOOLEAN)`, and `coverage()` → one row `(line VARCHAR)`. Example line: `coverage: list window (50) + transcripts snape since 2026-08-07 + 0 manual seeds; 3 read, 1 stub, 0 foreign`.

- [ ] **Step 1: Failing tests**: `inventory_all` (3 rows after Task 4 fixtures); `inventory_kind_filter` (`'explanation'` → 2); `inventory_aliases` (Alpha lists the UUID alias); `override_kind_wins`; `coverage_line` (contains `transcripts snape since`).
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: all pass.
- [ ] **Step 5:** Commit `feat(query): query session, inventory and coverage`.

### Task 6: Extraction macros, with the gotchas encoded

**Files:** Modify `sql/corpus.sql`; Test `test/t_60_extract.sh`

**Interfaces:**
- Produces:
  - `rulings(kind_filter := 'explanation')` → `(id, title, ruling)`;
  - `evidence()` → `(id, idx, evidence, caption)`;
  - `strip()` → `(id, idx, label, value, unit)`;
  - `citations()` → `(from_id, to_id, to_known BOOLEAN, text)`;
  - `prior_art(q)` → `(id, title, eyebrow, standfirst, score)`.

- [ ] **Step 1: Failing tests**:
  - `evidence_aligned`: Alpha gives exactly `1|E1|C1`, `2|E2|NULL`, `3|E3|C3`.
  - `strip_split`: `tests|1,230|assertions`.
  - `rulings_basic`: Alpha and Gamma rulings; Beta is absent.
  - `citations_normalize_alias` (Review Focus 5): the footer's UUID link yields `to_id` = Alpha's canonical id, and the QJFX link yields `to_known=false` in the fixture ledger.
  - `prior_art_no_snippet`: `prior_art('widgets')` returns Alpha with `standfirst='About widgets.'`. Assert that no column contains `1,230assertions`.
  - `empty_page_yields_no_rows` (Review Focus 2): `evidence()`, `strip()` and `citations()` all return 0 rows for Beta, and do not error.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement. `evidence` and `strip` use `generate_series(1, k)` with indexed XPaths, as in the brief: `(//dl[contains(@class,"strip")]/dt)[i]` and `(//dl[contains(@class,"strip")]/dd)[i]/text()` and `…/small`. `citations` extracts the id from the href with `AC_ID_RE` and maps it through `ledger` aliases.
- [ ] **Step 4:** Run. Expected: all pass.
- [ ] **Step 5:** Commit `feat(query): rulings, evidence, strip, citations, prior_art`.

### Task 7: Status, the merge driver, and sync

**Files:** Create `bin/artifact-corpus-status`, `bin/artifact-corpus-merge`, `bin/artifact-corpus-sync`; Test `test/t_70_status.sh`, `test/t_80_sync.sh`

**Interfaces:**
- Produces: `artifact-corpus-status [--worklist]`. It prints `coverage()`, counts by status and kind, `needs local read: N`, and the merge candidates.
  - `--worklist` prints only the ids to read, one per line: `stub` rows, `read` rows that are uncached here, and rows whose `updated` date is later than the read time. The read time is the version's leading epoch seconds: `1787021896-0172` gives `to_timestamp(1787021896)`, about 2026-08-18. That matches the observed page. The mapping is inferred from two samples, so Task 10 must verify it.
- Produces: `artifact-corpus-merge BASE OURS THEIRS` (git merge-driver argument order `%O %A %B`; it writes the result to OURS). Per id it unions the rows:
  - `status` precedence: `foreign` > `read` > `stub`;
  - `version`, `sha256` and `title` come from the side with the later `version`;
  - `seen_by` is a set union; `first_seen` is the min.
  - It exits 0. It exits 1 only on a parse error.
- Produces: `artifact-corpus-sync`.
  1. `git -C $AC_LEDGER_DIR pull --rebase`, then harvest.
  2. If `ledger.csv` changed: commit `ledger: harvest <host> <date>`, then push.
  3. If the push is rejected: pull --rebase once and push again.
  4. On any failure: write `~/.claude/inbox/artifact-corpus-sync.md` (house inbox format, ending `Dismiss once handled: claude-inbox dismiss artifact-corpus-sync`) and exit 1.

- [ ] **Step 1: Failing tests**:
  - `status_counts_uncached` (Review Focus 1);
  - `status_worklist` (stub + uncached ids, sorted);
  - `merge_union` (ours adds A, theirs adds B → both);
  - `merge_status_precedence` (ours `stub`, theirs `read v2` → `read v2`);
  - `sync_two_hosts`: a bare repo plus two clones. Each harvests different fixture transcripts, and both sync. The second sync's push is rejected, it rebases through the driver, and the end state on the remote has both hosts' ids. Use `git config merge.artifact-ledger.driver` in each clone.
  - `sync_failure_writes_inbox`: an unreachable remote → exit 1, and the inbox file exists under a temp `HOME`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: all pass.
- [ ] **Step 5:** Commit `feat(sync): status, ledger merge driver, git sync with inbox on failure`.

### Task 8: Skill, installer, and timer

**Files:** Create `skill/SKILL.md`, `install.sh`, `systemd/artifact-corpus-sync.{service,timer}`; Test `test/t_90_install.sh`

**Interfaces:**
- Produces: `install.sh`. It is idempotent and safe to re-run. It:
  - links `bin/*` into `~/.local/bin/`;
  - links `skill/` to `~/.claude/skills/artifact-corpus` only if the target is absent or already ours;
  - sets `git -C $AC_LEDGER_DIR config merge.artifact-ledger.driver 'artifact-corpus-merge %O %A %B'`;
  - links the systemd units into `~/.config/systemd/user/` and runs `systemctl --user enable --now artifact-corpus-sync.timer` (`OnCalendar=hourly`, `Persistent=true`);
  - runs `INSTALL zim FROM community; INSTALL webbed FROM community;`.
- Produces: `skill/SKILL.md`, frontmatter `name: artifact-corpus`. Its description triggers on "have I written about", "prior artifacts", "cite earlier work", "rulings across artifacts", and the house-artifact "Before publishing" step. Sections:
  1. A routing table: instead of `Artifact list` + `read` on N pages, use `artifact-corpus-query "FROM rulings()"`. The table has one row per macro.
  2. **The refresh procedure:**
     - run `artifact-corpus-sync`;
     - call `Artifact list limit:50` and pass each id's `updated` through to ingest;
     - get `artifact-corpus-status --worklist`;
     - dispatch **one** subagent with the worklist. Per id, it calls `Artifact read`, then runs `artifact-corpus-ingest --id … --owner (mine if the header says "owned by you") --kind-guess (its one-word judgement) <saved path>`, and returns only the ingest lines;
     - run `artifact-corpus-resolve`, then `artifact-corpus-build`, then commit and push the ledger with `artifact-corpus-sync`.
  3. The three gotchas as rules.
  4. "Say what the inventory could not see": quote `coverage()` whenever you answer a completeness question.

- [ ] **Step 1: Failing test** `install_idempotent`: run `install.sh` twice under a temp `HOME` with `ARTIFACT_CORPUS_NO_SYSTEMD=1`. The links exist, the second run changes nothing, and the merge driver config is set.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement. Honour `ARTIFACT_CORPUS_NO_SYSTEMD=1` (tests only).
- [ ] **Step 4:** Run `test/run.sh`. Expected: everything passes. Then check the skill: a fresh subagent reads only `skill/SKILL.md` and must state the refresh procedure back correctly.
- [ ] **Step 5:** Commit `feat: skill, installer, systemd timer`.

### Task 9: Publish the repos, wire up dotfiles, update house-artifact

**Files:** Modify `~/.dotfiles/{.gitmodules,install.sh,.claude/skills/house-artifact/SKILL.md}`

This task is outward-facing: it creates GitHub repos and pushes. **Confirm with Teague before Step 1.**

- [ ] **Step 1:** `gh repo create teaguesterling/artifact-corpus --private --source ~/Projects/artifact-corpus --push`, and the same for `artifact-ledger`. Read the echo: each must report `private` and show the pushed branch.
- [ ] **Step 2:** In `~/.dotfiles`:
  - `git submodule add git@github.com:teaguesterling/artifact-corpus.git artifact-corpus`;
  - `git submodule add -b main git@github.com:teaguesterling/artifact-ledger.git artifact-ledger`;
  - `git config -f .gitmodules submodule.artifact-ledger.ignore all`.
  Verify: `git -C ~/.dotfiles config -f .gitmodules --get submodule.artifact-ledger.ignore` prints `all`.
- [ ] **Step 3:** In `.dotfiles/install.sh`, after the `git-wt` line, add `install_directory "artifact-corpus/skill" ".claude/skills/artifact-corpus"` and call `"$DOTFILES_DIR/artifact-corpus/install.sh"` (guarded by `-x`).
- [ ] **Step 4:** In house-artifact `SKILL.md`:
  - structure item 0: the line after `<title>` is `<meta name="artifact:kind" content="explanation">`;
  - "Mechanics that bite": when republishing an artifact from an earlier session, add the meta tag if it is missing (lazy retrofit);
  - "Before publishing": replace the generic sentence with `artifact-corpus-query "FROM prior_art('<topic>')"` before writing, and `FROM citations()` for the footer.
- [ ] **Step 5:** Commit in `.dotfiles` (`feat: artifact-corpus and artifact-ledger submodules, house-artifact kind tag`). Push only if Teague says so.

### Task 10: First real run on snape, then longbottom

No new code. This task measures. Record the results in the ledger repo `README.md` and in a house-artifact page.

- [ ] **Step 1:** Run `~/.dotfiles/install.sh` on snape. Check that `systemctl --user list-timers` shows `artifact-corpus-sync.timer`.
- [ ] **Step 2:** Run `artifact-corpus-sync`. Expected: `harvest: +62 new` give or take, because snape's transcripts held 62 ids on 2026-10-18. Record the actual number.
- [ ] **Step 3:** Run the skill's refresh procedure for real (the subagent reads everything). Then measure the spec §8 unknowns:
  - Do a UUID and its short id return the same version? Compare `bcaac9e4…` with `QJFXq5…`.
  - Does `read` on a deleted id fail?
  - How long does `zim_search` take?
  - Do the 5 unresolved UUIDs turn out to be aliases or distinct artifacts?
  Record each result as measured.
- [ ] **Step 4:** Run every macro against the real corpus. Spot-check 3 `evidence()` rows against the live pages by eye. If duckdb_zim misbehaves, file an issue in teaguesterling/duckdb_zim, or message the zim peer session (both authorized by Teague).
- [ ] **Step 5:** On longbottom: `ssh longbottom 'cd ~/.dotfiles && git pull && git submodule update --init artifact-corpus artifact-ledger && ./install.sh && artifact-corpus-sync'`. Record how many new ids longbottom's transcripts add.
- [ ] **Step 6:** Commit the ledger (through sync). Publish the results page. Comment once on retritis#17 with the link.
