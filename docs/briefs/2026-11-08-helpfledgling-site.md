# Brief: build the helpfledgling.ai site for the retritis suite

Written 2026-11-08 by the `webspace-root-cleanup` Claude session (in the `ionos`
repo), at Teague's request: "Start a separate project for the real
helpfledgling.ai site for the retritis suite."

## STAR summary

**Situation.** `retritis` (this repo) is Teague's meta-installer for his suite of
agent tools: fledgling, squackit, blq, jetsam, duckeye, lackpy, kibitzer, umwelt,
agent-riggs and others. Teague owns the domain `helpfledgling.ai`, registered at
IONOS, and he says it was always meant for this suite. Until today nothing served
it except an IONOS parking page.

**Task.** Design and build the real helpfledgling.ai site for the retritis suite.
What the site is (a landing page, a docs home, both) is not decided yet.

**Action.** Brainstorm with Teague first. Then spec it, plan it, build it, and
deploy it to wherever he chooses.

**Result (true right now).** helpfledgling.ai (and www) serves a one-paragraph
placeholder from the IONOS folder `~/sites/helpfledgling.ai/`: "helpfledgling.ai.
Home of the retritis suite. Coming soon." This repo already has
`docs/index.html` ("Retritis — how the suite works together") and a book in
`docs/book/` (`00-preface.md` to `09-lackpy.md` and on). Neither is published
anywhere yet.

## Status

An idea, approved as a project. Not specced. **Run `superpowers:brainstorming`
first.** Teague has not said what the site should contain or where it should run.

## The prompt

You are starting the helpfledgling.ai website for the retritis suite. Begin with
`superpowers:brainstorming`, and ask Teague one question at a time. Look at what
already exists in this repo before you propose anything: `README.md`,
`docs/index.html`, `docs/architecture.svg` and `docs/book/`. The site will
probably reuse them.

When the design is approved, write the spec to
`docs/superpowers/specs/`, plan it, and build it. Publish design documents as
artifacts too, because Teague reads them on a phone.

## Measured so far (2026-11-08)

- `curl http://helpfledgling.ai/` gives 200 with the placeholder page. HTTPS is
  not set up. IONOS gives only about 2 free certificates on this account.
- `https://teaguesterling.github.io/retritis/` gives 404, so this repo has no
  GitHub Pages site yet.
- The domain had about 20 hits a week before today. Almost all were bots
  (inferred from the paths requested).
- The `fledgling` repo already publishes docs at `https://fledgling.readthedocs.io`
  and `https://teaguesterling.github.io/fledgling/`.

## The first question to settle: where does the site run?

This decision forks the build. Ask it early.

- **IONOS** (where the placeholder is now). Static files, deployed by rsync
  through `ssh snape ssh ionos` into `~/sites/helpfledgling.ai/`. The `ionos`
  repo's `ionos-sites` skill has the deploy model. **But Teague said on
  2026-11-08 that he wants to leave IONOS "sooner rather than later".**
- **GitHub Pages**, like teaguesterling.com and judgementalmonad.com, which moved
  there on 2026-11-08 (the main-ea session did those). This gives free HTTPS and
  survives an IONOS exit. It needs a DNS change, and only Teague makes DNS
  changes.
- The homelab, behind Caddy. Ask the `homelab` session if this comes up.

## Limits, agreed up front

- **No DNS changes, and no IONOS panel changes.** Only Teague changes DNS and
  Destinations. Tell him the exact record or setting to change.
- On IONOS, write only inside `~/sites/helpfledgling.ai/`. Do not touch any other
  folder on the host. The rest of the webspace was just cleaned up.
- After any IONOS change, run `deploy/check-served.sh` in `~/Projects/ionos`, and
  update the helpfledgling.ai rows in `deploy/served.tsv` there (they expect the
  text `retritis suite` today).
- Git and GitHub through the `jetsam` tools, not raw `git` or `gh`.

## Links

- `~/Projects/ionos`: the IONOS account map. `inventory/domains.yaml` has the
  helpfledgling.ai entry. `docs/host-root-README.md` describes the webspace.
- Cleanup write-up artifact: https://claude.ai/artifact/79EVgqSMqNmAa7CxXi9YJ7
- Originating session: https://claude.ai/code/session_01NSRdqdgH5WqkgNdoa2zBat
