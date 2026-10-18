# artifact-corpus — design

**Status:** design, pending approval. **Date:** 2026-10-18.
**Tracks:** teaguesterling/retritis#17. **Brief:** `docs/briefs/2026-10-18-artifact-corpus.md`
(read it first; this document does not repeat its verified API or its two gotchas).
**Session:** claude.ai/code/session_01MPVDmdiyKDtqjzLw9yuqGp

---

## 1. Intent

Teague publishes HTML artifacts on claude.ai (about 60 so far). He rarely queries them
himself; he asks agents to, for example "what have we already written about X", "seed this
discussion from prior work". Today an agent does that by calling `Artifact list`, guessing
from titles, and calling `Artifact read` on whole pages. Each read puts the head of a page
into the main context, so a 20-page question costs 20 pages.

The house-artifact style makes a better path possible: its CSS class names (`.ruling`,
`.evidence`, `.cap`, `.strip`, `.standfirst`, `footer`) are also a schema. If the corpus is
held locally, an agent can pull every `.ruling` across the corpus in one SQL query and
never load a page.

So the product has two halves:

1. **An inventory** of *everything* Teague has published, of every kind. It must be
   complete, and it is filterable by kind.
2. **A query surface** over the local copy, for agents. It returns rulings, evidence with
   captions, strip metrics, the citation graph, and full-text prior-art search.

The primary consumer is an agent, not a human. The main entry point is the
`house-artifact` "Before publishing" step, which already says *"Use the `artifact-corpus`
skill to find them, and to check you are not rewriting a page that already exists"*.

## 2. Goals, non-goals, anti-goals

**Goals**
- A complete inventory: every published artifact, including those that `list` can no
  longer show.
- Agents can answer the five questions in the brief (rulings, measurements, headline
  figures, citation graph, prior art) without putting page HTML into their own context.
- Both machines (snape and longbottom) converge on one inventory.
- Every kind is inventoried (explanations, games, boards, design pages), and a filter can
  select by kind.

**Non-goals**
- A UI for Teague. The consumer is an agent; DuckDB SQL and the skill are the interface.
- Editing or republishing artifacts in bulk.
- Scraping claude.ai over HTTP (it returns the SPA shell or a 403).

**Anti-goals** (it would fail even if it technically worked)
- **Artifact content on GitHub.** The git repos hold references only.
- **Silent-wrong results.** A query that misaligns evidence and captions, or quotes a
  concatenated `1,230assertions`, is worse than no query.
- **A refresh that floods the main agent's context** with HTML.
- **An inventory that looks complete but is not.** It must say what it could not see.

## 3. Constraints (measured 2026-10-18 on snape unless noted)

| Fact | Evidence |
|---|---|
| Only a Claude session can read an artifact. No CLI or cron can. | The Artifact tool is the only authenticated reader; the brief records the curl failure. |
| `Artifact list` returns at most 50, newest-updated first, loosely ordered. Older ones fall outside the window. | `list limit:50` returned exactly 50 plus the warning; "Tiiny Field Guide" (08-18) sits among September entries. |
| Local transcripts know more than `list`. | 758 `.jsonl` under `~/.claude/projects`, oldest 2026-08-07: 62 distinct ids. All 50 listed ids are present, plus 11 in a second form. |
| One artifact can have **two ids**: a short id (`claude.ai/artifact/QJFXq5…`) and a UUID (`claude.ai/code/artifact/bcaac9e4-…`). | The UUID `bcaac9e4…` reads back with title "Failure Ledger", the same as listed `QJFXq5…`. This was inferred from the title and not proven by version. |
| At least one artifact is invisible to `list`. | UUID `9b899b5a…` is "Sparse Band Verdicts" (654 KB, about 2026-08-18) and is not in the 50. |
| `Artifact read` returns a version string and saves full HTML to `~/.claude/projects/<proj>/<session>/tool-results/artifact-<id8>-<version>.html`, but also prints a long head of the page inline. | Two reads in this session. The inline head is the context cost that must stay out of the main agent. |
| Git history and memory hold almost no artifact links. | git across `~/Projects` + `.dotfiles`: 0; memory and inbox: 1. |
| `~/.claude` is local per machine. `/srv/logical/workspace` on snape is NFS from longbottom. `~/Projects` on snape is local ext4. | `findmnt`. This conflicts with CLAUDE.md's "both paths resolve to the same files", and the conflict is flagged separately. |
| Published pages are wrapped: house-artifact files start with `<title>`, no `<head>`. | house-artifact SKILL.md "Mechanics that bite". `//meta` and `//title` XPaths still match anywhere. |

**The duckdb_zim + webbed pipeline: measured on served builds** (`zim` aa7aea2, `webbed`
1716034, DuckDB v1.5.6; scratch spike with two pages):

- `COPY (SELECT path, title, mimetype, content FROM read_text(...)) TO 'corpus.zim' (FORMAT zim, TITLE …, LANGUAGE 'eng', INDEX true)` writes a valid archive.
- `read_zim('corpus.zim')` lists path, title, and mimetype. `zim_get_text(zim, path)` returns the HTML.
- `html_extract_text(zim_get_text(...), '//meta[@name="artifact:kind"]/@content')` returns `[explanation]` on a tagged page and `[]` on an untagged one. **Attribute XPath works.**
- The brief's indexed evidence/caption idiom over `zim_get_text` gives `E1|C1`, `E2|NULL`, `E3|C3`.
- `//dd/text()` gives `1,230`, and `//dd/small` gives `assertions`.
- `html_extract_links` returns the footer href intact.
- `zim_search('corpus.zim', 'gizmos')` finds the right page with a snippet.
- **A third gotcha:** the `zim_search` snippet joins inline child text (`1,230assertions`), the same as gotcha #2. A snippet locates a page; it is never a value to quote.
- **Writing never overwrites:** `COPY … (FORMAT zim)` fails if the target exists. A rebuild writes to a temp path and then renames.

## 4. Decisions Teague made

1. **Inventory scope: everything**, with a kind tag for filtering.
2. **Kind tag:** new artifacts carry `<meta name="artifact:kind" content="…">`, emitted by
   `house-artifact`. The **back catalog keeps its kind in the ledger now**, and gets the meta
   tag only when an artifact is next republished for some other reason ("retrofit lazily").
   No bulk republish.
3. **Two private git repos, each a submodule of `~/.dotfiles`:**
   - a **handling repo** (`artifact-corpus`): the skill, the SQL, and the small helpers
     installed on snape and longbottom, including a periodic cron pull;
   - a **ledger repo**: the inventory data.
4. **The ledger repo holds references only.** No HTML and no ZIM in git. Each machine keeps
   a gitignored HTML cache and **builds `corpus.zim` locally** with duckdb_zim.
5. **Use duckdb_zim** (Teague's own extension) as the archive builder and reader. Teague
   authorized filing issues against it, fixing them, or messaging the zim peer session when
   the build exposes a real defect.
6. **"Creators" means the ZIM builder** (`artifact-corpus-build`). There is no scaffolder.
7. **The ledger submodule is set to `ignore = all` and tracks a branch.** `.dotfiles` never
   shows it as dirty, and its pointer is bumped only by hand. No automation commits to
   `.dotfiles`. A fresh clone holds a stale ledger until the first sync pull, and that is
   accepted.

## 5. Architecture

```
            ┌──────────── claude.ai (authenticated) ────────────┐
            │   Artifact list (≤50)        Artifact read (HTML)  │
            └───────────────┬──────────────────────┬────────────┘
                            │ session only          │ session only (subagent)
  transcripts ──harvest──►  ▼                       ▼
  (cron, per machine)   ledger repo  ◄──commit── refresh (skill)
   ~/.claude/projects    ledger.csv               │
                            │ git pull/push        ▼
                            │ (cron)          HTML cache (gitignored, per machine)
                            ▼                       │ COPY … (FORMAT zim)
                      both machines                 ▼
                                               corpus.zim  ──► webbed / zim_search
                                                              (agent queries via skill)
```

### 5.1 Layout

```
~/.dotfiles/
  artifact-corpus/                 # submodule: handling repo (private)
    skill/SKILL.md                 # the skill itself (see 5.1a)
    sql/corpus.sql                 # macros: rulings(), evidence(), strip(), links(), prior_art()
    bin/artifact-corpus-harvest    # transcripts → stub ledger rows (no auth)
    bin/artifact-corpus-sync       # git pull --rebase; harvest; commit+push if changed
    bin/artifact-corpus-build      # HTML cache → corpus.zim (temp + rename)
    bin/artifact-corpus-status     # counts: ledger rows, cached, stale, unresolved
    install.sh                     # symlinks bin/ and skill, installs the scheduler entry
  artifact-ledger/                 # submodule: ledger repo (private)
    ledger.csv
    overrides.csv                  # hand edits: kind, alias merges, excludes
~/.cache/artifact-corpus/          # gitignored, per machine
  html/<canonical_id>.html
  corpus.zim
```

### 5.1a Where the skill lives

The skill's files live in the handling repo. The brief's location is kept as a relative
symlink: `~/.dotfiles/.claude/skills/artifact-corpus -> ../../artifact-corpus/skill`. The
existing dotfiles mechanism then links it into `~/.claude/skills/` as it does
`house-artifact`. On a machine without the private submodule, the link dangles and the skill
is absent, which is the correct failure.

### 5.2 Ledger schema (`ledger.csv`, one row per *id seen*)

| column | meaning |
|---|---|
| `id` | the id as seen: a short id or a UUID |
| `canonical_id` | the id that the row resolves to. It equals `id` for the canonical row. |
| `title` | from `list` or from `<title>` |
| `kind` | `explanation` \| `board` \| `app` \| `design` \| `unknown` |
| `kind_source` | `meta` \| `inferred` \| `override` |
| `project` | the transcript's project dir, e.g. `-home-teague-Projects-Tiiny` |
| `first_seen` | the earliest transcript or `list` date |
| `updated` | the latest `updated` from `list`, if known |
| `version` | the version string from the last `read` |
| `sha256` | a hash of the cached HTML |
| `seen_by` | `list`, `transcript:snape`, `transcript:longbottom` (`;`-joined) |
| `status` | `stub` (id only) \| `cached` \| `unreadable` \| `excluded` \| `foreign` |
| `owner` | `mine` \| `other`, from the `read` header ("owned by you") or the `list` scope |

CSV is chosen because it diffs and merges line by line in git, and DuckDB reads it
natively. `overrides.csv` always wins over inferred values.

### 5.3 Canonical id and alias resolution

- **The short id is canonical** when an artifact has one, because `list` returns it.
- A UUID is merged into a short id when both read back with the **same version string**.
  Same title alone is **not** enough to merge; it only marks a *candidate*, which the
  status output reports. (Two artifacts can share a title.)
- **Fallback, if the version strings differ between the two forms** (§8 measures this):
  merge when the cached HTML has the **same `sha256`**. Identical bytes are the same page.
- Anything else that shares a title stays separate, and `artifact-corpus-status` reports it as
  a *merge candidate*. Teague settles a candidate in `overrides.csv` only if he wants to.
- A UUID with no match stays canonical for itself.
- **Every macro groups by `canonical_id`,** so an unmerged duplicate shows up as two rows
  in `inventory()` and never as a doubled ruling. (A known duplicate is visible; it is never
  silent.)

### 5.3a Ownership

The inventory is **Teague's own artifacts** ("an inventory of all artifacts I've created").
The transcript harvest also catches links to pages other people shared. When a `read`
header does not say "owned by you", the row becomes `owner=other`, `status=foreign`. It is
never cached, and the macros exclude it. It stays in the ledger so that the harvest does
not re-add it.

### 5.4 Kind inference (back catalog)

In order, the first match wins:
1. `overrides.csv`
2. `//meta[@name="artifact:kind"]/@content`
3. `explanation` if the page has `.standfirst` or `.ruling` or `.eyebrow` + `.byline`
4. **A model classification by the refresh subagent.** While the page is open, the
   subagent picks one kind from the vocabulary and records `kind_source=model`. This is a
   labelled guess: the source is visible, and an override replaces it.
5. `unknown`, if the subagent could not decide.

Structural rules (step 3) never assign `app`, `board` or `design`. Only a meta tag, an
override or a labelled model guess can.

### 5.5 Refresh flows

**Cron, per machine, unauthenticated** (`artifact-corpus-sync`):
1. Run `git pull --rebase` on the ledger repo.
2. Harvest (also accepts `--seed FILE`, a list of ids or URLs, for example copied once from
   the `claude.ai/code/artifacts` gallery, recorded as `seen_by=manual`): scan `~/.claude/projects/**/*.jsonl` for `claude.ai/(code/)?artifact/<id>`,
   with the project dir and file mtime. Add unseen ids as `stub` rows, and append
   `transcript:<hostname>` to `seen_by`.
3. If anything changed, commit and push. On a push conflict, rebase and retry once, then
   give up loudly (exit non-zero and write a note to the claude-inbox).

**Session, authenticated** (the skill's `refresh` step, run lazily when the skill loads and
the cache is stale):
1. Run `artifact-corpus-sync` first.
2. Call `Artifact list limit:50`, and upsert ids, titles, and `updated`.
3. Select the work set: `stub` rows, plus rows whose `updated` is newer than the cached
   version.
4. **Dispatch one subagent** for the work set. It calls `Artifact read` per id, copies the
   saved `tool-results/artifact-*.html` file into the cache as `<canonical_id>.html`,
   records `version`, `sha256` and `title`, and **returns only a table of id, title,
   version and status**. The main agent never sees HTML.
5. Resolve aliases (5.3), infer kinds (5.4), commit and push the ledger, and run
   `artifact-corpus-build`.

### 5.5a Completeness is reported as coverage, not as a missing count

Nobody can count artifacts that no source has seen. `artifact-corpus-status` therefore
states its coverage: "the 50 most recently updated pages, plus transcripts on <hosts> since
<oldest transcript date>, plus N manual seeds". The `inventory()` macro returns the same
coverage line, so an agent can say what the inventory could not see.

### 5.6 The query surface (skill)

`sql/corpus.sql` defines macros over `corpus.zim` joined to `ledger.csv`. Each macro
encodes the safe idiom:

| macro | returns | idiom |
|---|---|---|
| `inventory(kind := NULL)` | ledger rows plus `in_zim` | plain read |
| `rulings(kind := 'explanation')` | id, title, ruling text | `//div[contains(@class,"ruling")]/p` |
| `evidence()` | id, idx, evidence, caption | **indexed XPath per container** (gotcha #1) |
| `strip()` | id, label, value, unit | `//dd/text()` and `//dd/small` (gotcha #2), indexed per `dt` |
| `citations()` | from_id, to_id, link text | `html_extract_links`, href normalized to a canonical id |
| `prior_art(q)` | id, title, eyebrow, standfirst, score | `zim_search`, then **re-extract** eyebrow and standfirst by XPath. The snippet is never returned as a value (gotcha #3). |

The skill's SKILL.md follows the retritis pattern: a routing table ("instead of
`Artifact read` on N pages, use `rulings()`"), the refresh procedure, and the three gotchas
stated as rules.

### 5.7 Changes to `house-artifact`

- Emit `<meta name="artifact:kind" content="explanation">` directly after `<title>`.
- "Before publishing" already points at `artifact-corpus`; give it the concrete call:
  `prior_art('<topic>')` before writing, and `citations()` for the footer.
- On any republish of a back-catalog artifact, add the meta tag (lazy retrofit).

## 6. Calls I made (Claude), not Teague; check these

1. **The kind vocabulary:** `explanation`, `board`, `app`, `design`, `unknown`.
2. **Ledger format:** CSV, plus a separate `overrides.csv`.
3. **Alias merge needs a matching version string,** not a matching title.
4. **Cache location** `~/.cache/artifact-corpus/` (XDG). It is outside `~/.claude`, so
   Claude Code housekeeping does not touch it.
5. **Refresh is lazy** (when the skill loads and the cache is stale), plus cron for the
   unauthenticated half. There is no SessionStart hook.
6. **Alias fallback:** merge on identical `sha256`. A shared title only flags a candidate.
7. **Foreign artifacts** are tracked as `status=foreign` and excluded from queries.
8. **Labelled model kind-guess** in the refresh subagent (`kind_source=model`).
9. **Coverage statement** in place of a missing count, plus an optional `--seed` import.
10. **Skill location:** files in the handling repo, symlinked from the brief's path.
11. **Spec location:** here in retritis, beside the brief and #17. The handling repo does
   not exist yet.

## 7. Left to the builder

- The repo names on GitHub (`artifact-corpus`, `artifact-ledger` are placeholders).
- Cron or systemd user timer, and the interval. snape has no user crontab today; it has
  only system timers.
- The exact staleness rule that triggers a lazy refresh.
- The internal shape of the macros, as long as each one encodes its idiom and has a test
  that pins the gotcha it guards (for example, the `E2|NULL` fixture for `evidence()`).

## 8. Unverified (measure before relying on it)

- Whether longbottom's transcripts add ids that snape lacks (expected, but not measured).
- Whether the 5 unresolved UUIDs (`analysis`, `corpus_stages`, `shutdown`,
  `tiiny-pipeline`, panduck status board) are aliases or distinct artifacts.
- Whether `Artifact read` on a UUID returns the same version string as on its short id.
  The alias rule in 5.3 depends on this.
- Whether pages that were deleted on claude.ai make `read` fail, or return something
  else. That decides the `unreadable` status.
- Whether `zim_search` performs acceptably at about 60 pages with large embedded images
  (the 654 KB page is mostly base64 JPEG).
