# Brief: artifact-corpus — query the published artifact corpus with webbed

**Status:** idea, approved, deferred as an addon. Tracked at
teaguesterling/retritis#17.
**Origin:** Teague, 2026-10-18. Reasoning in
claude.ai/code/session_01XoHU19qnngy1CJnXyX1csz

---

## The prompt

Build the companion to the `house-artifact` skill: a way to extract from, and
refer to, previously published artifacts, using DuckDB and `webbed`.

The insight that makes it possible: **the house style's class names double as a
schema.** About twenty published artifacts already share `.ruling`, `.evidence`,
`.cap`, `.strip`, `.pill` and a `footer` link block. That consistency is what
makes the corpus queryable, so the style convention and the data model are the
same thing.

Deliver it as a skill beside `house-artifact`, in
`~/.dotfiles/.claude/skills/artifact-corpus/`, symlinked into
`~/.claude/skills/` the way `house-artifact` and `deep-field` are.

## What it must answer

  - **Every standing lesson.** All `.ruling` blocks across the corpus. These are
    the decisions meant to outlive their document, and right now they are
    unreadable in bulk.
  - **Every measurement.** Each `.evidence` block paired with its `.cap`.
  - **The headline figures.** `.strip` `dt`/`dd` pairs as a table.
  - **A citation graph.** Footer links, so a new artifact can cite prior work
    and so you can check whether a page already covers the subject before
    writing a new one.
  - **Prior art lookup.** "Have I written about X?" — titles, eyebrows and
    standfirsts, searchable.

## Verified API — these run today against webbed v2.10.0

```sql
LOAD webbed;
-- the signature that matters: html_extract_text(html, xpath) -> VARCHAR[]
SELECT html_extract_text(content, '//div[contains(@class,"ruling")]/p')
FROM read_text('~/.claude/artifacts-cache/*.html');

-- citation graph: returns struct(text, href, title, line_number)
SELECT unnest(html_extract_links(content)) FROM read_text(...);
```

`read_html_objects` takes no XPath — only `filename`, `maximum_file_size`,
`ignore_errors` — so per-node work goes through `html_extract_text` with an
indexed XPath. `parse_html_objects` cannot take a subquery argument
(`Binder Error: Table function cannot contain subqueries`).

## Two gotchas, already measured. Both are silent-wrong. Encode them.

**1. Parallel `unnest` pairs positionally and misaligns.** Two separate XPaths
unnested side by side will shift every row after a container that is missing one
child:

```
E1|C1
E2|C3      <- wrong: E2 has no caption, C3 belongs to E3
E3|NULL
```

The safe idiom is one indexed XPath per container:

```sql
WITH d AS (SELECT filename, content FROM read_text('...*.html')),
     n AS (SELECT *, len(html_extract_text(content,'//div[contains(@class,"evidence")]')) AS k FROM d)
SELECT i AS idx,
  html_extract_text(content,'(//div[contains(@class,"evidence")])['||i||']/pre')[1] AS evidence,
  html_extract_text(content,'(//div[contains(@class,"evidence")])['||i||']/p[contains(@class,"cap")]')[1] AS caption
FROM n, generate_series(1,k) t(i);
```

Verified to give `E1|C1`, `E2|NULL`, `E3|C3`.

**2. A child element concatenates into its parent's text.** `//dd` yields
`1,230assertions`. Use `//dd/text()` for `1,230` and `//dd/small` for
`assertions`.

## The part that is not solved yet

Artifacts live on claude.ai and need authenticated reads, so the corpus has to
be cached locally first. Decide the cache: where it lives, how it refreshes, and
how it maps artifact id to file. `Artifact action:"list"` gives ids, titles and
updated timestamps; `action:"read"` gives the HTML and saves large ones to a
file. An incremental refresh keyed on the updated timestamp is probably right.

Do not scrape claude.ai with curl. It returns the SPA shell or a 403.

## Context

  - `~/.dotfiles/.claude/skills/house-artifact/` — the style whose class names
    are the schema. `style.css` is the authority on which classes exist.
  - `~/.CLAUDE.md`, "Explanation artifacts" — the policy this serves.
  - webbed is served at v2.10.0 and is two releases behind v2.12.0, because its
    registry PR has not been swept. Pin to what is actually served, and
    re-measure the API if you install a newer one.
